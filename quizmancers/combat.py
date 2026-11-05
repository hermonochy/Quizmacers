from dataclasses import dataclass
import random

from .config import (
    AI_X,
    Element,
    MAX_HEALTH,
    MAX_SHIELD,
    PLAYER_X,
    PROJECTILE_Y,
    QUESTION_SECONDS,
    CHOICE_QUESTION_SECONDS,
    ROUND_SECONDS,
)
from .questions import MultiplicationBank
from .question_database import DatabaseBank, QuestionDatabase
from .curriculum import StudySelection
from .question_timing import ai_solve_delay, round_length_for, time_limit_for
from .spells import COUNTERS, ELEMENT_ORDER, spell_for
from .pace import pace_for
from .fusions import FUSION_COOLDOWN, FUSION_ELEMENTS, FUSION_KINDS, FUSION_WINDOW, fusion_for, potential_fusions


@dataclass
class Wizard:
    side: str
    x: float
    health: int = MAX_HEALTH
    shield: int = 0
    shield_remaining: float = 0.0
    level: int = 1
    combo: int = 0
    soaked_remaining: float = 0.0
    burn_remaining: float = 0.0
    burn_accumulator: float = 0.0
    hit_remaining: float = 0.0
    cast_remaining: float = 0.0
    casting_element: Element = Element.FIRE
    pulse_remaining: float = 0.0
    pulse_cooldown: float = 0.0
    bloom_remaining: float = 0.0
    bloom_tick: float = 0.0
    sanctuary_remaining: float = 0.0
    sanctuary_charges: int = 0
    familiar_timer: float = 5.5
    recent_element: Element | None = None
    fusion_window: float = 0.0
    fusion_cooldown: float = 0.0
    impact_element: Element = Element.FIRE
    impact_tier: int = 1

    @property
    def health_ratio(self) -> float:
        return max(0.0, self.health / MAX_HEALTH)



@dataclass
class Projectile:
    owner: str
    element: Element
    tier: int
    x: float
    y: float
    direction: int
    speed: int
    damage: int
    radius: int
    age: float = 0.0
    familiar: bool = False
    reflected: bool = False
    reaction_checked: bool = False
    phase: int = 0
    fusion: str = ""


@dataclass
class DelayedCast:
    delay: float
    side: str
    element: Element
    tier: int
    damage: int
    phase: int


@dataclass
class AreaEffect:
    side: str
    element: Element
    tier: int
    x: float
    y: float
    kind: str
    lifetime: float
    interval: float
    damage: int
    tick_elapsed: float = 0.0
    age: float = 0.0


@dataclass(frozen=True)
class DuelEvent:
    kind: str
    side: str
    x: float
    y: float
    message: str = ""
    amount: int = 0
    element: Element = Element.FIRE
    tier: int = 1


class AIController:
    def __init__(self, rng: random.Random, difficulty: str = "Duelist", rank_index: int = 0):
        self.rng = rng
        self.difficulty = difficulty
        self.rank_index = max(0, min(8, rank_index))

    def next_answer_time(self, wizard: Wizard | None = None, opponent: Wizard | None = None) -> float:
        pressure = max(wizard.level if wizard else 1, opponent.level if opponent else 1)
        ranges = {
            "Apprentice": (3.7, 5.9),
            "Duelist": (2.8, 4.5),
            "Archmage": (1.9, 3.25),
        }
        low, high = ranges.get(self.difficulty, ranges["Duelist"])
        return max(1.65, self.rng.uniform(low, high) * (1.0 - 0.020 * (pressure - 1)) * (1.0 - 0.004 * self.rank_index))

    def correct(self, wizard: Wizard | None = None, opponent: Wizard | None = None) -> bool:
        pressure = max(wizard.level if wizard else 1, opponent.level if opponent else 1)
        base, progress, cap = {
            "Apprentice": (0.76, 0.012, 0.80),
            "Duelist": (0.84, 0.015, 0.885),
            "Archmage": (0.92, 0.012, 0.96),
        }.get(self.difficulty, (0.84, 0.015, 0.885))
        return self.rng.random() < min(cap, base + progress * (pressure - 1) + 0.003 * self.rank_index)

    def choose_element(self, wizard: Wizard, opponent: Wizard) -> Element:
        opportunities = potential_fusions(wizard.recent_element) if wizard.fusion_window > 0 and wizard.fusion_cooldown <= 0 else ()
        fusion_chance = {"Apprentice": 0.08, "Duelist": 0.15, "Archmage": 0.48}.get(self.difficulty, 0.24)
        if opportunities and self.rng.random() < fusion_chance:
            if opponent.soaked_remaining > 0:
                lightning = [kind for kind, fusion in opportunities if fusion.kind == "chain_lightning"]
                if lightning:
                    return lightning[0]
            return self.rng.choice(opportunities)[0]
        if wizard.health < MAX_HEALTH * 0.65 and wizard.shield < 18 and self.rng.random() < 0.23:
            return Element.SPIRIT
        if wizard.shield < 12 and self.rng.random() < 0.13:
            return Element.SPIRIT
        if opponent.soaked_remaining > 0 and wizard.level >= 2 and self.rng.random() < 0.83:
            return Element.FIRE
        if opponent.shield > 18 and self.rng.random() < 0.68:
            return Element.EARTH
        if opponent.burn_remaining == 0 and opponent.soaked_remaining == 0 and self.rng.random() < 0.33:
            return Element.WATER
        return self.rng.choice(ELEMENT_ORDER[:4])


class Duel:
    def __init__(self, seed: int | None = None, difficulty: str = "Duelist", rank_index: int = 0,
                 topic: str = "Times Tables", database: QuestionDatabase | None = None,
                 selection: StudySelection | None = None, pace: str = "Standard"):
        self.rng = random.Random(seed)
        self.selection = selection
        self.topic = selection.title if selection is not None else topic
        self.is_times_tables = selection.is_times_tables if selection is not None else topic == "Times Tables"
        if database is not None:
            database.initialise()
        self.revision = (database.revision_for(selection) if selection is not None else database.revision(topic)) if database is not None else None
        ai_rng = random.Random(self.rng.randrange(1 << 48))
        if self.is_times_tables:
            tables = (2, 5, 10) if selection is not None and selection.course == "KS1" else None
            multipliers = tuple(range(1, 11)) if tables is not None else None
            self.bank = MultiplicationBank(self.rng, self.revision, tables, multipliers)
            self.ai_bank = MultiplicationBank(ai_rng, None, tables, multipliers)
        else:
            database = database or QuestionDatabase()
            database.initialise()
            self.bank = DatabaseBank(database, topic, self.rng, self.revision, selection=selection)
            self.ai_bank = DatabaseBank(database, topic, ai_rng, selection=selection)
        self.pace = pace_for(pace)
        self.difficulty = difficulty if difficulty in ("Apprentice", "Duelist", "Archmage") else "Duelist"
        from .progression import tier_for_rank
        self.rank_index = max(0, min(8, rank_index))
        spell_tier = tier_for_rank(self.rank_index)
        self.ai_controller = AIController(self.rng, self.difficulty, self.rank_index)
        self.player = Wizard("player", PLAYER_X, level=spell_tier, familiar_timer=4.7)
        self.ai = Wizard("ai", AI_X, level=spell_tier, familiar_timer=5.7)
        self.player_question = self.bank.next_question()
        self.ai_question = self.ai_bank.next_question()
        self.question_duration = time_limit_for(self.player_question) * self.pace.deadline_scale
        self.ai_question_duration = max(time_limit_for(self.ai_question),
                                        time_limit_for(self.player_question)) * self.pace.deadline_scale
        self.round_duration = (ROUND_SECONDS if self.is_times_tables else round_length_for(
            [question.expected_seconds for question in self.bank.questions])) * self.pace.deadline_scale
        self.player_question_elapsed = 0.0
        self.ai_question_elapsed = 0.0
        self.ai_answer_at = self._ai_answer_delay()
        self.selected_element = Element.FIRE
        self.projectiles: list[Projectile] = []
        self.delayed: list[DelayedCast] = []
        self.areas: list[AreaEffect] = []
        self.events: list[DuelEvent] = []
        self.elapsed = 0.0
        self.player_waiting = False
        self.ai_waiting = False
        self.player_recovery = 0.0
        self.ai_recovery = 0.0
        self.player_feedback = ""
        self.retry_remaining = 0.0
        self.retry_used = False
        self.winner: str | None = None
        self.finished = False

    def _ai_answer_delay(self) -> float:
        if self.is_times_tables:
            return self.ai_controller.next_answer_time(self.ai, self.player) * 1.22 * self.pace.ai_delay_scale
        estimate = max(self.ai_question.expected_seconds, self.player_question.expected_seconds)
        return ai_solve_delay(estimate, self.difficulty, self.rank_index,
                              self.rng, self.ai.level) * self.pace.ai_delay_scale

    @property
    def player_question_active(self) -> bool:
        return not self.finished and not self.player_waiting

    @property
    def player_question_is_review(self) -> bool:
        return self.revision is not None and self.revision.get(self.player_question.key).needs_review

    @property
    def seconds_left(self) -> float:
        return max(0.0, self.round_duration - self.elapsed)

    @property
    def question_seconds_left(self) -> float:
        if self.retry_remaining > 0:
            return self.retry_remaining
        return max(0.0, self.question_duration - self.player_question_elapsed)

    @property
    def ai_thinking_ratio(self) -> float:
        return 0.0 if self.ai_waiting else min(1.0, self.ai_question_elapsed / max(0.1, self.ai_answer_at))

    def player_fusion_options(self) -> tuple[tuple[Element, object], ...]:
        if self.player.fusion_window <= 0 or self.player.fusion_cooldown > 0:
            return ()
        return potential_fusions(self.player.recent_element)

    def select_element(self, element: Element) -> None:
        if not self.finished and element in ELEMENT_ORDER:
            self.selected_element = element

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty in ("Apprentice", "Duelist", "Archmage"):
            self.difficulty = difficulty
            self.ai_controller.difficulty = difficulty
            remaining_fraction = max(0.0, 1.0 - self.ai_thinking_ratio)
            new_total = self._ai_answer_delay()
            self.ai_answer_at = self.ai_question_elapsed + new_total * remaining_fraction

    def _wizard(self, side: str) -> Wizard:
        return self.player if side == "player" else self.ai

    def _opponent(self, side: str) -> Wizard:
        return self.ai if side == "player" else self.player

    def _finalise_miscast(self, timed_out: bool = False) -> None:
        if self.revision is not None:
            self.revision.record(self.player_question, False, timed_out=timed_out)
        expected = (self.player_question.options[self.player_question.correct_index]
                    if self.player_question.options else str(self.player_question.answer))
        self.player_feedback = f"Correct answer: {expected}"
        self.player.combo = 0
        self.player.recent_element = None
        self.player.fusion_window = 0.0
        self.retry_remaining = 0.0
        self.player_waiting = True
        self.player_recovery = 2.2
        self._event("timeout" if timed_out else "answer_wrong", "player", self.player.x,
                    259, "TIME UP!" if timed_out else "MISCAST!", 0)

    def submit_answer(self, answer: str) -> bool | None:
        if self.finished or self.player_waiting:
            return None
        normalized = answer.strip()
        if not normalized.isdigit():
            return None
        if self.player_question.options and normalized not in ("1", "2", "3", "4"):
            return None
        correct = self.player_question.is_correct(normalized)
        if correct:
            if self.revision is not None:
                self.revision.record(self.player_question, not self.retry_used)
            self.player_feedback = ""
            self._answer_success("player", self.selected_element, self.player_question_elapsed,
                                 0.72 if self.retry_used else 1.0)
            if self.retry_used:
                self._event("answer_correct", "player", self.player.x, 283,
                            "RECOVERED CAST!", 0, self.selected_element, self.player.level)
            self.retry_remaining = 0.0
            self.player_waiting = True
            self.player_recovery = 0.9
        elif not self.retry_used:
            self.retry_used = True
            self.retry_remaining = self.pace.retry_seconds
            self.player.combo = 0
            self.player.recent_element = None
            self.player.fusion_window = 0.0
            self.player_feedback = "SPELL UNSTABLE! TRY AGAIN!"
            self._event("retry", "player", self.player.x, 260, "SPELL UNSTABLE!", 0)
        else:
            self._finalise_miscast()
        return correct

    def activate_pulse(self, side: str = "player") -> bool:
        if self.finished:
            return False
        wizard = self._wizard(side)
        if wizard.pulse_cooldown > 0:
            return False
        wizard.pulse_remaining = 0.62
        wizard.pulse_cooldown = 6.2
        self._event("pulse", side, wizard.x, PROJECTILE_Y, "ARCANE PARRY", 0, Element.SPIRIT, wizard.level)
        return True

    def _next_player_question(self) -> None:
        self.player_question = self.bank.next_question()
        self.question_duration = time_limit_for(self.player_question) * self.pace.deadline_scale
        self.ai_question_duration = max(self.ai_question_duration, self.question_duration)
        self.player_question_elapsed = 0.0
        self.retry_remaining = 0.0
        self.retry_used = False

    def _next_ai_question(self) -> None:
        self.ai_question = self.ai_bank.next_question()
        self.ai_question_duration = max(time_limit_for(self.ai_question),
                                        time_limit_for(self.player_question)) * self.pace.deadline_scale
        self.ai_question_elapsed = 0.0
        self.ai_answer_at = max(0.85, self._ai_answer_delay())

    def _event(self, kind: str, side: str, x: float, y: float, message: str = "", amount: int = 0,
               element: Element = Element.FIRE, tier: int = 1) -> None:
        self.events.append(DuelEvent(kind, side, x, y, message, amount, element, tier))

    def pop_events(self) -> list[DuelEvent]:
        events = self.events
        self.events = []
        return events

    def _answer_success(self, side: str, element: Element, answer_time: float, power_scale: float = 1.0) -> None:
        wizard = self._wizard(side)
        wizard.combo = min(6, wizard.combo + 1)
        power = self._cast(side, element, answer_time, power_scale)
        self._try_fusion(side, element, power)
        if side == "player":
            message = f"{spell_for(element, wizard.level).name.upper()}!  "
            message += f"{wizard.combo}x COMBO" if wizard.combo > 1 else "NICE CAST!"
            self._event("answer_correct", side, wizard.x, 259, message, power, element, wizard.level)

    def _launch(self, side: str, element: Element, tier: int, damage: int,
                phase: int = 0, familiar: bool = False, reflected: bool = False,
                fusion: str = "") -> None:
        wizard = self._wizard(side)
        spec = spell_for(element, tier)
        direction = 1 if side == "player" else -1
        x = wizard.x + 64 * direction
        radius = max(5, int(spec.radius * (0.55 if familiar else 0.78 if phase else 1.0)))
        if fusion:
            radius = 20 + tier * 4
        speed = (max(590, spec.travel_speed) + 100) if fusion else spec.travel_speed + (230 if familiar else 55 if phase else 0)
        y = PROJECTILE_Y - 45 if fusion else PROJECTILE_Y + ((phase % 3) - 1) * 31 if phase else PROJECTILE_Y
        self.projectiles.append(Projectile(side, element, tier, x, y, direction, speed,
                                           max(1, damage), radius, familiar=familiar,
                                           reflected=reflected, phase=phase, fusion=fusion))
        if not fusion:
            self._event("familiar" if familiar else "cast", side, x, y,
                        "ARCANE SPARK" if familiar else spec.name.upper(), damage, element, tier)

    def _try_fusion(self, side: str, element: Element, power: int) -> None:
        wizard = self._wizard(side)
        fusion = fusion_for(wizard.recent_element, element) if wizard.fusion_window > 0 and wizard.fusion_cooldown <= 0 else None
        if fusion:
            damage = max(4, round(power * (0.14 + wizard.level * 0.01)))
            self._launch(side, element, wizard.level, damage, fusion=fusion.kind)
            self._event("fusion_cast", side, wizard.x, PROJECTILE_Y - 45,
                        fusion.name.upper(), damage, FUSION_ELEMENTS[fusion.kind], wizard.level)
            wizard.recent_element = None
            wizard.fusion_window = 0.0
            wizard.fusion_cooldown = FUSION_COOLDOWN
        else:
            wizard.recent_element = element if element != Element.SPIRIT else None
            wizard.fusion_window = FUSION_WINDOW if wizard.recent_element is not None else 0.0

    def _cast(self, side: str, element: Element, answer_time: float, power_scale: float = 1.0) -> int:
        wizard = self._wizard(side)
        spec = spell_for(element, wizard.level)
        expected = max(5.0, (self.player_question.expected_seconds if side == 'player'
                    else self.ai_question.expected_seconds))
        speed_factor = max(0.0, 1.0 - min(answer_time, expected * 1.5) / (expected * 1.5))
        combo_bonus = 1.0 + min(0.2, (wizard.combo - 1) * 0.04)
        power = max(1, round((spec.power + spec.speed_bonus * speed_factor * self.pace.speed_bonus_scale)
                             * combo_bonus * power_scale))
        if side == "ai":
            power = max(1, round(power * {"Apprentice": 0.62, "Duelist": 0.77,
                                           "Archmage": 1.0}[self.difficulty]))
        wizard.cast_remaining = 0.64 if wizard.level >= 3 else 0.5
        wizard.casting_element = element
        if wizard.level >= 4:
            self._event("ultimate_cast", side, wizard.x, PROJECTILE_Y,
                        spec.name.upper(), power, element, wizard.level)
        if element == Element.SPIRIT:
            original = wizard.shield
            wizard.shield = min(MAX_SHIELD, wizard.shield + power)
            wizard.shield_remaining = 8.0 if wizard.level < 4 else 10.0
            healed = min(MAX_HEALTH - wizard.health, spec.heal)
            wizard.health += healed
            if wizard.level >= 3:
                wizard.bloom_remaining = 3.2 if wizard.level == 3 else 5.0
                wizard.bloom_tick = 0.0
            if wizard.level == 4:
                wizard.sanctuary_remaining = 5.0
                wizard.sanctuary_charges = 1
            self._event("ward", side, wizard.x, 327,
                        f"+{wizard.shield - original} WARD" + (f"  +{healed} HP" if healed else ""),
                        wizard.shield - original, element, wizard.level)
            return wizard.shield - original
        if element == Element.AIR:
            wizard.soaked_remaining = 0.0
        main_ratio = 1.0
        if wizard.level >= 3:
            if element == Element.FIRE and wizard.level == 3:
                main_ratio = 0.76
                self.delayed.extend((DelayedCast(0.32, side, element, 3, round(power * 0.39), 1),
                                     DelayedCast(0.72, side, element, 3, round(power * 0.39), 2)))
            elif element == Element.AIR and wizard.level == 4:
                main_ratio = 0.7
                for i in range(1, 4):
                    self.delayed.append(DelayedCast(0.18 * i, side, element, 4,
                                                    round(power * 0.32), i))
            elif element in (Element.EARTH, Element.WATER, Element.AIR, Element.FIRE):
                main_ratio = 0.82 if wizard.level == 3 else 0.94
        self._launch(side, element, wizard.level, round(power * main_ratio))
        return power

    def _apply_damage(self, target: Wizard, damage: int, element: Element, tier: int,
                      trait: str = "") -> tuple[int, int]:
        pierce = round(damage * 0.22) if trait == "pierce" else 0
        shield_force = damage - pierce
        if trait == "shatter":
            shield_force = round(shield_force * 1.6)
        absorbed = min(target.shield, shield_force)
        target.shield -= absorbed
        residual = max(0, damage - pierce - (absorbed / 1.6 if trait == "shatter" else absorbed))
        actual = min(target.health, pierce + round(residual))
        target.health -= actual
        if actual or absorbed:
            target.hit_remaining = max(target.hit_remaining, 0.34 + 0.055 * tier)
            target.impact_element = element
            target.impact_tier = tier
        return actual, absorbed

    def _hit(self, projectile: Projectile) -> None:
        target = self._opponent(projectile.owner)
        if target.pulse_remaining > 0 or (target.sanctuary_charges and target.sanctuary_remaining > 0):
            if target.pulse_remaining > 0:
                target.pulse_remaining = 0
            else:
                target.sanctuary_charges -= 1
            self._event("parry", target.side, target.x, projectile.y,
                        "REFLECT!", 0, Element.SPIRIT, target.level)
            if not projectile.reflected:
                counter_element = projectile.element
                self._launch(target.side, counter_element, min(target.level, projectile.tier),
                             max(4, round(projectile.damage * 0.42)), familiar=True, reflected=True)
            return
        spec = spell_for(projectile.element, projectile.tier)
        damage = projectile.damage
        if projectile.fusion:
            if projectile.fusion == "chain_lightning" and target.soaked_remaining > 0:
                damage = round(damage * 1.25)
                target.soaked_remaining = 0.0
            elif projectile.fusion == "flame_tornado":
                target.burn_remaining = max(target.burn_remaining, 2.0)
            elif projectile.fusion == "mudslide":
                target.soaked_remaining = max(target.soaked_remaining, 3.0)
            trait = "shatter" if projectile.fusion == "mudslide" else ""
            primary = FUSION_ELEMENTS[projectile.fusion]
            actual, absorbed = self._apply_damage(target, damage, primary, projectile.tier, trait)
            self._event("fusion_hit", target.side, target.x, projectile.y,
                        FUSION_KINDS[projectile.fusion].name.upper(), actual,
                        primary, projectile.tier)
            if absorbed:
                self._event("block", target.side, target.x, projectile.y,
                            "BLOCKED", absorbed, Element.SPIRIT, projectile.tier)
            self._make_fusion_area(projectile, target)
            return
        if spec.trait == "lightning" and target.soaked_remaining > 0 and not projectile.familiar:
            damage = round(damage * 1.35)
            target.soaked_remaining = 0.0
            self._event("combo", target.side, target.x, 277, "CONDUCTIVE!", 0, projectile.element, projectile.tier)
        if not projectile.familiar:
            if projectile.element == Element.WATER:
                target.burn_remaining = 0.0
                target.burn_accumulator = 0.0
                target.soaked_remaining = 4.8
            elif spec.trait == "burn":
                target.burn_remaining = 2.5 + 0.45 * projectile.tier
                target.burn_accumulator = 0.0
        trait = "" if projectile.familiar else spec.trait
        actual, absorbed = self._apply_damage(target, damage, projectile.element, projectile.tier, trait)
        self._event("hit", target.side, target.x, projectile.y,
                    f"-{actual} HP" if actual else "BLOCKED!", actual, projectile.element, projectile.tier)
        if absorbed:
            self._event("block", target.side, target.x, projectile.y,
                        "SHIELD CRACK!" if trait == "shatter" else "BLOCKED", absorbed,
                        Element.SPIRIT, projectile.tier)
        if not projectile.familiar and projectile.tier >= 3 and projectile.phase == 0:
            self._make_area(projectile, target)

    def _make_fusion_area(self, projectile: Projectile, target: Wizard) -> None:
        fusion = FUSION_KINDS[projectile.fusion]
        existing = next((area for area in self.areas if area.kind == fusion.kind and area.side == projectile.owner), None)
        if existing is not None:
            existing.lifetime = max(existing.lifetime, fusion.lifetime)
            return
        self.areas.append(AreaEffect(
            projectile.owner, FUSION_ELEMENTS[projectile.fusion], projectile.tier, target.x,
            PROJECTILE_Y, fusion.kind, fusion.lifetime, fusion.interval,
            1 + projectile.tier
        ))
        self._event("fusion_zone", target.side, target.x, PROJECTILE_Y,
                    fusion.name.upper(), 0, FUSION_ELEMENTS[projectile.fusion], projectile.tier)

    def _make_area(self, projectile: Projectile, target: Wizard) -> None:
        element, tier = projectile.element, projectile.tier
        kind = {
            Element.FIRE: "inferno" if tier == 4 else "",
            Element.EARTH: "cataclysm" if tier == 4 else "quake",
            Element.WATER: "maelstrom" if tier == 4 else "surge",
            Element.AIR: "" if tier == 4 else "cyclone",
        }.get(element, "")
        if not kind:
            return
        data = {
            "inferno": (3.3, 0.65, 5),
            "quake": (1.9, 0.6, 5),
            "cataclysm": (3.4, 0.68, 7),
            "surge": (1.9, 0.6, 3),
            "maelstrom": (3.8, 0.58, 4),
            "cyclone": (2.4, 0.58, 5),
        }
        lifetime, interval, damage = data[kind]
        self.areas.append(AreaEffect(projectile.owner, element, tier, target.x, PROJECTILE_Y,
                                     kind, lifetime, interval, damage))
        self._event("area_spawn", target.side, target.x, PROJECTILE_Y,
                    kind.upper(), 0, element, tier)

    def _update_areas(self, dt: float) -> None:
        living = []
        for area in self.areas:
            area.lifetime -= dt
            area.age += dt
            area.tick_elapsed += dt
            target = self._opponent(area.side)
            while area.tick_elapsed >= area.interval and area.lifetime > 0:
                area.tick_elapsed -= area.interval
                actual, absorbed = self._apply_damage(target, area.damage, area.element, area.tier)
                if area.kind in ("surge", "maelstrom", "mudslide"):
                    target.soaked_remaining = max(target.soaked_remaining, 2.0)
                self._event("area_tick", target.side, target.x, PROJECTILE_Y,
                            f"-{actual} {area.kind.upper()}", actual, area.element, area.tier)
                if area.kind == "flame_tornado":
                    target.burn_remaining = max(target.burn_remaining, 0.6)
                if absorbed:
                    self._event("block", target.side, target.x, PROJECTILE_Y,
                                "BLOCKED", absorbed, Element.SPIRIT, area.tier)
            if area.lifetime > 0:
                living.append(area)
        self.areas = living

    def _clash_projectiles(self, dt: float) -> None:
        removed: set[int] = set()
        for i, first in enumerate(self.projectiles):
            if i in removed:
                continue
            for j in range(i + 1, len(self.projectiles)):
                if j in removed:
                    continue
                second = self.projectiles[j]
                if first.owner == second.owner or first.familiar != second.familiar:
                    continue
                close = abs(first.x - second.x) <= first.radius + second.radius + 6
                previous_first = first.x - first.speed * first.direction * dt
                previous_second = second.x - second.speed * second.direction * dt
                crossed = (previous_first - previous_second) * (first.x - second.x) <= 0
                if not close and not crossed:
                    continue
                self._event("clash", "center", (first.x + second.x) / 2, PROJECTILE_Y,
                            "SPELL CLASH!", 0, first.element, max(first.tier, second.tier))
                if COUNTERS.get(first.element) == second.element:
                    removed.add(j)
                    first.damage = max(1, round(first.damage * 0.65))
                elif COUNTERS.get(second.element) == first.element:
                    removed.add(i)
                    second.damage = max(1, round(second.damage * 0.65))
                elif first.damage > second.damage * 1.45:
                    removed.add(j)
                    first.damage = max(1, first.damage - round(second.damage * 0.5))
                elif second.damage > first.damage * 1.45:
                    removed.add(i)
                    second.damage = max(1, second.damage - round(first.damage * 0.5))
                else:
                    removed.update((i, j))
                if i in removed:
                    break
        if removed:
            self.projectiles = [shot for index, shot in enumerate(self.projectiles) if index not in removed]

    def _update_wizard(self, wizard: Wizard, dt: float) -> None:
        wizard.hit_remaining = max(0.0, wizard.hit_remaining - dt)
        wizard.fusion_window = max(0.0, wizard.fusion_window - dt)
        wizard.fusion_cooldown = max(0.0, wizard.fusion_cooldown - dt)
        if wizard.fusion_window <= 0:
            wizard.recent_element = None
        wizard.cast_remaining = max(0.0, wizard.cast_remaining - dt)
        wizard.pulse_remaining = max(0.0, wizard.pulse_remaining - dt)
        wizard.pulse_cooldown = max(0.0, wizard.pulse_cooldown - dt)
        wizard.soaked_remaining = max(0.0, wizard.soaked_remaining - dt)
        wizard.sanctuary_remaining = max(0.0, wizard.sanctuary_remaining - dt)
        if wizard.sanctuary_remaining <= 0:
            wizard.sanctuary_charges = 0
        if wizard.shield_remaining > 0:
            wizard.shield_remaining = max(0.0, wizard.shield_remaining - dt)
            if wizard.shield_remaining == 0:
                wizard.shield = 0
        if wizard.bloom_remaining > 0:
            wizard.bloom_remaining = max(0.0, wizard.bloom_remaining - dt)
            wizard.bloom_tick += dt
            while wizard.bloom_tick >= 1.0 and wizard.bloom_remaining > 0:
                wizard.bloom_tick -= 1.0
                heal = min(4 if wizard.level >= 4 else 3, MAX_HEALTH - wizard.health)
                wizard.health += heal
                if heal:
                    self._event("bloom", wizard.side, wizard.x, 307, f"+{heal} HP", heal,
                                Element.SPIRIT, wizard.level)
        if wizard.burn_remaining > 0:
            active_time = min(dt, wizard.burn_remaining)
            wizard.burn_remaining = max(0.0, wizard.burn_remaining - dt)
            wizard.burn_accumulator += active_time
            while wizard.burn_accumulator >= 1.0:
                wizard.burn_accumulator -= 1.0
                if wizard.health > 0:
                    wizard.health = max(0, wizard.health - 3)
                    wizard.hit_remaining = max(wizard.hit_remaining, 0.17)
                    self._event("burn", wizard.side, wizard.x, 318, "-3 BURN", 3, Element.FIRE)
        else:
            wizard.burn_accumulator = 0.0
        wizard.familiar_timer -= dt
        if wizard.familiar_timer <= 0:
            wizard.familiar_timer += 6.6 * self.pace.familiar_interval_scale
            element = wizard.casting_element if wizard.casting_element != Element.SPIRIT else Element.AIR
            self._launch(wizard.side, element, wizard.level, 3 + wizard.level, familiar=True)

    def _update_delayed(self, dt: float) -> None:
        remaining = []
        for cast in self.delayed:
            cast.delay -= dt
            if cast.delay <= 0:
                self._launch(cast.side, cast.element, cast.tier, cast.damage, phase=cast.phase)
            else:
                remaining.append(cast)
        self.delayed = remaining

    def _update_projectiles(self, dt: float) -> None:
        for shot in self.projectiles:
            shot.age += dt
            shot.x += shot.speed * shot.direction * dt
        self._clash_projectiles(dt)
        remaining = []
        for shot in self.projectiles:
            target = self._opponent(shot.owner)
            if target.side == "ai" and not shot.reaction_checked and not shot.familiar:
                distance = abs(shot.x - target.x)
                if 85 < distance < 170:
                    shot.reaction_checked = True
                    parry_chance = (0.05 + 0.025 * (target.level - 1)) * {
                        "Apprentice": 0.5, "Duelist": 1.0, "Archmage": 1.8
                    }[self.difficulty]
                    if target.pulse_cooldown == 0 and self.rng.random() < parry_chance:
                        self.activate_pulse("ai")
            target_x = target.x - 40 if shot.direction > 0 else target.x + 40
            if (shot.direction > 0 and shot.x >= target_x) or (shot.direction < 0 and shot.x <= target_x):
                self._hit(shot)
            else:
                remaining.append(shot)
        self.projectiles = remaining

    def _finish_if_needed(self) -> None:
        if self.player.health <= 0 or self.ai.health <= 0 or self.elapsed >= self.round_duration:
            if self.player.health > self.ai.health:
                self.winner = "player"
            elif self.ai.health > self.player.health:
                self.winner = "ai"
            else:
                self.winner = "draw"
            self.finished = True
            self._event("finish", self.winner, 590, 297)

    def _spell_in_flight(self, side: str) -> bool:
        return (any(shot.owner == side and not shot.familiar for shot in self.projectiles)
                or any(cast.side == side for cast in self.delayed))

    def _resolve_recovery(self, dt: float) -> None:
        if self.player_waiting:
            self.player_recovery = max(0.0, self.player_recovery - dt)
            if self.player_recovery <= 0.0 and not self._spell_in_flight("player"):
                self.player_waiting = False
                self.player_feedback = ""
                self._next_player_question()
                self._event("question_ready", "player", self.player.x, 260, "NEXT QUESTION")
        if self.ai_waiting:
            self.ai_recovery = max(0.0, self.ai_recovery - dt)
            if self.ai_recovery <= 0.0 and not self._spell_in_flight("ai"):
                self.ai_waiting = False
                self._next_ai_question()

    def update(self, dt: float) -> None:
        if self.finished:
            return
        dt = max(0.0, min(0.1, dt))
        self.elapsed += dt
        if not self.player_waiting:
            if self.retry_remaining > 0:
                self.retry_remaining = max(0.0, self.retry_remaining - dt)
                if self.retry_remaining == 0.0:
                    self._finalise_miscast()
            else:
                self.player_question_elapsed += dt
        if not self.ai_waiting:
            self.ai_question_elapsed += dt
        for wizard in (self.player, self.ai):
            self._update_wizard(wizard, dt)
        self._update_delayed(dt)
        self._update_areas(dt)
        self._update_projectiles(dt)
        self._resolve_recovery(dt)
        self._finish_if_needed()
        if self.finished:
            return
        if not self.player_waiting and self.retry_remaining <= 0 and self.player_question_elapsed >= self.question_duration:
            self._finalise_miscast(timed_out=True)
        if not self.ai_waiting and self.ai_question_elapsed >= min(self.ai_answer_at, self.ai_question_duration):
            if self.ai_answer_at <= self.ai_question_duration and self.ai_controller.correct(self.ai, self.player):
                element = self.ai_controller.choose_element(self.ai, self.player)
                self._answer_success("ai", element, self.ai_question_elapsed)
                self.ai_recovery = 0.9
            else:
                self.ai.combo = 0
                self.ai.recent_element = None
                self.ai.fusion_window = 0.0
                self._event("fizzle", "ai", self.ai.x, 260, "MISCAST")
                self.ai_recovery = 0.75
            self.ai_waiting = True
        self._finish_if_needed()
