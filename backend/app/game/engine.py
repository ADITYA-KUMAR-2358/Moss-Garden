"""Replay a commit history into garden state.

The result depends only on the activities and the UTC day passed as `today`.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.config import (
    BADGE_ACTIVE_DAYS,
    BADGE_LEVELS,
    BADGE_RETURN_GAP_DAYS,
    CARETAKER_SIGNALS,
    LEVEL_STEP,
    MATURITY_BLOOM_AT,
    MATURITY_MATURE_AT,
    MATURITY_PER_ACTIVE_DAY,
    MATURITY_YOUNG_AT,
    PLANT_SPECIES,
    VITALITY_ACTIVE_GAIN,
    VITALITY_DROUGHT_BELOW,
    VITALITY_FLOOR,
    VITALITY_MAX,
    VITALITY_RECOVERY_FLOOR,
    VITALITY_REST_LOSS,
    VITALITY_START,
    WEEKLY_STEADY_BONUS_XP,
    WEEKLY_STEADY_DAYS,
    XP_BASE,
    XP_DAILY_CAP,
    XP_ORDER_MULTIPLIERS,
    XP_RUSH_COMMIT_COUNT,
)


@dataclass(frozen=True)
class Activity:
    repo_key: str
    sha: str
    committed_at: datetime
    quality: float
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class Award:
    source_key: str
    amount: int
    reason: str
    day: date


@dataclass(frozen=True)
class DayRecord:
    day: date
    commit_count: int
    commit_xp: int
    bonus_xp: int
    rush: bool


@dataclass(frozen=True)
class PlantRecord:
    slot: int
    species: str
    maturity: int
    planted_on: date


@dataclass(frozen=True)
class Projection:
    xp: int
    level: int
    vitality: int
    drought: bool
    fresh: bool
    season: str
    awards: tuple[Award, ...]
    days: tuple[DayRecord, ...]
    plants: tuple[PlantRecord, ...]
    badges: tuple[str, ...]


def utc_day(moment: datetime) -> date:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).date()


def level_threshold(level: int) -> int:
    if level <= 1:
        return 0
    return LEVEL_STEP * (level - 1) * level // 2


def level_for_xp(xp: int) -> int:
    level = 1
    while xp >= level_threshold(level + 1):
        level += 1
        if level > 100:
            break
    return level


def season_for(day: date) -> str:
    if day.month in (12, 1, 2):
        return "frost"
    if day.month in (3, 4, 5):
        return "rain"
    if day.month in (6, 7, 8):
        return "sun"
    return "leaf"


def stage_for(maturity: int) -> str:
    if maturity >= MATURITY_BLOOM_AT:
        return "bloom"
    if maturity >= MATURITY_MATURE_AT:
        return "mature"
    if maturity >= MATURITY_YOUNG_AT:
        return "young"
    return "sprout"


def _scaled_xp(quality: float, multiplier: float) -> int:
    clamped = min(1.0, max(0.0, quality))
    value = Decimal(XP_BASE) * Decimal(str(clamped)) * Decimal(str(multiplier))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _vitality(active: set[date], today: date) -> tuple[int, bool, bool]:
    if not active:
        return VITALITY_START, False, True
    value = VITALITY_START
    day = min(active)
    while day <= today:
        if day in active:
            if value < VITALITY_DROUGHT_BELOW:
                value = min(VITALITY_MAX, max(value + VITALITY_ACTIVE_GAIN, VITALITY_RECOVERY_FLOOR))
            else:
                value = min(VITALITY_MAX, value + VITALITY_ACTIVE_GAIN)
        else:
            value = max(VITALITY_FLOOR, value - VITALITY_REST_LOSS)
        day += timedelta(days=1)
    return value, value < VITALITY_DROUGHT_BELOW, False


def _species_for(slot: int, level: int) -> str:
    opened = [item["id"] for item in PLANT_SPECIES if item["min_level"] <= level]
    if not opened:
        opened = [PLANT_SPECIES[0]["id"]]
    return opened[slot % len(opened)]


def project(activities: list[Activity], today: date) -> Projection:
    ordered = sorted(activities, key=lambda item: (utc_day(item.committed_at), item.committed_at, item.sha))
    seen: set[tuple[str, str]] = set()
    by_day: dict[date, list[Activity]] = {}
    for activity in ordered:
        day = utc_day(activity.committed_at)
        if day > today:
            continue
        key = (activity.repo_key, activity.sha)
        if key in seen:
            continue
        seen.add(key)
        by_day.setdefault(utc_day(activity.committed_at), []).append(activity)

    awards: list[Award] = []
    days: list[DayRecord] = []
    plants: list[PlantRecord] = []
    xp = 0
    open_plant: PlantRecord | None = None
    week_counts: dict[tuple[int, int], int] = {}
    caretaker = False

    if by_day:
        cursor = min(by_day)
        last = max(max(by_day), today)
        while cursor <= last:
            bucket = by_day.get(cursor, [])
            commit_xp = 0
            for index, activity in enumerate(bucket):
                multiplier = XP_ORDER_MULTIPLIERS[min(index, len(XP_ORDER_MULTIPLIERS) - 1)]
                raw = _scaled_xp(activity.quality, multiplier)
                room = XP_DAILY_CAP - commit_xp
                awarded = max(0, min(raw, room))
                if awarded:
                    awards.append(
                        Award(
                            source_key=f"commit:{activity.repo_key}:{activity.sha}",
                            amount=awarded,
                            reason="commit",
                            day=cursor,
                        )
                    )
                    commit_xp += awarded
                if any(signal in CARETAKER_SIGNALS for signal in activity.signals):
                    caretaker = True
            bonus = 0
            if bucket:
                year, week, _weekday = cursor.isocalendar()
                week_counts[(year, week)] = week_counts.get((year, week), 0) + 1
                if week_counts[(year, week)] == WEEKLY_STEADY_DAYS:
                    bonus = WEEKLY_STEADY_BONUS_XP
                    awards.append(
                        Award(
                            source_key=f"week:{year}-W{week:02d}",
                            amount=bonus,
                            reason="steady-week",
                            day=cursor,
                        )
                    )
            if bucket or bonus:
                days.append(
                    DayRecord(
                        day=cursor,
                        commit_count=len(bucket),
                        commit_xp=commit_xp,
                        bonus_xp=bonus,
                        rush=len(bucket) >= XP_RUSH_COMMIT_COUNT,
                    )
                )
            xp += commit_xp + bonus
            if bucket:
                level_now = level_for_xp(xp)
                if open_plant is None or open_plant.maturity >= MATURITY_BLOOM_AT:
                    open_plant = PlantRecord(
                        slot=len(plants),
                        species=_species_for(len(plants), level_now),
                        maturity=0,
                        planted_on=cursor,
                    )
                    plants.append(open_plant)
                grown = min(MATURITY_BLOOM_AT, open_plant.maturity + MATURITY_PER_ACTIVE_DAY)
                open_plant = PlantRecord(
                    open_plant.slot,
                    open_plant.species,
                    grown,
                    open_plant.planted_on,
                )
                plants[open_plant.slot] = open_plant
            cursor += timedelta(days=1)

    active = {item.day for item in days if item.commit_count}
    vitality, drought, fresh = _vitality(active, today)
    level = level_for_xp(xp)
    badges = _badges(active, plants, level, caretaker)
    return Projection(
        xp=xp,
        level=level,
        vitality=vitality,
        drought=drought,
        fresh=fresh,
        season=season_for(today),
        awards=tuple(awards),
        days=tuple(days),
        plants=tuple(plants),
        badges=badges,
    )


def _badges(
    active: set[date],
    plants: list[PlantRecord],
    level: int,
    caretaker: bool,
) -> tuple[str, ...]:
    found: list[str] = []
    if active:
        found.append("first-commit")
    if len(active) >= BADGE_ACTIVE_DAYS:
        found.append("seven-days")
    weeks: dict[tuple[int, int], int] = {}
    for day in active:
        key = (day.isocalendar().year, day.isocalendar().week)
        weeks[key] = weeks.get(key, 0) + 1
    if any(count >= WEEKLY_STEADY_DAYS for count in weeks.values()):
        found.append("steady-week")
    if any(plant.maturity >= MATURITY_MATURE_AT for plant in plants):
        found.append("mature")
    if any(plant.maturity >= MATURITY_BLOOM_AT for plant in plants):
        found.append("bloom")
    for marker in BADGE_LEVELS:
        if level >= marker:
            found.append(f"level-{marker}")
    ordered = sorted(active)
    for earlier, later in zip(ordered, ordered[1:]):
        quiet = (later - earlier).days - 1
        if quiet >= BADGE_RETURN_GAP_DAYS:
            found.append("returned")
            break
    if caretaker:
        found.append("caretaker")
    return tuple(found)
