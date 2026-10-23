"""Deterministic weekly note. It uses counts that were actually recorded."""


def weekly_journal(
    *,
    active_days: int,
    xp: int,
    blooms: int,
    quiet_days: int,
) -> str:
    if active_days <= 0:
        opening = "The garden held still this week. Nothing was lost."
    elif active_days == 1:
        opening = f"One cared-for day added {xp} XP. That counts."
    else:
        opening = f"{active_days} cared-for days added {xp} XP."
    sentences = [opening]
    if blooms:
        sentences.append("A plant moved into a new stage.")
    if quiet_days:
        sentences.append("Quiet days left every plant where it was.")
    sentences.append("A small improvement on another day is enough.")
    return " ".join(sentences)
