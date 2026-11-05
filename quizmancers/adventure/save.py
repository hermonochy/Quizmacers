import json
import os
from pathlib import Path
import tempfile

from .model import AdventureProgress


class AdventureStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).resolve().parent.parent.parent / "adventure.json"

    def load(self) -> AdventureProgress:
        try:
            return AdventureProgress.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return AdventureProgress()

    def save(self, progress: AdventureProgress):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent,
                                             prefix="adventure_", suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                json.dump(progress.to_dict(), stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
