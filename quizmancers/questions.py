from collections import deque
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Question:
    left: int
    right: int

    @property
    def expected_seconds(self) -> float:
        return 5.0

    @property
    def key(self) -> str:
        first, second = sorted((self.left, self.right))
        return f"times:{first}x{second}"

    @property
    def answer(self) -> int:
        return self.left * self.right

    @property
    def prompt(self) -> str:
        return f"{self.left}  ×  {self.right}  =  ?"

    @property
    def options(self) -> tuple:
        return ()

    def is_correct(self, response: str) -> bool:
        return response.strip().isdigit() and int(response.strip()) == self.answer


@dataclass(frozen=True)
class MultipleChoiceQuestion:
    question_id: int
    prompt: str
    options: tuple[str, str, str, str]
    correct_index: int
    topic: str
    expected_seconds: float = 25.0

    @property
    def key(self) -> str:
        return f"db:{self.question_id}"

    @property
    def answer(self) -> int:
        return self.correct_index + 1

    def is_correct(self, response: str) -> bool:
        return response.strip() == str(self.correct_index + 1)

    def shuffle(self, rng: random.Random) -> "MultipleChoiceQuestion":
        shuffled = list(enumerate(self.options))
        rng.shuffle(shuffled)
        correct = next(index for index, (old_index, _) in enumerate(shuffled) if old_index == self.correct_index)
        return MultipleChoiceQuestion(self.question_id, self.prompt, tuple(choice for _, choice in shuffled),
                                      correct, self.topic, self.expected_seconds)


class MultiplicationBank:
    def __init__(self, rng: random.Random | None = None, revision=None,
                 tables=None, multipliers=None):
        self.rng = rng or random.Random()
        self.revision = revision
        tables = tuple(tables) if tables is not None else tuple(range(2, 13))
        multipliers = tuple(multipliers) if multipliers is not None else tuple(range(2, 13))
        facts = {Question(left, right).key: Question(left, right)
                 for left in tables for right in multipliers}
        self.candidates = list(facts.values())
        self.recent = deque(maxlen=10 if revision is None else 4)

    def next_question(self) -> Question:
        if self.revision is not None:
            question = self.revision.choose(self.candidates, self.recent, self.rng)
            self.recent.append(question.key)
            if self.rng.random() < 0.5:
                return Question(question.right, question.left)
            return question
        for _ in range(50):
            question = self.rng.choice(self.candidates)
            if question.key not in self.recent:
                self.recent.append(question.key)
                if self.rng.random() < 0.5:
                    return Question(question.right, question.left)
                return question
        question = self.rng.choice(self.candidates)
        self.recent.append(question.key)
        return question
