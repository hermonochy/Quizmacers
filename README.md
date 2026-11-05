# Quizmancers v1.2 — A Kinder Way to Cast

Quizmancers is a single-player Pygame revision battle game. Choose a course, exam board, subject and subtopic, answer questions, cast elemental spells, and work your way from Apprentice to Archmage.

## What's new in v1.2?

### Spell unstable! Try again!

A **wrong submitted answer** now triggers a **single short correction window** rather than immediately losing the spell. You have 3.5 seconds in Standard pace, 4.5 in Relaxed, and 3 seconds in Competitive. Correcting the answer still fires a spell at **72% of its usual power** and ends your combo. Making a second incorrect submission, or letting the correction timer expire, ends the question as a miscast and shows the correct answer.

A corrected answer is **still recorded as a mistake for adaptive revision**: you got a chance to save the spell, but the game knows this is something worth practising. This also avoids accidentally mastering questions just by guessing. There is only one correction per question.

For **times tables**, type your answer and press **Enter** to submit. **Backspace** lets you fix a typo before submitting. For **multiple-choice**, pressing **1–4** or clicking a choice now *selects* it without submitting. Press **Enter** to confirm, or click the same selected answer a second time. You may change your selection before confirming.

### Revision Pace

The main menu now includes a **PACE** selector next to AI difficulty. Click it or press **P** on the menu.

| Pace | Player question limit | AI solving speed | Ambient familiar attacks | Correction grace |
| --- | --- | --- | --- | --- |
| Relaxed | 150% of Standard | 45% longer to answer | Less frequent | 4.5 seconds |
| Standard | Original limits | Standard speed | Standard frequency | 3.5 seconds |
| Competitive | 85% of Standard | 13% faster | More frequent | 3 seconds |

These pace multipliers also adjust total duel duration and how strongly response speed contributes to damage. **AI difficulty** (Apprentice / Duelist / Archmage) remains a separate setting. The game remembers your selected pace and AI difficulty in `settings.json` beside `main.py`.

### Adventure mode foundation (not yet playable)

New independent modules in `quizmancers/adventure/` define the first chapter of a future story:

- **Starfall School of Wizardry:** Attend maths lessons on number sense, times tables, fractions and algebra.
- **Magical companion:** Begin with Pip, a starling spirit. Ember and Moss are also defined as future companion choices; companions are narrative/cosmetic for now.
- **Training duel:** Prove what you've learned against the academy's practice golem.
- **Inciting incident:** When you finish the academy trial, the Astral Beacon shatters.
- **Teleportation portals:** The school portal opens to Whisperwood. Further locations (Crystal Coast and Ember Peaks) open after their respective encounters.
- **Exploration, quests and encounters:** Each location defines story text and encounters tied to an existing maths subject/subtopic, with boss flags for later chapters.
- **Adventure-specific saving:** `AdventureStore` can save story progress in an independent `adventure.json` file beside `main.py`, without changing your wizard rank or question history.

`AdventureWorld.make_duel(...)` already constructs a normal Quizmancers battle using a story lesson or enemy's subject. The adventure world is currently **a tested game-logic foundation**; exploration, a map interface, companion animations, classroom scenes and adventure menus will be added later. Only the existing duel mode is playable in v1.2.

## Controls

| Screen | Controls |
| --- | --- |
| Main menu | Up/Down: select course/board/subject/subtopic; Left/Right: change; Tab: AI difficulty; **P: Revision Pace**; Enter: start |
| Battle | Q/W/E/R/T: fire, earth, water, air, spirit; digits: enter times-table answer or select choice; Enter: cast or confirm; Backspace: edit typed answer; Space: parry; H: guide |
| Results | R or Enter: rematch; M: return to menu |

You can also use the mouse for menu selectors and spells. For multiple-choice, select an answer with one click and cast with a second click on that answer, or by pressing Enter. The battle window can be resized.

## Run the game

Extract the ZIP, then from the folder containing `main.py` run:

```bash
pip install -r requirements.txt
python main.py
```

## Updating from v1.1

Extract the new ZIP into a fresh folder, then **copy your existing `progress.json` and `questions.db`** beside the new `main.py`. Keep backups of both files. Do not replace a newer `questions.db` with an older copy: it contains your adaptive revision records. Your saved rank and question history are retained. `settings.json` is new and created when you change the menu options.

## Tests

```bash
python -m unittest discover -s tests -q
```

The automated tests check the new correction window, question history, pace multipliers, save files, adventure portals, story state, and existing battle mechanics. The real Pygame interface still needs a local graphical playtest; the development environment could not install Pygame.

---

## v1.1 technical documentation

# Quizmancers v1.1 — Realistic question timings and more maths

Quizmancers is a Python/Pygame revision duel. Choose **course → exam board → subject → subtopic** on the main menu, then answer questions to cast elemental spells. The wizard's rank and available spell tier remain permanent and are determined by victories and defeats. The duel remains paced so you get to watch your spell resolve before your next question. v1.1 adds individual solving-time estimates to the question database, and the AI now uses those estimates instead of a times-tables pace.

## Run

Requires Python 3.10+ and Pygame 2.5+; SQLite is included with Python.

```bash
python -m pip install -r requirements.txt
python main.py
```

The game window is resizable. All save files are stored beside `main.py`.

## Choosing revision material

The menu has four selectable rows:

1. **Course:** KS1; KS2 (SATs); KS3; GCSE; IGCSE; A level.
2. **Exam board:** National Curriculum for KS1–KS3; AQA, Pearson Edexcel, OCR, Eduqas, WJEC or CCEA for GCSE; Cambridge International or Pearson Edexcel for IGCSE; AQA, Pearson Edexcel, OCR A, OCR B (MEI), WJEC or CCEA for A level.
3. **Subject:** The subjects with questions available for the selected course and board. Maths is currently available at every stage. The eight previous non-maths sample subjects are still selectable under KS3.
4. **Subtopic:** A focused question bank, **All subtopics** (mixing stored subtopics in that subject), or **Times Tables** where Maths is selected.

**Mouse:** click the left/right arrows beside any selection. **Keyboard:** Up/Down to highlight a field, Left/Right to change it, Enter to start, Tab to change AI difficulty. Duel controls are unchanged: Q/W/E/R/T for the five elements; type a times-table answer then Enter, or choose a multiple-choice answer with 1–4 or the mouse. Space parries; H opens the guide; Esc goes back.

Every question is an original **illustrative practice question**, not an official or verified board-specific past-paper question. Currently, GCSE, IGCSE and A-level board choices share the same introductory mathematics question pool for their course. **Board-specific rows can be added** and the menu/database will filter them correctly. The board selector therefore does not yet promise exact specification coverage or grading.

## What's in the question bank?

The included `questions.db` contains **827 multiple-choice questions**, including **526 additional unique maths questions** on top of v1.0's 301 questions. These are largely original, templated practice variations (not externally verified exam-board questions), so please review them for use in formal teaching. Maths focuses on these areas:

| Course | Stored maths subtopics |
| --- | --- |
| KS1 | Number Bonds; Place Value; Adding and Subtracting; Shapes and Measures |
| KS2 (SATs) | Fractions; Decimals and Percentages; Geometry; Measurement; Place Value |
| KS3 | Algebra; Fractions and Ratios; Number; Geometry; Probability and Statistics |
| GCSE | Number; Algebra; Geometry; Ratio and Proportion; Probability and Statistics |
| IGCSE | Number and Sets; Algebra and Graphs; Geometry and Trigonometry; Statistics and Probability |
| A level | Pure: Algebra; Calculus; Trigonometry; Statistics; Mechanics |

**Times Tables** are generated in code, not stored as fixed questions. Many additional maths questions, including integer-root quadratic equations, binomial expansions, linear equations, percentage problems, and introductory calculus, are pre-populated in SQLite. Correct answers are stored in the first option and shuffled at play time. KS1 uses 2, 5 and 10 times tables up to 10×; KS2 and above use 2–12 times tables. Times-table mistakes continue to be tracked as individual multiplication facts.

The other 128 sample questions are under **KS3**: Biology, Chemistry, Physics, Geography, History, English, Computing, and General Knowledge. Those original questions and their existing study histories are preserved during migration from v0.9.

## Adaptive revision and progress

Quizmancers remembers incorrect answers and timeouts, prioritises weak questions, and marks a question mastered after three correct responses in a row. The main menu displays the revision stats for your selected subtopic; **All subtopics** shows the subject-wide summary. Questions from different courses and boards have separate practice history, while questions within different subtopics of a course/board/subject share the same revision record. This means switching between Algebra and All subtopics does not lose your progress.

**Times Tables reuses the existing Times Tables revision history**, including mistakes saved by v0.9. The older KS3 non-maths topics likewise reuse their existing history.

## Realistic question timing

The game's earlier fixed timer made easy questions and multi-step algebra feel equally rushed. Every stored question now has an `estimated_seconds` field representing an approximate working-time expectation. The countdown gives a generous allowance (about 1.6 times the estimate plus 11 seconds), and the AI's answer time is scaled from the same estimate. Estimates are **design values**, not measured averages from real students; they can be edited as you gather playtest feedback.

| Question type | Typical estimate | Question countdown |
| --- | ---: | ---: |
| Times tables (generated) | 5 sec | 16 sec |
| Quick knowledge recall | 22 sec | ~47 sec |
| Straightforward linear algebra | 40 sec | ~76 sec |
| Expand two brackets | 59 sec | ~107 sec |
| Solve a GCSE quadratic | 80 sec | ~141 sec |
| Introductory integration | 73 sec | ~129 sec |

These values are examples; individual questions have their own estimates. The AI no longer fires a full question-generated spell every few seconds when the player is solving a quadratic. For a mixed-topic duel, the AI's timing uses the slower of its question and the player's current question, helping prevent an unfair mismatch. Automatic familiar bolts still appear, but both sides produce them.

Speed bonuses for spells are now calculated relative to the *expected solving time*, not a single universal timer. Harder topics can produce longer matches (up to nine minutes) so a complex question does not consume the entire duel. Times tables remain quick; **no combat controls changed**.

Winning still earns +1 rank point and losing -1, never below zero. Every ten points gives a new title, from Apprentice up to Archmage. Your unlocked spell tier and enemy strength scale with your permanent rank. These systems are unchanged.

## Upgrade from v1.0 (also supports older saves)

1. **Back up** your old `progress.json` and `questions.db`.
2. Extract the new v1.1 ZIP into a fresh folder.
3. Copy your **old** `progress.json` and `questions.db` into the folder containing the new `main.py`, replacing the supplied database if asked.
4. Run `python main.py`. Any missing curriculum/timing fields and additional maths questions will be added automatically. Your old questions, customised answer text, rank, and revision records will not be deleted.

If you have already used a newer database with more recent study records, do not overwrite it with an older copy. Keep backups when merging versions.

## SQLite data format

The question table keeps the original columns and adds these curriculum selectors:

| Column | Meaning |
| --- | --- |
| `id` | Stable unique question ID, used for revision history |
| `topic` | Legacy topic / unique namespace for a question set |
| `course` | `KS1`, `KS2 (SATs)`, `KS3`, `GCSE`, `IGCSE`, `A level`, or an added course |
| `board` | `Common` for shared questions, or a specific exam-board name |
| `subject` | `Maths`, `Biology`, etc. |
| `subtopic` | `Algebra`, `Calculus`, `Fractions`, etc. |
| `question` | Prompt text |
| `option_a` … `option_d` | Four possible answers |
| `correct_option` | Correct option number (1–4), before shuffling |
| `difficulty` | 1–4 (reserved for more granular question selection) |
| `estimated_seconds` | Approximate time a typical learner needs to solve the question; used for player deadline, AI pace, and spell power |

`revision_progress` remains a separate table, with each attempt recorded using a study scope and stable question key.

The user interface discovers available **subjects and subtopics from the database**, so adding another subject does not require rewriting the menu. To add a board-specific GCSE Biology question:

```python
import sqlite3

with sqlite3.connect("questions.db") as db:
    db.execute(
        """INSERT INTO questions
        (topic, course, board, subject, subtopic, question,
         option_a, option_b, option_c, option_d, correct_option, difficulty)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "GCSE_AQA_BIOLOGY_CELLS",
            "GCSE",
            "AQA",
            "Biology",
            "Cell Structure",
            "Which structure contains most of a human cell's DNA?",
            "Nucleus", "Cell wall", "Vacuole", "Ribosome", 1, 1,
        ),
    )
```

After a restart, GCSE → AQA → Biology → Cell Structure appears. This added question will not appear under GCSE → OCR. To share a question across every board for a course, set `board` to `Common`. Existing questions are only seeded into an empty topic/subtopic, so normal startups will not overwrite your existing edits. The seed data is in `quizmancers/maths_data.py` and `quizmancers/question_data.py`, and the migration/query logic is in `quizmancers/question_database.py`.

This format makes it possible to add further GCSE subjects, board-specific material, and A-level subjects later. **Curriculum coverage is currently a prototype**, so assess question quality and specification alignment before using it for serious exam preparation.

## Project layout

```text
Quizmancers/
  main.py
  questions.db                 SQLite questions and adaptive revision
  progress.json                created automatically after a completed duel
  quizmancers/
    curriculum.py              course and exam-board metadata
    maths_data.py              173 original seed maths questions
    question_data.py           existing 128 general-subject seed questions
    question_database.py       migrations and scoped question filtering
    revision.py                spaced practice and saving
    questions.py               times tables, multiple-choice classes
    game.py                    menu and controls
    combat.py                  duel and AI
    rendering.py               menu, arena and effects UI
    ...                        spell, audio, visual and viewport modules
  tests/
  requirements.txt
```

## Tests

```bash
python -m unittest discover -s tests -q
```

The automated suite covers combat, ranking, subject/course filtering, exam-board isolation, question shuffling, saved review, old-database migration, and times tables. A local graphical Pygame playtest is still recommended; this package was built in an environment without a usable Pygame display.

## Editing question times

You can change the expected working time for any question directly in SQLite without changing Python source code. For example:

```python
import sqlite3

with sqlite3.connect("questions.db") as connection:
    connection.execute(
        "UPDATE questions SET estimated_seconds=? WHERE id=?",
        (90.0, 123),
    )
```

Change `123` to the real question ID. The AI and player timer automatically adjust next time that question appears. For new questions, set `estimated_seconds` when you insert them (default is 25 seconds). The new `quizmancers/question_timing.py` module contains conservative guesses for existing old questions that didn't have timing data before migration. Your custom estimates are not overwritten on subsequent launches.

The expanded questions are generated by `quizmancers/maths_expansion.py` and inserted into `questions.db` on first run. After seeding, these are normal stored questions that you can edit. As before, new subtopics and subjects appear from the database without new menus or controls. Please avoid replacing a newer `questions.db` with an older one if it contains your revision history.

## Testing

```bash
python -m unittest discover -s tests -q
```
