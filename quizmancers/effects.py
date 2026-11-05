from dataclasses import dataclass
import math
import random

import pygame

from .combat import DuelEvent, Projectile
from .config import Element
from .spells import ELEMENT_COLORS
from .fusions import FUSION_KINDS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    lifetime: float
    total: float
    color: tuple[int, int, int]
    shape: str = "spark"


@dataclass
class Ripple:
    x: float
    y: float
    color: tuple[int, int, int]
    lifetime: float
    total: float
    start: float
    end: float


@dataclass
class FloatingLabel:
    text: str
    x: float
    y: float
    lifetime: float
    total: float
    color: tuple[int, int, int]


class Effects:
    def __init__(self, audio):
        self.rng = random.Random()
        self.particles: list[Particle] = []
        self.ripples: list[Ripple] = []
        self.labels: list[FloatingLabel] = []
        self.audio = audio
        self.flash = 0.0
        self.shake = 0.0
        self.feedback = "ANSWER TO CAST A SPELL"
        self.feedback_color = (204, 188, 232)
        self.feedback_lifetime = 0.0
        self.level_banner = ""
        self.level_banner_lifetime = 0.0
        self.fusion_banner = ""
        self.fusion_banner_lifetime = 0.0
        self.ultimate_banner = ""
        self.ultimate_banner_lifetime = 0.0

    def emit(self, x: float, y: float, element: Element, count: int = 20, tier: int = 1) -> None:
        color = ELEMENT_COLORS[element]
        shape = {Element.FIRE: "ember", Element.EARTH: "stone", Element.WATER: "drop", Element.AIR: "wind", Element.SPIRIT: "star"}[element]
        for _ in range(count + tier * 3):
            angle = self.rng.random() * math.tau
            speed = self.rng.uniform(45, 160 + 38 * tier)
            life = self.rng.uniform(0.25, 0.58 + 0.1 * tier)
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed - 15,
                                           self.rng.uniform(2, 5 + tier), life, life, color, shape))

    def ring(self, x: float, y: float, element: Element, tier: int, large: bool = False) -> None:
        end = 65 + tier * 18 if large else 35 + tier * 14
        self.ripples.append(Ripple(x, y, ELEMENT_COLORS[element], 0.43 + 0.08 * tier,
                                   0.43 + 0.08 * tier, 5, end))

    def on_events(self, events: list[DuelEvent]) -> None:
        for event in events:
            if event.kind == "familiar":
                self.emit(event.x, event.y, event.element, 2, 1)
            elif event.kind == "pulse":
                self.ring(event.x, event.y, Element.SPIRIT, 3, True)
                self.emit(event.x, event.y, Element.SPIRIT, 16, 2)
                self.audio.play("ward")
            elif event.kind == "parry":
                self.emit(event.x, event.y, Element.SPIRIT, 24, 3)
                self.ring(event.x, event.y, Element.SPIRIT, 4, True)
                self.labels.append(FloatingLabel("REFLECT!", event.x, event.y - 104, 1, 1, (248, 233, 255)))
                self.shake = max(self.shake, 5.0)
                self.audio.play("parry")
            elif event.kind == "fusion_cast":
                self.emit(event.x, event.y, event.element, 41, event.tier)
                self.ring(event.x, event.y, event.element, 4, True)
                if event.side == "player":
                    self.fusion_banner = event.message
                    self.fusion_banner_lifetime = 1.7
                else:
                    self.labels.append(FloatingLabel(event.message, event.x, event.y - 133,
                                                     1.3, 1.3, (255, 221, 138)))
                self.shake = max(self.shake, 4.8)
                self.audio.play("ultimate")
            elif event.kind == "fusion_hit":
                self.emit(event.x, event.y, event.element, 39, event.tier)
                self.ring(event.x, event.y, event.element, 4, True)
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 130,
                                                 1.15, 1.15, (255, 236, 168)))
                self.shake = max(self.shake, 8.0)
                self.flash = max(self.flash, 0.12)
                self.audio.play("hit")
            elif event.kind == "fusion_zone":
                self.emit(event.x, event.y, event.element, 26, event.tier)
                self.ring(event.x, event.y, event.element, 4, True)
                self.shake = max(self.shake, 6.0)
            elif event.kind == "ultimate_cast":
                self.emit(event.x, event.y, event.element, 34, 4)
                self.ring(event.x, event.y, event.element, 4, True)
                if event.side == "player":
                    self.ultimate_banner = event.message
                    self.ultimate_banner_lifetime = 1.2
                self.shake = max(self.shake, 4.5)
            elif event.kind == "area_spawn":
                self.emit(event.x, event.y, event.element, 32, event.tier)
                self.ring(event.x, event.y, event.element, 4, True)
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 132, 1.25, 1.25, (252, 228, 180)))
                self.shake = max(self.shake, 4.0 + event.tier)
                self.audio.play("hit")
            elif event.kind == "area_tick":
                self.emit(event.x, event.y, event.element, 4, event.tier)
                if event.amount:
                    self.labels.append(FloatingLabel(event.message, event.x, event.y - 85, 0.68, 0.68, (255, 239, 193)))
                self.shake = max(self.shake, 1.8)
            elif event.kind == "bloom":
                self.emit(event.x, event.y, Element.SPIRIT, 5, 2)
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 102, 0.72, 0.72, (187, 255, 207)))
            elif event.kind == "cast":
                self.emit(event.x, event.y, event.element, 6, event.tier)
                self.ring(event.x, event.y, event.element, event.tier)
                self.audio.play("ultimate" if event.tier >= 4 else "cast")
            elif event.kind == "ward":
                self.emit(event.x, event.y, Element.SPIRIT, 23, event.tier)
                self.ring(event.x, event.y, Element.SPIRIT, event.tier, True)
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 96, 1.45, 1.45, (220, 189, 255)))
                self.audio.play("ward")
            elif event.kind == "hit":
                self.emit(event.x, event.y, event.element, 26, event.tier)
                self.ring(event.x, event.y, event.element, event.tier, True)
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 101, 1.0, 1.0, (255, 246, 229)))
                self.shake = max(self.shake, 3.5 + 1.2 * event.tier)
                self.flash = max(self.flash, 0.07 + 0.017 * event.tier)
                self.audio.play("hit")
            elif event.kind == "block":
                self.emit(event.x, event.y, Element.SPIRIT, 8, event.tier)
            elif event.kind == "burn":
                self.emit(event.x, event.y + 5, Element.FIRE, 2)
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 93, 0.7, 0.7, (255, 132, 82)))
            elif event.kind == "clash":
                self.emit(event.x, event.y, event.element, 18, event.tier)
                self.ring(event.x, event.y, event.element, event.tier, True)
                self.labels.append(FloatingLabel("CLASH!", event.x, event.y - 62, 0.8, 0.8, (255, 236, 180)))
                self.shake = max(self.shake, 3.0)
                self.audio.play("clash")
            elif event.kind == "combo":
                self.labels.append(FloatingLabel(event.message, event.x, event.y - 85, 1.05, 1.05, (255, 234, 95)))
            elif event.kind == "level_up":
                self.emit(event.x, event.y, Element.SPIRIT, 48, 4)
                self.ring(event.x, event.y, Element.SPIRIT, 4, True)
                if event.side == "player":
                    self.level_banner = event.message
                    self.level_banner_lifetime = 2.1
                else:
                    self.labels.append(FloatingLabel(f"RIVAL LEVEL {event.tier}!", event.x, event.y - 89, 1.6, 1.6, (255, 227, 172)))
                self.audio.play("level_up")
            elif event.kind == "retry":
                self.feedback = "SPELL UNSTABLE! TRY AGAIN!"
                self.feedback_color = (255, 207, 138)
                self.feedback_lifetime = 1.7
                self.emit(event.x, event.y, Element.SPIRIT, 12, 1)
                self.audio.play("wrong")
            elif event.kind in ("answer_correct", "answer_wrong", "timeout"):
                self.feedback = event.message
                self.feedback_color = (160, 255, 195) if event.kind == "answer_correct" else (255, 153, 163)
                self.feedback_lifetime = 1.4
                self.audio.play("correct" if event.kind == "answer_correct" else "wrong")
            elif event.kind == "fizzle":
                self.labels.append(FloatingLabel("MISCAST", event.x, event.y - 80, 1.0, 1.0, (225, 191, 233)))
            elif event.kind == "finish":
                self.emit(event.x, event.y, Element.SPIRIT, 65, 4)
                self.shake = 9.0
                self.audio.play("finish")
        self.particles = self.particles[-550:]
        self.ripples = self.ripples[-50:]
        self.labels = self.labels[-30:]

    def trail(self, projectiles: list[Projectile], dt: float) -> None:
        for projectile in projectiles:
            color = FUSION_KINDS[projectile.fusion].color if projectile.fusion else ELEMENT_COLORS[projectile.element]
            count = 1 if projectile.familiar else 2 if projectile.tier < 3 else 3
            for _ in range(count):
                life = self.rng.uniform(0.18, 0.39)
                drift = self.rng.uniform(-40, 40)
                self.particles.append(Particle(
                    projectile.x - projectile.direction * self.rng.uniform(6, projectile.radius + 18),
                    projectile.y + self.rng.uniform(-projectile.radius, projectile.radius),
                    -projectile.direction * self.rng.uniform(35, 80), drift,
                    self.rng.uniform(2, 3 + projectile.tier), life, life, color,
                    "ember" if projectile.element == Element.FIRE else "drop" if projectile.element == Element.WATER else "spark",
                ))
        self.particles = self.particles[-550:]

    def update(self, dt: float) -> None:
        self.flash = max(0.0, self.flash - dt)
        self.shake = max(0.0, self.shake - dt * 18)
        self.feedback_lifetime = max(0.0, self.feedback_lifetime - dt)
        self.level_banner_lifetime = max(0.0, self.level_banner_lifetime - dt)
        self.fusion_banner_lifetime = max(0.0, self.fusion_banner_lifetime - dt)
        self.ultimate_banner_lifetime = max(0.0, self.ultimate_banner_lifetime - dt)
        living = []
        for particle in self.particles:
            particle.lifetime -= dt
            if particle.lifetime <= 0:
                continue
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vx *= max(0.0, 1 - dt * 1.8)
            particle.vy += dt * (115 if particle.shape in ("stone", "drop") else -12 if particle.shape == "ember" else 20)
            living.append(particle)
        self.particles = living
        for ripple in self.ripples:
            ripple.lifetime -= dt
        self.ripples = [ripple for ripple in self.ripples if ripple.lifetime > 0]
        for label in self.labels:
            label.y -= 26.0 * dt
            label.lifetime -= dt
        self.labels = [label for label in self.labels if label.lifetime > 0]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        for ripple in self.ripples:
            progress = 1.0 - ripple.lifetime / ripple.total
            radius = max(1, round(ripple.start + (ripple.end - ripple.start) * progress))
            alpha = max(30, int(220 * (1 - progress)))
            color = tuple(round(component * alpha / 255 + 70 * (1 - alpha / 255)) for component in ripple.color)
            pygame.draw.circle(surface, color, (round(ripple.x), round(ripple.y)), radius, max(1, round(5 * (1 - progress))))
        for particle in self.particles:
            opacity = max(0.0, particle.lifetime / particle.total)
            color = tuple(max(0, min(255, int(component * opacity + 65 * (1 - opacity)))) for component in particle.color)
            x, y = round(particle.x), round(particle.y)
            radius = max(1, round(particle.radius * opacity))
            if particle.shape == "star" and radius >= 3:
                pygame.draw.line(surface, color, (x - radius * 2, y), (x + radius * 2, y), 2)
                pygame.draw.line(surface, color, (x, y - radius * 2), (x, y + radius * 2), 2)
            elif particle.shape == "stone":
                pygame.draw.polygon(surface, color, [(x - radius, y), (x, y - radius), (x + radius, y), (x, y + radius)])
            elif particle.shape == "wind":
                pygame.draw.line(surface, color, (x - radius * 3, y - radius), (x + radius * 2, y + radius), 2)
            elif particle.shape == "drop":
                pygame.draw.ellipse(surface, color, (x - radius, y - radius * 2, radius * 2, radius * 3))
            else:
                pygame.draw.circle(surface, color, (x, y), radius)
        for label in self.labels:
            rendered = font.render(label.text, True, label.color)
            shadow = font.render(label.text, True, (51, 31, 69))
            x = round(label.x - rendered.get_width() / 2)
            y = round(label.y)
            surface.blit(shadow, (x + 2, y + 3))
            surface.blit(rendered, (x, y))
