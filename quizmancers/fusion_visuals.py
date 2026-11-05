import math

import pygame

from .config import Element, HEIGHT, WIDTH
from .spells import ELEMENT_COLORS


def fusion_projectile(surface: pygame.Surface, shot, time: float) -> bool:
    if not shot.fusion:
        return False
    x, y = round(shot.x), round(shot.y)
    phase = time * 10 + shot.age * 12
    facing = shot.direction
    r = shot.radius
    if shot.fusion == "flame_tornado":
        for i in range(8):
            rise = (i - 3.5) * 13
            width = round(12 + 2.9 * (i + 1))
            sway = math.sin(phase + i * 1.2) * (15 + i * 2)
            px = round(x + sway)
            py = round(y + rise)
            color = (255, 83 + (i % 4) * 27, 42) if i % 2 else (255, 192, 76)
            pygame.draw.arc(surface, color, (px - width, py - 8, width * 2, 22),
                            phase * 0.2 + i, phase * 0.2 + i + 4.4, 5)
        pygame.draw.circle(surface, (255, 232, 111), (x, y), 11)
        for i in range(5):
            bx = x - facing * (20 + i * 12)
            by = y + math.sin(phase * 0.8 + i) * 22
            pygame.draw.circle(surface, (255, 120, 43), (round(bx), round(by)), 4 + i % 2)
    elif shot.fusion == "chain_lightning":
        points = []
        for i in range(9):
            px = x - facing * (104 - i * 13)
            py = y + math.sin(phase + i * 3.1) * (14 + i % 3 * 7)
            points.append((round(px), round(py)))
        for start, end in zip(points, points[1:]):
            pygame.draw.line(surface, (255, 154, 74), start, end, 12)
            pygame.draw.line(surface, (255, 242, 141), start, end, 6)
            pygame.draw.line(surface, (255, 255, 237), start, end, 2)
        for i in (2, 4, 6):
            px, py = points[i]
            pygame.draw.line(surface, (255, 236, 139), (px, py),
                             (px + facing * 18, py + (24 if i % 4 else -25)), 3)
        pygame.draw.circle(surface, (255, 255, 237), (x, y), 11)
    elif shot.fusion == "mudslide":
        pygame.draw.ellipse(surface, (91, 71, 70), (x - r * 2, y + 4, r * 4, 37))
        for i in range(6):
            px = x - facing * (i * 17 - 30)
            py = y - 14 + math.sin(phase + i) * 8
            pygame.draw.circle(surface, (136, 103, 73), (round(px), round(py)), 15 + (i % 3) * 5)
            pygame.draw.arc(surface, (114, 211, 239), (px - 21, py - 18, 44, 40),
                            0.25, 2.7, 4)
        pygame.draw.circle(surface, (244, 214, 146), (x + facing * 9, y - 10), 6)
    return True


def fusion_area(surface: pygame.Surface, area, time: float) -> bool:
    if area.kind not in ("flame_tornado", "chain_lightning", "mudslide"):
        return False
    x, y = round(area.x), round(area.y)
    phase = time * 7
    if area.kind == "flame_tornado":
        pygame.draw.ellipse(surface, (183, 86, 59), (x - 117, 400, 234, 49))
        for index in range(10):
            level = index / 9
            yy = y + 78 - level * 218
            radius = 80 * (1 - level * 0.65)
            wobble = math.sin(phase + index * 1.2) * (23 + 8 * level)
            pygame.draw.arc(surface, (250, 99, 47) if index % 2 else (255, 205, 95),
                            (round(x + wobble - radius), round(yy), round(2 * radius), 44),
                            phase * 0.3 + index, phase * 0.3 + index + 4.7, 7)
        for i in range(7):
            bx = x + math.sin(phase + i) * (37 + i * 8)
            by = 406 - (time * (58 + i * 7) + i * 33) % 175
            pygame.draw.circle(surface, (255, 172, 62), (round(bx), round(by)), 4 + i % 3)
    elif area.kind == "chain_lightning":
        for index in range(3):
            start = x - 70 + 70 * index
            pts = [(round(start), 150)]
            for i in range(1, 9):
                xx = start + math.sin(phase * 2 + index * 7 + i * 3) * (12 + i * 2)
                yy = 150 + i * 27
                pts.append((round(xx), round(yy)))
            pts.append((x, y + 12))
            for a, b in zip(pts, pts[1:]):
                pygame.draw.line(surface, (255, 212, 91), a, b, 7)
                pygame.draw.line(surface, (255, 253, 217), a, b, 3)
        for i in range(6):
            angle = time * 9 + i * math.tau / 6
            r = 30 + 10 * (i % 3)
            pygame.draw.circle(surface, (255, 250, 180),
                               (round(x + math.cos(angle) * r), round(y + math.sin(angle) * r)), 5)
    elif area.kind == "mudslide":
        pygame.draw.ellipse(surface, (115, 92, 72), (x - 170, 405, 340, 61))
        pygame.draw.ellipse(surface, (175, 137, 97), (x - 160, 405, 320, 44))
        for index in range(11):
            px = x - 140 + index * 28
            wave = 10 * math.sin(phase + index * 0.9)
            pygame.draw.circle(surface, (152, 111, 81), (round(px), round(416 - wave)), 17 + index % 3 * 3)
            pygame.draw.arc(surface, (122, 210, 235),
                            (round(px - 19), round(410 - wave), 38, 31), 0.1, 2.8, 4)
        for i in range(5):
            dx = x - 115 + i * 56
            pygame.draw.polygon(surface, (200, 164, 107),
                                ((dx - 8, 426), (dx - 3, 397 - i % 3 * 8), (dx + 13, 425)))
    return True


def ultimate_atmosphere(surface: pygame.Surface, duel, time: float) -> None:
    active = [area.element for area in duel.areas if area.tier == 4]
    active.extend(shot.element for shot in duel.projectiles if shot.tier == 4 and not shot.familiar)
    active.extend(wizard.casting_element for wizard in (duel.player, duel.ai)
                  if wizard.cast_remaining > 0 and wizard.level == 4)
    if not active:
        return
    element = active[0]
    wash = pygame.Surface((WIDTH, 407), pygame.SRCALPHA)
    colors = {
        Element.FIRE: (113, 32, 35, 37),
        Element.EARTH: (76, 50, 50, 38),
        Element.WATER: (22, 70, 136, 42),
        Element.AIR: (44, 104, 91, 32),
        Element.SPIRIT: (79, 50, 138, 29),
    }
    wash.fill(colors[element])
    surface.blit(wash, (0, 116))
    if element == Element.FIRE:
        for i in range(11):
            xx = 65 + i * 102 + 28 * math.sin(time * 1.8 + i)
            yy = 165 + ((time * (47 + i * 4) + i * 29) % 235)
            pygame.draw.circle(surface, (255, 188, 76), (round(xx), round(yy)), 3 + i % 3)
    elif element == Element.EARTH:
        for i in range(8):
            xx = 140 + i * 129
            drift = 15 * math.sin(time * 3 + i)
            pygame.draw.line(surface, (167, 109, 82), (xx, 485), (xx + drift, 465 - i % 3 * 10), 4)
    elif element == Element.WATER:
        for i in range(23):
            xx = (i * 79 + time * 70) % WIDTH
            yy = 137 + (i * 47 + time * 185) % 338
            pygame.draw.line(surface, (159, 224, 250), (xx, yy), (xx - 7, yy + 15), 2)
    elif element == Element.AIR:
        for i in range(9):
            yy = 179 + i * 37
            dx = 34 * math.sin(time * 2 + i)
            pygame.draw.arc(surface, (169, 234, 213), (round(120 + dx), yy, 920, 54),
                            math.pi * 0.3, math.pi * 0.85, 2)
    elif element == Element.SPIRIT:
        for i in range(10):
            angle = time * 1.6 + i * math.tau / 10
            xx = 590 + math.cos(angle) * 222
            yy = 319 + math.sin(angle) * 80
            pygame.draw.circle(surface, (218, 185, 252), (round(xx), round(yy)), 5, 2)


def wizard_impact(surface: pygame.Surface, x: float, y: float, wizard, time: float) -> None:
    strength = max(0.0, min(1.0, wizard.hit_remaining / 0.62))
    if strength <= 0:
        return
    cx = round(x)
    cy = round(y - 20)
    element = wizard.impact_element
    color = ELEMENT_COLORS[element]
    extent = int(60 + 58 * (1 - strength) + wizard.impact_tier * 5)
    pygame.draw.circle(surface, color, (cx, cy), extent, max(1, round(5 * strength)))
    for i in range(9):
        angle = (i * math.tau / 9 + time * 2.8)
        r = extent * (0.58 + i % 3 * 0.1)
        px = round(cx + math.cos(angle) * r)
        py = round(cy + math.sin(angle) * r * 0.75)
        pygame.draw.line(surface, color, (px, py),
                         (round(px + math.cos(angle) * (10 + strength * 19)),
                          round(py + math.sin(angle) * (10 + strength * 19))),
                         max(1, round(3 * strength)))
