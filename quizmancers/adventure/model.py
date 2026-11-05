from dataclasses import dataclass, field

from ..curriculum import StudySelection


@dataclass(frozen=True)
class Companion:
    key: str
    name: str
    description: str


@dataclass(frozen=True)
class Lesson:
    key: str
    title: str
    selection: StudySelection
    minimum_accuracy: float = 0.6


@dataclass(frozen=True)
class Encounter:
    key: str
    name: str
    selection: StudySelection
    rank_floor: int = 0
    boss: bool = False


@dataclass(frozen=True)
class Portal:
    destination: str
    required_flag: str = ""


@dataclass(frozen=True)
class Location:
    key: str
    name: str
    description: str
    lessons: tuple[str, ...] = ()
    encounters: tuple[str, ...] = ()
    portals: tuple[Portal, ...] = ()


@dataclass
class AdventureProgress:
    location: str = "academy"
    companion: str = "pip"
    flags: set[str] = field(default_factory=set)
    completed_lessons: set[str] = field(default_factory=set)
    encounters_won: set[str] = field(default_factory=set)
    discovered: set[str] = field(default_factory=lambda: {"academy"})

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "location": self.location,
            "companion": self.companion,
            "flags": sorted(self.flags),
            "completed_lessons": sorted(self.completed_lessons),
            "encounters_won": sorted(self.encounters_won),
            "discovered": sorted(self.discovered),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AdventureProgress":
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("Invalid adventure save")
        keys = ("flags", "completed_lessons", "encounters_won", "discovered")
        if (not isinstance(payload.get("location"), str)
                or not isinstance(payload.get("companion"), str)
                or any(not isinstance(payload.get(key), list) or not all(isinstance(v, str) for v in payload[key])
                       for key in keys)):
            raise ValueError("Invalid adventure progress")
        return cls(payload["location"], payload["companion"],
                   *(set(payload[key]) for key in keys))
