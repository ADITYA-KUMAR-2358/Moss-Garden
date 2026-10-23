"""Stable fallback plant names. The same slot always gets the same name."""

_ADJECTIVES = (
    "Quiet",
    "Patient",
    "Soft",
    "Small",
    "Steady",
    "Kind",
    "Clear",
    "Gentle",
)


def fallback_plant_copy(species: str, slot: int) -> tuple[str, str]:
    adjective = _ADJECTIVES[slot % len(_ADJECTIVES)]
    name = f"{adjective} {species}"
    description = f"A {species} kept by ordinary, repeated work."
    return name, description
