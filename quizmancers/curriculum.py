from dataclasses import dataclass


COURSES = ("KS1", "KS2 (SATs)", "KS3", "GCSE", "IGCSE", "A level")
BOARDS = {
    "KS1": ("National Curriculum",),
    "KS2 (SATs)": ("National Curriculum",),
    "KS3": ("National Curriculum",),
    "GCSE": ("AQA", "Pearson Edexcel", "OCR", "Eduqas", "WJEC", "CCEA"),
    "IGCSE": ("Cambridge International", "Pearson Edexcel"),
    "A level": ("AQA", "Pearson Edexcel", "OCR A", "OCR B (MEI)", "WJEC", "CCEA"),
}
ALL_SUBTOPICS = "All subtopics"
COMMON_BOARD = "Common"


@dataclass(frozen=True)
class StudySelection:
    course: str = "KS2 (SATs)"
    board: str = "National Curriculum"
    subject: str = "Maths"
    subtopic: str = "Times Tables"

    @property
    def is_times_tables(self) -> bool:
        return self.subject == "Maths" and self.subtopic == "Times Tables"

    @property
    def title(self) -> str:
        return f"{self.subject} / {self.subtopic}"

    @property
    def revision_scope(self) -> str:
        if self.is_times_tables:
            return "Times Tables"
        if self.course == "KS3" and self.subject != "Maths" and self.subtopic in ("General", ALL_SUBTOPICS):
            return self.subject
        return f"{self.course}|{self.board}|{self.subject}"
