from dataclasses import dataclass
import random
import sqlite3


@dataclass(frozen=True)
class RevisionSummary:
    practised: int = 0
    attempts: int = 0
    correct: int = 0
    to_review: int = 0
    mastered: int = 0

    @property
    def accuracy(self) -> int:
        return round(self.correct * 100 / self.attempts) if self.attempts else 0


@dataclass(frozen=True)
class RevisionRecord:
    attempts: int = 0
    correct: int = 0
    incorrect: int = 0
    timeouts: int = 0
    streak: int = 0

    @property
    def needs_review(self) -> bool:
        return self.incorrect > 0 and self.streak < 3

    @property
    def mastered(self) -> bool:
        return self.streak >= 3

    @property
    def priority(self) -> float:
        if self.incorrect:
            if self.streak >= 3:
                return 0.55
            return 1.0 + min(12.0, 7.0 + self.incorrect * 1.0) / (2 ** self.streak)
        if self.correct:
            return 0.55 if self.streak < 3 else 0.38
        return 1.0


class RevisionTracker:
    def __init__(self, path, topic: str):
        self.path = path
        self.topic = topic
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT question_key, attempts, correct, incorrect, timeouts, streak "
                "FROM revision_progress WHERE topic = ?", (topic,)
            ).fetchall()
        self.records = {row[0]: RevisionRecord(*row[1:]) for row in rows}

    def get(self, question_key: str) -> RevisionRecord:
        return self.records.get(question_key, RevisionRecord())

    def priority(self, question_key: str) -> float:
        return self.get(question_key).priority

    def choose(self, candidates, recent, rng: random.Random):
        allowed = [question for question in candidates if question.key not in recent]
        if not allowed:
            allowed = list(candidates)
        if not any(self.get(question.key).needs_review for question in allowed):
            unseen = [question for question in allowed if self.get(question.key).attempts == 0]
            if unseen:
                allowed = unseen
        weights = [self.priority(question.key) for question in allowed]
        return rng.choices(allowed, weights=weights, k=1)[0]

    def record(self, question, correct: bool, timed_out: bool = False) -> RevisionRecord:
        previous = self.get(question.key)
        record = RevisionRecord(
            previous.attempts + 1,
            previous.correct + int(correct),
            previous.incorrect + int(not correct),
            previous.timeouts + int(timed_out),
            previous.streak + 1 if correct else 0,
        )
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO revision_progress "
                "(topic, question_key, attempts, correct, incorrect, timeouts, streak) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(topic, question_key) DO UPDATE SET "
                "attempts = excluded.attempts, correct = excluded.correct, "
                "incorrect = excluded.incorrect, timeouts = excluded.timeouts, streak = excluded.streak",
                (self.topic, question.key, record.attempts, record.correct,
                 record.incorrect, record.timeouts, record.streak),
            )
        self.records[question.key] = record
        return record

    def summary_for(self, keys) -> RevisionSummary:
        records = tuple(self.records[key] for key in keys if key in self.records)
        return RevisionSummary(
            len(records),
            sum(item.attempts for item in records),
            sum(item.correct for item in records),
            sum(item.needs_review for item in records),
            sum(item.mastered for item in records),
        )

    @property
    def summary(self) -> RevisionSummary:
        records = tuple(self.records.values())
        return RevisionSummary(
            len(records),
            sum(item.attempts for item in records),
            sum(item.correct for item in records),
            sum(item.needs_review for item in records),
            sum(item.mastered for item in records),
        )
