from dataclasses import dataclass


@dataclass(frozen=True)
class RevisionPace:
    name: str
    deadline_scale: float
    ai_delay_scale: float
    familiar_interval_scale: float
    speed_bonus_scale: float
    retry_seconds: float


PACEs = {
    "Relaxed": RevisionPace("Relaxed", 1.5, 1.45, 1.5, 0.45, 4.5),
    "Standard": RevisionPace("Standard", 1.0, 1.0, 1.0, 0.8, 3.5),
    "Competitive": RevisionPace("Competitive", 0.85, 0.87, 0.88, 1.0, 3.0),
}


PACE_NAMES = tuple(PACEs)


def pace_for(name: str) -> RevisionPace:
    return PACEs.get(name, PACEs["Standard"])
