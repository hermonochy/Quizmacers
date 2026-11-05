from dataclasses import dataclass
import json
import os
import sys
from pathlib import Path
import tempfile


RANKS = (
    "Apprentice",
    "Initiate",
    "Novice",
    "Adept",
    "Conjurer",
    "Sorcerer",
    "Magus",
    "Grand Magus",
    "Archmage",
)
POINTS_PER_RANK = 10
SAVE_VERSION = 1


def save_path() -> Path:
    return Path(__file__).resolve().parent.parent / "progress.json"


def legacy_save_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "Quizmancers" / "progress.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Quizmancers" / "progress.json"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "quizmancers" / "progress.json"


def tier_for_rank(rank_index: int) -> int:
    if rank_index >= 8:
        return 4
    if rank_index >= 6:
        return 3
    if rank_index >= 3:
        return 2
    return 1


def appearance_for_rank(rank_index: int) -> int:
    return min(4, 1 + max(0, rank_index) // 2)


@dataclass
class Progress:
    points: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def rank_index(self) -> int:
        return min(len(RANKS) - 1, self.points // POINTS_PER_RANK)

    @property
    def title(self) -> str:
        return RANKS[self.rank_index]

    @property
    def spell_tier(self) -> int:
        return tier_for_rank(self.rank_index)

    @property
    def next_title(self) -> str | None:
        return RANKS[self.rank_index + 1] if self.rank_index < len(RANKS) - 1 else None

    @property
    def points_to_next(self) -> int:
        return max(0, (self.rank_index + 1) * POINTS_PER_RANK - self.points) if self.next_title else 0

    @property
    def rank_progress(self) -> float:
        return 1.0 if self.next_title is None else (self.points % POINTS_PER_RANK) / POINTS_PER_RANK

    def record(self, winner: str) -> "RankChange":
        before = self.points
        old_title = self.title
        if winner == "player":
            self.points += 1
            self.wins += 1
        elif winner == "ai":
            self.points = max(0, self.points - 1)
            self.losses += 1
        elif winner == "draw":
            self.draws += 1
        else:
            raise ValueError(f"Unknown match result: {winner}")
        return RankChange(winner, before, self.points, old_title, self.title)

    def to_dict(self) -> dict:
        return {
            "version": SAVE_VERSION,
            "points": self.points,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
        }

    @classmethod
    def from_dict(cls, value: object) -> "Progress":
        if not isinstance(value, dict) or value.get("version") != SAVE_VERSION:
            raise ValueError("Invalid save version")
        fields = ("points", "wins", "losses", "draws")
        if any(type(value.get(field)) is not int or value[field] < 0 for field in fields):
            raise ValueError("Invalid save data")
        return cls(*(value[field] for field in fields))


@dataclass(frozen=True)
class RankChange:
    winner: str
    before: int
    after: int
    old_title: str
    new_title: str

    @property
    def delta(self) -> int:
        return self.after - self.before

    @property
    def promoted(self) -> bool:
        return self.old_title != self.new_title and self.after > self.before

    @property
    def demoted(self) -> bool:
        return self.old_title != self.new_title and self.after < self.before


class ProgressStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else save_path()

    def load(self) -> Progress:
        try:
            return Progress.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            if self.path == save_path():
                try:
                    previous = Progress.from_dict(json.loads(legacy_save_path().read_text(encoding="utf-8")))
                    self.save(previous)
                    return previous
                except (OSError, ValueError, TypeError):
                    pass
            return Progress()
        except (OSError, ValueError, TypeError):
            return Progress()

    def save(self, progress: Progress) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent,
                                             prefix="progress_", suffix=".tmp", delete=False) as stream:
                temp_name = stream.name
                json.dump(progress.to_dict(), stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name is not None:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass
