from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

from .pace import PACEs


@dataclass
class GameSettings:
    difficulty: str = "Duelist"
    pace: str = "Standard"

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        difficulty = data.get("difficulty", "Duelist")
        pace = data.get("pace", "Standard")
        return cls(difficulty if difficulty in ("Apprentice", "Duelist", "Archmage") else "Duelist",
                   pace if pace in PACEs else "Standard")


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).resolve().parent.parent / "settings.json"

    def load(self):
        try:
            return GameSettings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (FileNotFoundError, OSError, ValueError):
            return GameSettings()

    def save(self, settings):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="settings_", suffix=".tmp", delete=False) as stream:
                temp_name = stream.name
                json.dump({"difficulty": settings.difficulty, "pace": settings.pace}, stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)
