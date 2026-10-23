from datetime import date, datetime, timezone

from app.game.engine import Activity, level_for_xp, level_threshold, project, season_for
from app.game.journal import weekly_journal
from app.game.names import fallback_plant_copy
from app.game.quality import score_message


def _commit(day: str, sha: str, quality: float = 0.7, signals=()):
    return Activity(
        repo_key="demo/garden",
        sha=sha,
        committed_at=datetime.fromisoformat(day + "T12:00:00+00:00"),
        quality=quality,
        signals=signals,
    )


def test_no_activity_keeps_a_fresh_garden():
    state = project([], date(2026, 10, 21))

    assert state.xp == 0
    assert state.level == 1
    assert state.fresh is True
    assert state.drought is False
    assert state.plants == ()
    assert state.badges == ()
    assert state.season == "leaf"


def test_one_commit_awards_quality_weighted_xp():
    state = project([_commit("2026-10-21", "a", 1.0)], date(2026, 10, 21))

    assert state.xp == 10
    assert state.awards[0].amount == 10
    assert state.badges == ("first-commit",)


def test_same_day_order_diminishes_and_hits_the_cap():
    dozen = [_commit("2026-10-21", f"c{index:02d}", 1.0) for index in range(12)]
    dozen_state = project(dozen, date(2026, 10, 21))
    crowded = [_commit("2026-10-22", f"d{index:02d}", 1.0) for index in range(30)]
    crowded_state = project(crowded, date(2026, 10, 22))

    assert [award.amount for award in dozen_state.awards[:4]] == [10, 5, 3, 1]
    assert dozen_state.xp == 27
    assert dozen_state.days[0].rush is True
    assert crowded_state.xp == 40
    assert crowded_state.days[0].commit_count == 30


def test_steady_week_beats_one_burst():
    steady = [_commit(f"2026-10-{day:02d}", f"s{day}", 0.7) for day in (5, 6, 7, 8)]
    burst = [_commit("2026-10-09", f"b{index}", 0.7) for index in range(12)]

    steady_state = project(steady, date(2026, 10, 8))
    burst_state = project(burst, date(2026, 10, 9))

    assert steady_state.xp == 43
    assert any(award.reason == "steady-week" for award in steady_state.awards)
    assert burst_state.xp == 22
    assert burst_state.xp < steady_state.xp
    assert "steady-week" not in burst_state.badges


def test_quiet_days_do_not_remove_progress():
    commits = [_commit("2026-10-01", "a", 1.0)]
    before = project(commits, date(2026, 10, 1))
    after = project(commits, date(2026, 10, 21))

    assert after.xp == before.xp
    assert after.level == before.level
    assert after.plants == before.plants
    assert set(before.badges).issubset(after.badges)
    assert after.vitality >= 20
    assert after.drought is True


def test_return_after_a_gap_earns_a_badge_without_losing_xp():
    commits = [
        _commit("2026-10-01", "a", 1.0),
        _commit("2026-10-10", "b", 1.0),
    ]
    state = project(commits, date(2026, 10, 10))

    assert state.xp == 20
    assert "returned" in state.badges
    assert state.vitality >= 50


def test_level_boundaries():
    assert level_threshold(1) == 0
    assert level_threshold(2) == 40
    assert level_threshold(3) == 120
    assert level_for_xp(39) == 1
    assert level_for_xp(40) == 2
    assert level_for_xp(119) == 2
    assert level_for_xp(120) == 3


def test_maturity_boundaries_and_the_next_plant():
    commits = [_commit(f"2026-01-{day:02d}", f"d{day}", 0.4) for day in range(1, 15)]
    state = project(commits, date(2026, 1, 14))
    first, second = state.plants

    assert first.maturity == 100
    assert second.maturity == 8
    assert second.planted_on == date(2026, 1, 14)
    assert "mature" in state.badges
    assert "bloom" in state.badges


def test_replay_is_stable_and_xp_does_not_shrink():
    commits = [_commit("2026-10-02", "a", 0.85, ("test",))]
    first = project(commits, date(2026, 10, 4))
    second = project(commits, date(2026, 10, 4))

    assert second.xp == first.xp
    assert second.awards == first.awards
    assert "caretaker" in second.badges


def test_seasons_follow_utc_month():
    assert season_for(date(2026, 1, 2)) == "frost"
    assert season_for(date(2026, 4, 2)) == "rain"
    assert season_for(date(2026, 7, 2)) == "sun"
    assert season_for(date(2026, 10, 2)) == "leaf"


def test_quality_table_and_fallback_copy():
    assert score_message("").weight == 0.35
    assert score_message("wip").weight == 0.45
    assert score_message("Add regression test").weight == 0.85
    assert score_message("Rename the helper").weight == 0.7
    assert fallback_plant_copy("moss", 0) == fallback_plant_copy("moss", 0)


def test_journal_uses_the_counts_it_is_given():
    text = weekly_journal(active_days=0, xp=0, blooms=0, quiet_days=7)
    assert "Nothing was lost" in text
    assert "—" not in text


def test_naive_datetime_is_read_as_utc():
    activity = Activity(
        repo_key="demo/garden",
        sha="z",
        committed_at=datetime(2026, 10, 21, 23, 30),
        quality=1,
    )
    state = project([activity], date(2026, 10, 21))
    assert state.days[0].day == date(2026, 10, 21)
    assert activity.committed_at.tzinfo is None
    assert timezone.utc is timezone.utc
