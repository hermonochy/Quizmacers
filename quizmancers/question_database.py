from collections import deque
from pathlib import Path
import random
import sqlite3

from .curriculum import ALL_SUBTOPICS, BOARDS, COMMON_BOARD, COURSES, StudySelection
from .maths_data import MATHS_QUESTIONS
from .maths_expansion import EXPANDED_MATHS
from .question_timing import estimate_solve_seconds
from .question_data import SEED_QUESTIONS, TOPICS
from .questions import MultipleChoiceQuestion
from .revision import RevisionSummary, RevisionTracker


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "questions.db"


class QuestionDatabase:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else DEFAULT_DATABASE_PATH

    def initialise(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY,
                    topic TEXT NOT NULL,
                    question TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_option INTEGER NOT NULL CHECK(correct_option BETWEEN 1 AND 4),
                    difficulty INTEGER NOT NULL DEFAULT 1 CHECK(difficulty BETWEEN 1 AND 4),
                    UNIQUE(topic, question)
                )
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(questions)")}
            for name, definition in (
                ("course", "TEXT NOT NULL DEFAULT 'KS3'"),
                ("board", "TEXT NOT NULL DEFAULT 'National Curriculum'"),
                ("subject", "TEXT NOT NULL DEFAULT ''"),
                ("subtopic", "TEXT NOT NULL DEFAULT 'General'"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE questions ADD COLUMN {name} {definition}")
            timing_added = "estimated_seconds" not in columns
            if timing_added:
                connection.execute("ALTER TABLE questions ADD COLUMN estimated_seconds REAL NOT NULL DEFAULT 25.0")
            connection.execute("UPDATE questions SET subject=topic WHERE subject='' OR subject IS NULL")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_curriculum ON questions(course, subject, board, subtopic)")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS revision_progress (
                    topic TEXT NOT NULL,
                    question_key TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    correct INTEGER NOT NULL DEFAULT 0,
                    incorrect INTEGER NOT NULL DEFAULT 0,
                    timeouts INTEGER NOT NULL DEFAULT 0,
                    streak INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(topic, question_key)
                )
            """)
            for topic, records in SEED_QUESTIONS.items():
                exists = connection.execute("SELECT 1 FROM questions WHERE topic=? LIMIT 1", (topic,)).fetchone()
                if exists:
                    continue
                connection.executemany("""
                    INSERT OR IGNORE INTO questions
                    (topic, question, option_a, option_b, option_c, option_d, correct_option, difficulty,
                     course, board, subject, subtopic)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 1, 'KS3', 'National Curriculum', ?, 'General')
                """, ((topic, *record, topic) for record in records))
            if timing_added:
                entries = connection.execute("SELECT id, course, subject, subtopic, question FROM questions").fetchall()
                connection.executemany(
                    "UPDATE questions SET estimated_seconds=? WHERE id=?",
                    ((estimate_solve_seconds(course, subject, subtopic, prompt), identity)
                     for identity, course, subject, subtopic, prompt in entries))
            for course, subjects in MATHS_QUESTIONS.items():
                for subtopic, records in subjects.items():
                    exists = connection.execute("""
                        SELECT 1 FROM questions
                        WHERE course=? AND board=? AND subject='Maths' AND subtopic=? LIMIT 1
                    """, (course, COMMON_BOARD, subtopic)).fetchone()
                    if exists:
                        continue
                    namespace = f"Maths::{course}::{COMMON_BOARD}::{subtopic}"
                    connection.executemany("""
                        INSERT OR IGNORE INTO questions
                        (topic, question, option_a, option_b, option_c, option_d, correct_option, difficulty,
                         course, board, subject, subtopic, estimated_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?, 'Maths', ?, ?)
                    """, ((namespace, *record, course, COMMON_BOARD, subtopic,
                            estimate_solve_seconds(course, 'Maths', subtopic, record[0])) for record in records))
            connection.executemany("""
                INSERT OR IGNORE INTO questions
                (topic, question, option_a, option_b, option_c, option_d, correct_option, difficulty,
                 course, board, subject, subtopic, estimated_seconds)
                VALUES (?, ?, ?, ?, ?, ?, 1, 2, ?, ?, 'Maths', ?, ?)
            """, ((f'Maths::{course}::{COMMON_BOARD}::{subtopic}', prompt, a, b, c, d,
                    course, COMMON_BOARD, subtopic, seconds)
                   for course, subtopic, prompt, a, b, c, d, seconds in EXPANDED_MATHS))

    def revision(self, topic: str) -> RevisionTracker:
        return RevisionTracker(self.path, topic)

    def revision_summary(self, topic: str) -> RevisionSummary:
        return self.revision(topic).summary

    def revision_for(self, selection: StudySelection) -> RevisionTracker:
        return self.revision(selection.revision_scope)

    def revision_summary_for(self, selection: StudySelection) -> RevisionSummary:
        tracker = self.revision_for(selection)
        if selection.subtopic == ALL_SUBTOPICS or selection.is_times_tables:
            return tracker.summary
        keys = {question.key for question in self.questions_for(selection)}
        return tracker.summary_for(keys)

    def topics(self) -> tuple[str, ...]:
        with sqlite3.connect(self.path) as connection:
            found = {row[0] for row in connection.execute("SELECT DISTINCT topic FROM questions WHERE subject!='Maths'")}
        return tuple(topic for topic in TOPICS if topic == "Times Tables" or topic in found) + tuple(sorted(found - set(TOPICS)))

    def questions(self, topic: str) -> list[MultipleChoiceQuestion]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("""
                SELECT id, question, option_a, option_b, option_c, option_d, correct_option, estimated_seconds
                FROM questions WHERE topic = ? ORDER BY id
            """, (topic,)).fetchall()
        return [MultipleChoiceQuestion(row[0], row[1], tuple(row[2:6]), row[6] - 1, topic, max(5.0, min(180.0, float(row[7])))) for row in rows]

    def courses(self) -> tuple[str, ...]:
        with sqlite3.connect(self.path) as connection:
            found = {row[0] for row in connection.execute("SELECT DISTINCT course FROM questions WHERE course!=''")}
        return tuple(course for course in COURSES if course in found) + tuple(sorted(found - set(COURSES)))

    def boards(self, course: str) -> tuple[str, ...]:
        known = BOARDS.get(course, ())
        with sqlite3.connect(self.path) as connection:
            found = {row[0] for row in connection.execute("SELECT DISTINCT board FROM questions WHERE course=?", (course,))}
        found.discard(COMMON_BOARD)
        return tuple(known) + tuple(sorted(found - set(known))) or ("National Curriculum",)

    def subjects(self, course: str, board: str) -> tuple[str, ...]:
        with sqlite3.connect(self.path) as connection:
            found = {row[0] for row in connection.execute("""
                SELECT DISTINCT subject FROM questions
                WHERE course=? AND board IN (?, ?) AND subject!=''
            """, (course, board, COMMON_BOARD))}
        return tuple(sorted(found, key=lambda name: (name != "Maths", name)))

    def subtopics(self, course: str, board: str, subject: str) -> tuple[str, ...]:
        with sqlite3.connect(self.path) as connection:
            found = {row[0] for row in connection.execute("""
                SELECT DISTINCT subtopic FROM questions
                WHERE course=? AND board IN (?, ?) AND subject=?
            """, (course, board, COMMON_BOARD, subject))}
        ordered = ("Times Tables",) if subject == "Maths" else ()
        rest = tuple(sorted(found - set(ordered)))
        if len(rest) > 1:
            return ordered + (ALL_SUBTOPICS,) + rest
        return ordered + rest

    def questions_for(self, selection: StudySelection) -> list[MultipleChoiceQuestion]:
        query = """
            SELECT id, question, option_a, option_b, option_c, option_d, correct_option, estimated_seconds
            FROM questions WHERE course=? AND subject=? AND board IN (?, ?)
        """
        params = [selection.course, selection.subject, selection.board, COMMON_BOARD]
        if selection.subtopic != ALL_SUBTOPICS:
            query += " AND subtopic=?"
            params.append(selection.subtopic)
        query += " ORDER BY id"
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [MultipleChoiceQuestion(row[0], row[1], tuple(row[2:6]), row[6] - 1,
                                       selection.subject, max(5.0, min(180.0, float(row[7])))) for row in rows]


class DatabaseBank:
    def __init__(self, database: QuestionDatabase, topic: str, rng: random.Random | None = None,
                 revision=None, selection: StudySelection | None = None):
        self.rng = rng or random.Random()
        self.revision = revision
        self.questions = database.questions_for(selection) if selection else database.questions(topic)
        if not self.questions:
            raise ValueError(f"No stored questions for topic: {topic}")
        self.pool = list(self.questions)
        self.rng.shuffle(self.pool)
        self.recent = deque(maxlen=min(8 if revision is None else 3, len(self.questions) - 1))

    def next_question(self) -> MultipleChoiceQuestion:
        if self.revision is not None:
            question = self.revision.choose(self.questions, self.recent, self.rng)
            self.recent.append(question.key)
            return question.shuffle(self.rng)
        for _ in range(len(self.questions) + 1):
            if not self.pool:
                self.pool = list(self.questions)
                self.rng.shuffle(self.pool)
            question = self.pool.pop()
            if question.question_id not in self.recent:
                self.recent.append(question.question_id)
                return question.shuffle(self.rng)
            self.pool.insert(0, question)
        question = self.pool.pop()
        self.recent.append(question.question_id)
        return question.shuffle(self.rng)
