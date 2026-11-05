from .model import AdventureProgress, Companion, Encounter, Lesson, Location, Portal
from ..curriculum import StudySelection


COMPANIONS = {
    "pip": Companion("pip", "Pip", "A small starling spirit who helps you learn and explore."),
    "ember": Companion("ember", "Ember", "A curious fire sprite with a talent for finding secrets."),
    "moss": Companion("moss", "Moss", "A patient woodland familiar who loves riddles."),
}


LESSONS = {
    "first_wand": Lesson("first_wand", "First Spells: Number Sense",
                         StudySelection("KS2 (SATs)", "National Curriculum", "Maths", "Place Value")),
    "tables": Lesson("tables", "The Multiplication Circle",
                     StudySelection("KS2 (SATs)", "National Curriculum", "Maths", "Times Tables")),
    "fractions": Lesson("fractions", "The Fraction Cauldron",
                        StudySelection("KS2 (SATs)", "National Curriculum", "Maths", "Fractions")),
    "algebra": Lesson("algebra", "Runes of Algebra",
                      StudySelection("KS3", "National Curriculum", "Maths", "Algebra")),
}


ENCOUNTERS = {
    "academy_trial": Encounter("academy_trial", "The School's Training Golem",
                               StudySelection("KS2 (SATs)", "National Curriculum", "Maths", "Times Tables")),
    "wood_spirit": Encounter("wood_spirit", "Bramble Wisp",
                             StudySelection("KS2 (SATs)", "National Curriculum", "Maths", "Fractions")),
    "tide_keeper": Encounter("tide_keeper", "The Tide Keeper",
                             StudySelection("KS3", "National Curriculum", "Maths", "Algebra")),
    "ember_guardian": Encounter("ember_guardian", "The Ember Guardian",
                                StudySelection("GCSE", "AQA", "Maths", "Geometry"), boss=True),
}


LOCATIONS = {
    "academy": Location("academy", "Starfall School of Wizardry",
                        "Meet your companion, attend maths lessons and practise spells.",
                        lessons=("first_wand", "tables", "fractions", "algebra"),
                        encounters=("academy_trial",),
                        portals=(Portal("whisperwood", "beacon_broken"),)),
    "whisperwood": Location("whisperwood", "Whisperwood",
                            "A forest whose ancient paths are hidden by broken magic.",
                            encounters=("wood_spirit",),
                            portals=(Portal("academy"), Portal("crystal_coast", "wood_spirit"))),
    "crystal_coast": Location("crystal_coast", "Crystal Coast",
                              "The sea has turned strange since the beacon's light failed.",
                              encounters=("tide_keeper",),
                              portals=(Portal("whisperwood"), Portal("ember_peaks", "tide_keeper"))),
    "ember_peaks": Location("ember_peaks", "Ember Peaks",
                             "A mountain temple guards the final shard of the beacon.",
                             encounters=("ember_guardian",),
                             portals=(Portal("crystal_coast"),)),
}


class AdventureWorld:
    def __init__(self):
        self.locations = LOCATIONS
        self.lessons = LESSONS
        self.encounters = ENCOUNTERS
        self.companions = COMPANIONS

    def new_game(self, companion: str = "pip") -> AdventureProgress:
        if companion not in self.companions:
            raise ValueError("Unknown companion")
        return AdventureProgress(companion=companion)

    def accessible_portals(self, progress: AdventureProgress) -> tuple[Location, ...]:
        location = self.locations[progress.location]
        return tuple(self.locations[portal.destination] for portal in location.portals
                     if not portal.required_flag or portal.required_flag in progress.flags
                     or portal.required_flag in progress.encounters_won)

    def travel(self, progress: AdventureProgress, destination: str) -> Location:
        destinations = {location.key for location in self.accessible_portals(progress)}
        if destination not in destinations:
            raise ValueError("Portal locked or unreachable")
        progress.location = destination
        progress.discovered.add(destination)
        return self.locations[destination]

    def study(self, progress: AdventureProgress, lesson_key: str, accuracy: float) -> bool:
        if lesson_key not in self.locations[progress.location].lessons:
            raise ValueError("Lesson not offered here")
        lesson = self.lessons[lesson_key]
        if not 0 <= accuracy <= 1:
            raise ValueError("Accuracy out of range")
        if accuracy < lesson.minimum_accuracy:
            return False
        progress.completed_lessons.add(lesson_key)
        return True

    def encounter(self, progress: AdventureProgress, encounter_key: str, victory: bool) -> bool:
        if encounter_key not in self.locations[progress.location].encounters:
            raise ValueError("Encounter not present")
        if encounter_key == "academy_trial" and not {"first_wand", "tables", "fractions"}.issubset(progress.completed_lessons):
            raise ValueError("Finish introductory lessons first")
        if not victory:
            return False
        progress.encounters_won.add(encounter_key)
        return True

    def story_event(self, progress: AdventureProgress) -> str | None:
        if "academy_trial" in progress.encounters_won and "beacon_broken" not in progress.flags:
            progress.flags.add("beacon_broken")
            return ("The Astral Beacon shatters during your graduation celebration. "
                    "Your companion senses its lost shards beyond the school's teleportation gates.")
        if "ember_guardian" in progress.encounters_won and "beacon_restored" not in progress.flags:
            progress.flags.add("beacon_restored")
            return "The final shard returns to the academy, and the Astral Beacon shines again."
        return None

    def study_selection_for(self, key: str) -> StudySelection:
        if key in self.lessons:
            return self.lessons[key].selection
        if key in self.encounters:
            return self.encounters[key].selection
        raise KeyError(key)

    def make_duel(self, key: str, database, rank_index: int, difficulty: str, pace: str):
        from ..combat import Duel
        return Duel(rank_index=rank_index, difficulty=difficulty, pace=pace,
                    selection=self.study_selection_for(key), database=database)
