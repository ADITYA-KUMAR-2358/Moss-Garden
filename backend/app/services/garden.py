"""Rebuild and store garden state from commits. Replay is safe."""

import logging
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.schema import parse_journal_payload, parse_name_payload, parse_quality_payload
from app.config import (
    AUDIO_RAIN_LEVEL,
    AUDIO_SPRING_LEVEL,
    BADGE_LABELS,
    BADGE_RETURN_GAP_DAYS,
    GITHUB_HISTORY_DAYS,
    PLANT_SPECIES,
    get_settings,
)
from app.game.engine import Activity, project, stage_for
from app.game.journal import weekly_journal
from app.game.names import fallback_plant_copy
from app.game.quality import score_message
from app.integrations.backboard import BackboardLLMClient
from app.integrations.github import CommitCandidate, GitHubClient, GitHubError, RepoCandidate
from app.models import (
    AiCache,
    Badge,
    CommitRecord,
    GardenDay,
    Journal,
    JournalAudio,
    Plant,
    Repository,
    UsageLog,
    User,
    XpLedger,
)

logger = logging.getLogger(__name__)
AI_MODEL_LABEL = "Gemma 4, an open-weight model, through Backboard"
AI_NAMES_PER_RUN = 3


def _signals(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part for part in value.split(",") if part)


def activities_for(session: Session, user_id: int) -> list[Activity]:
    rows = session.scalars(select(CommitRecord).where(CommitRecord.user_id == user_id)).all()
    repo_names = {
        row.id: row.full_name
        for row in session.scalars(select(Repository).where(Repository.user_id == user_id)).all()
    }
    return [
        Activity(
            repo_key=repo_names.get(row.repository_id, str(row.repository_id)),
            sha=row.sha,
            committed_at=row.committed_at,
            quality=row.quality,
            signals=_signals(row.signals),
        )
        for row in rows
    ]


def remember_projection(session: Session, user: User, today: date) -> dict:
    projection = project(activities_for(session, user.id), today)
    for award in projection.awards:
        source_key = f"user:{user.id}:{award.source_key}"
        exists = session.scalar(select(XpLedger.id).where(XpLedger.source_key == source_key))
        if exists is None and award.amount > 0:
            session.add(
                XpLedger(
                    user_id=user.id,
                    source_key=source_key,
                    amount=award.amount,
                    reason=award.reason,
                    day=award.day,
                )
            )
    for record in projection.days:
        if record.commit_count <= 0 and record.bonus_xp <= 0:
            continue
        row = session.scalar(
            select(GardenDay).where(GardenDay.user_id == user.id, GardenDay.day == record.day)
        )
        if row is None:
            session.add(
                GardenDay(
                    user_id=user.id,
                    day=record.day,
                    commit_count=record.commit_count,
                    commit_xp=record.commit_xp,
                    bonus_xp=record.bonus_xp,
                    rush=record.rush,
                )
            )
        else:
            row.commit_count = record.commit_count
            row.commit_xp = max(row.commit_xp, record.commit_xp)
            row.bonus_xp = max(row.bonus_xp, record.bonus_xp)
            row.rush = record.rush
    existing_plants = {
        row.slot: row
        for row in session.scalars(select(Plant).where(Plant.user_id == user.id)).all()
    }
    for record in projection.plants:
        current = existing_plants.get(record.slot)
        if current is None:
            name, description = fallback_plant_copy(record.species, record.slot)
            session.add(
                Plant(
                    user_id=user.id,
                    slot=record.slot,
                    species=record.species,
                    name=name,
                    description=description,
                    name_source="rules",
                    maturity=record.maturity,
                    planted_on=record.planted_on,
                )
            )
        else:
            current.species = record.species
            current.maturity = max(current.maturity, record.maturity)
    owned = set(session.scalars(select(Badge.badge_id).where(Badge.user_id == user.id)).all())
    for badge_id in projection.badges:
        if badge_id not in owned:
            session.add(Badge(user_id=user.id, badge_id=badge_id, earned_on=today))
    session.flush()
    xp = session.scalar(select(func.coalesce(func.sum(XpLedger.amount), 0)).where(XpLedger.user_id == user.id))
    return _view(session, user, today, int(xp or 0), projection)


def _view(session: Session, user: User, today: date, xp: int, projection) -> dict:
    plants = session.scalars(select(Plant).where(Plant.user_id == user.id).order_by(Plant.slot)).all()
    badges = session.scalars(select(Badge).where(Badge.user_id == user.id)).all()
    year, week, _weekday = today.isocalendar()
    week_days = [row for row in projection.days if row.day.isocalendar()[:2] == (year, week)]
    active = sum(1 for row in week_days if row.commit_count)
    week_xp = sum(row.commit_xp + row.bonus_xp for row in week_days)
    blooms = sum(1 for plant in plants if plant.maturity >= 100)
    quiet = 7 - min(active, 7)
    journal = weekly_journal(active_days=active, xp=week_xp, blooms=blooms, quiet_days=max(quiet, 0))
    monday = _week_start(today)
    journal, journal_source = _store_journal(session, user, today, monday, journal)
    has_audio = _narrate_week(session, user, monday, journal)
    species_labels = {item["id"]: item["label"] for item in PLANT_SPECIES}
    level = projection.level
    next_xp = None
    from app.game.engine import level_threshold

    upcoming = level_threshold(level + 1)
    if upcoming > xp:
        next_xp = upcoming
    share_text = f"My moss garden is level {level}, with {xp} XP kept. Small commits, slow growth."
    counted_days = [row for row in projection.days if row.commit_count]
    repos_counted = session.scalar(
        select(func.count(Repository.id)).where(Repository.user_id == user.id, Repository.selected.is_(True))
    )
    github_url = None if user.is_demo else f"https://github.com/{quote(user.login)}"
    return {
        "login": user.login,
        "display_name": user.display_name,
        "demo": user.is_demo,
        "profile": {
            "avatar_url": f"{github_url}.png?size=160" if github_url else None,
            "github_url": github_url,
            "member_since": user.created_at.date().isoformat() if user.created_at else None,
            "first_commit_day": counted_days[0].day.isoformat() if counted_days else None,
            "commits": sum(row.commit_count for row in counted_days),
            "active_days": len(counted_days),
            "repos": int(repos_counted or 0),
        },
        "xp": xp,
        "level": level,
        "next_level_xp": next_xp,
        "vitality": projection.vitality,
        "drought": projection.drought,
        "fresh": projection.fresh,
        "season": projection.season,
        "return_gap_days": BADGE_RETURN_GAP_DAYS,
        "audio": {
            "spring_level": AUDIO_SPRING_LEVEL,
            "rain_level": AUDIO_RAIN_LEVEL,
        },
        "plants": [
            {
                "slot": plant.slot,
                "species": plant.species,
                "label": species_labels.get(plant.species, plant.species),
                "name": plant.name,
                "description": plant.description,
                "maturity": plant.maturity,
                "stage": stage_for(plant.maturity),
                "name_source": plant.name_source,
            }
            for plant in plants
        ],
        "badges": [
            {
                "id": badge.badge_id,
                "label": BADGE_LABELS.get(badge.badge_id, badge.badge_id),
                "earned_on": badge.earned_on.isoformat(),
            }
            for badge in sorted(badges, key=lambda row: row.earned_on)
        ],
        "week": {
            "active_days": active,
            "steady_days": 4,
            "xp": week_xp,
        },
        "ai": {
            "available": ai_available(),
            "enabled": bool(user.ai_opt_in),
            "model": AI_MODEL_LABEL,
            "can_change": not user.is_demo,
        },
        "journal": {
            "body": journal,
            "source": journal_source,
            "week_start": monday.isoformat(),
            "audio": has_audio,
            "narration": has_audio,
        },
        "recent": [
            {
                "day": row.day.isoformat(),
                "commits": row.commit_count,
                "xp": row.commit_xp + row.bonus_xp,
                "rush": row.rush,
            }
            for row in projection.days
            if row.commit_count or row.bonus_xp
        ][-8:],
        "share": {
            "text": share_text,
            "intent_url": "https://twitter.com/intent/tweet?text=" + quote(share_text),
        },
    }


def store_candidates(session: Session, user: User, repository: Repository, candidates: list[CommitCandidate], client: BackboardLLMClient | None) -> int:
    added = 0
    settings = get_settings()
    for candidate in candidates:
        exists = session.scalar(
            select(CommitRecord.id).where(
                CommitRecord.repository_id == repository.id,
                CommitRecord.sha == candidate.sha,
            )
        )
        if exists is not None:
            continue
        scored = score_message(candidate.message)
        source = scored.source
        if (
            client is not None
            and settings.ai_include_commit_messages
            and candidate.message.strip()
        ):
            prompt = (
                "Score this commit message only. Do not claim you read the code. "
                "Reply as JSON with keys quality (0 to 1), signals (array), note (short). "
                f"Message: {candidate.message[:500]}"
            )
            payload = client.complete_json(
                cache_key=f"quality:{repository.full_name}:{candidate.sha}:{settings.backboard_model_name}",
                prompt=prompt,
            )
            parsed = parse_quality_payload(payload)
            if parsed is not None:
                scored = parsed
                source = "model"
        session.add(
            CommitRecord(
                user_id=user.id,
                repository_id=repository.id,
                sha=candidate.sha,
                committed_at=candidate.committed_at,
                message=candidate.message,
                quality=scored.weight,
                signals=",".join(scored.signals),
                quality_source=source,
            )
        )
        added += 1
    session.flush()
    return added


def start_from_github(session: Session, user: User, client: GitHubClient, today: date | None = None) -> dict:
    """List repositories after sign-in and grow the first one if nothing is chosen yet."""
    try:
        remote = client.list_repos()
    except GitHubError as error:
        return {"imported": 0, "status": "error", "detail": str(error)}
    _upsert_repos(session, user, remote)
    session.commit()
    chosen = session.scalars(
        select(Repository).where(Repository.user_id == user.id, Repository.selected.is_(True))
    ).all()
    owned = [item for item in remote if not item.private and item.full_name.startswith(f"{user.login}/")]
    picked = owned[:5] or [item for item in remote if not item.private][:1]
    if not chosen and picked:
        names = {item.full_name for item in picked}
        rows = session.scalars(select(Repository).where(Repository.user_id == user.id)).all()
        for row in rows:
            if row.full_name in names:
                row.selected = True
        session.commit()
    return sync_repositories(session, user, client, today)


def sync_repositories(session: Session, user: User, client: GitHubClient, today: date | None = None) -> dict:
    if user.is_demo or not user.token_encrypted:
        return {"imported": 0, "status": "skipped"}
    today = today or datetime.now(timezone.utc).date()
    since = (datetime.now(timezone.utc) - timedelta(days=GITHUB_HISTORY_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    imported = 0
    try:
        remote = client.list_repos()
    except GitHubError as error:
        return {"imported": 0, "status": "error", "detail": str(error)}
    _upsert_repos(session, user, remote)
    selected = session.scalars(
        select(Repository).where(Repository.user_id == user.id, Repository.selected.is_(True))
    ).all()
    llm = BackboardLLMClient(get_settings(), session, today) if user.ai_opt_in else None
    for repository in selected:
        try:
            for page in client.iter_commits(repository.full_name, user.login, since):
                imported += store_candidates(session, user, repository, page, llm)
                session.commit()
            repository.accessible = True
        except GitHubError as error:
            repository.accessible = error.status != 404
            session.commit()
            continue
    remember_projection(session, user, today)
    session.commit()
    if llm is not None:
        tend_with_ai(session, user, today, llm)
        session.commit()
    return {"imported": imported, "status": "ok"}


def ai_available() -> bool:
    settings = get_settings()
    return bool(
        settings.ai_enabled
        and settings.ai_daily_request_budget > 0
        and settings.backboard_api_key
        and settings.backboard_llm_provider
        and settings.backboard_model_name
    )


def tend_with_ai(session: Session, user: User, today: date, client: BackboardLLMClient | None = None) -> dict:
    """Name new plants and write this week's journal. Only garden counts and species are sent."""
    if not user.ai_opt_in or user.is_demo or not ai_available():
        return {"named": 0, "journal": False}
    client = client or BackboardLLMClient(get_settings(), session, today)
    named = 0
    unnamed = session.scalars(
        select(Plant)
        .where(Plant.user_id == user.id, Plant.name_source != "model")
        .order_by(Plant.slot)
        .limit(AI_NAMES_PER_RUN)
    ).all()
    for plant in unnamed:
        maybe_name_plant(session, user, plant, client)
        named += int(plant.name_source == "model")
    session.flush()
    wrote = _ai_journal(session, user, today, client)
    return {"named": named, "journal": wrote}


def _ai_journal(session: Session, user: User, today: date, client: BackboardLLMClient) -> bool:
    projection = project(activities_for(session, user.id), today)
    year, week, _weekday = today.isocalendar()
    week_days = [row for row in projection.days if row.day.isocalendar()[:2] == (year, week)]
    active = sum(1 for row in week_days if row.commit_count)
    week_xp = sum(row.commit_xp + row.bonus_xp for row in week_days)
    plants = session.scalars(select(Plant).where(Plant.user_id == user.id).order_by(Plant.slot)).all()
    names = ", ".join(f"{plant.name} ({plant.species})" for plant in plants[-6:]) or "none yet"
    week_key = _week_key(today)
    payload = client.complete_json(
        cache_key=f"journal:{user.id}:{week_key}:{active}:{week_xp}:{len(plants)}",
        prompt=(
            "Write a calm weekly garden journal entry of 2 to 4 short sentences. "
            "Never grade the gardener, never mention streaks, code, or repositories. "
            "Reply as JSON with one key, body. "
            f"Facts: {active} cared-for days this week, {week_xp} XP added, "
            f"{7 - min(active, 7)} quiet days, season {projection.season}, plants: {names}."
        ),
    )
    body = parse_journal_payload(payload)
    if body is None:
        return False
    row = session.scalar(select(Journal).where(Journal.user_id == user.id, Journal.week_key == week_key))
    if row is None:
        session.add(Journal(user_id=user.id, week_key=week_key, body=body, source="model", week_start=_week_start(today)))
    else:
        row.body = body
        row.source = "model"
    session.flush()
    return True


def export_garden(session: Session, user: User) -> dict:
    """Everything Moss Garden stores about this gardener, except the encrypted GitHub token."""
    repos = session.scalars(select(Repository).where(Repository.user_id == user.id)).all()
    repo_names = {row.id: row.full_name for row in repos}

    def rows(model, *order):
        return session.scalars(select(model).where(model.user_id == user.id).order_by(*order)).all()

    return {
        "format": "moss-garden-export",
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "gardener": {
            "login": user.login,
            "display_name": user.display_name,
            "github_id": user.github_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "ai_opt_in": bool(user.ai_opt_in),
        },
        "repositories": [
            {"full_name": row.full_name, "selected": row.selected, "accessible": row.accessible}
            for row in repos
        ],
        "commits": [
            {
                "repository": repo_names.get(row.repository_id),
                "sha": row.sha,
                "committed_at": row.committed_at.isoformat(),
                "message": row.message,
                "quality": row.quality,
                "signals": _signals(row.signals),
                "quality_source": row.quality_source,
            }
            for row in rows(CommitRecord, CommitRecord.committed_at)
        ],
        "xp_ledger": [
            {"day": row.day.isoformat(), "amount": row.amount, "reason": row.reason}
            for row in rows(XpLedger, XpLedger.day)
        ],
        "plants": [
            {
                "slot": row.slot,
                "species": row.species,
                "name": row.name,
                "description": row.description,
                "name_source": row.name_source,
                "maturity": row.maturity,
                "planted_on": row.planted_on.isoformat(),
            }
            for row in rows(Plant, Plant.slot)
        ],
        "badges": [
            {"id": row.badge_id, "label": BADGE_LABELS.get(row.badge_id, row.badge_id), "earned_on": row.earned_on.isoformat()}
            for row in rows(Badge, Badge.earned_on)
        ],
        "journals": [
            {"week": row.week_key, "source": row.source, "body": row.body}
            for row in rows(Journal, Journal.week_key)
        ],
    }


def _upsert_repos(session: Session, user: User, remote: list[RepoCandidate]) -> None:
    current = {
        row.github_repo_id: row
        for row in session.scalars(select(Repository).where(Repository.user_id == user.id)).all()
    }
    for item in remote:
        row = current.get(item.github_repo_id)
        if row is None:
            session.add(
                Repository(
                    user_id=user.id,
                    github_repo_id=item.github_repo_id,
                    full_name=item.full_name,
                    selected=False,
                    accessible=True,
                )
            )
        else:
            row.full_name = item.full_name
            row.accessible = True
    session.flush()


def _week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def _week_key(today: date) -> str:
    year, week, _weekday = today.isocalendar()
    return f"{year}-W{week:02d}"


def _store_journal(session: Session, user: User, today: date, monday: date, body: str) -> tuple[str, str]:
    """Keep this week's rules journal current. A model-written entry wins while AI stays on."""
    week_key = _week_key(today)
    row = session.scalar(select(Journal).where(Journal.user_id == user.id, Journal.week_key == week_key))
    if row is None:
        session.add(Journal(user_id=user.id, week_key=week_key, body=body, source="rules", week_start=monday))
        session.flush()
        return body, "rules"
    if row.source == "model" and user.ai_opt_in:
        return row.body, "model"
    row.body = body
    row.source = "rules"
    row.week_start = monday
    session.flush()
    return body, "rules"


def _characters_this_month(session: Session, today: date) -> int:
    start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    total = session.scalar(
        select(func.coalesce(func.sum(UsageLog.characters), 0)).where(
            UsageLog.purpose == "tts",
            UsageLog.created_at >= start,
        )
    )
    return int(total or 0)


def _narrate_week(session: Session, user: User, monday: date, body: str) -> bool:
    existing = session.scalar(
        select(JournalAudio).where(JournalAudio.user_id == user.id, JournalAudio.week_start == monday)
    )
    if existing is not None:
        return True
    settings = get_settings()
    if not settings.audio_enabled:
        return False
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        return False
    cleaned = " ".join(body.split())
    if not cleaned:
        return False
    spent = _characters_this_month(session, datetime.now(timezone.utc).date())
    if spent + len(cleaned) > settings.elevenlabs_monthly_char_cap:
        return False
    try:
        from app.integrations.elevenlabs import narrate

        audio = narrate(settings.elevenlabs_api_key, settings.elevenlabs_voice_id, cleaned)
    except Exception:
        logger.exception("narration skipped")
        return False
    session.add(
        JournalAudio(
            user_id=user.id,
            week_start=monday,
            voice_id=settings.elevenlabs_voice_id,
            audio=audio,
        )
    )
    session.add(
        UsageLog(
            purpose="tts",
            characters=len(cleaned),
            created_at=datetime.now(timezone.utc),
        )
    )
    session.flush()
    return True


def journal_audio_for(session: Session, user: User, week_start: date) -> bytes | None:
    row = session.scalar(
        select(JournalAudio).where(JournalAudio.user_id == user.id, JournalAudio.week_start == week_start)
    )
    if row is None:
        return None
    return row.audio


def delete_user(session: Session, user: User) -> None:
    for model in (JournalAudio, Journal, Badge, Plant, GardenDay, XpLedger, CommitRecord, Repository):
        session.execute(delete(model).where(model.user_id == user.id))
    # Ids can be reused after a delete, so cached names and journals must not outlive the gardener.
    for prefix in (f"name:{user.id}:", f"journal:{user.id}:"):
        session.execute(delete(AiCache).where(AiCache.cache_key.startswith(prefix)))
    session.delete(user)


def maybe_name_plant(session: Session, user: User, plant: Plant, client: BackboardLLMClient) -> None:
    if plant.name_source == "model":
        return
    payload = client.complete_json(
        cache_key=f"name:{user.id}:{plant.slot}:{plant.species}",
        prompt=(
            "Name a garden plant. Reply as JSON with name and description. "
            f"Species: {plant.species}. Do not mention repositories or code."
        ),
    )
    parsed = parse_name_payload(payload)
    if parsed is None:
        return
    plant.name, plant.description = parsed
    plant.name_source = "model"
