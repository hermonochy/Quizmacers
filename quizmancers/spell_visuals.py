import math

import pygame

from .config import Element, PROJECTILE_Y, WIDTH
from .spells import ELEMENT_COLORS, spell_for


def ambient(surface: pygame.Surface, time: float) -> None:
    for i in range(28):
        phase = time * (0.21 + (i % 5) * 0.06) + i * 2.391
        x = 72 + ((i * 191 + phase * 36) % (WIDTH - 144))
        y = 278 + (i * 47 % 215) + math.sin(phase * 2.0) * 13
        radius = 1 + i % 3
        pygame.draw.circle(surface, (250, 211, 142) if i % 3 else (223, 179, 243),
                           (round(x), round(y)), radius)
    for i in range(8):
        phase = time * (0.8 + 0.08 * i) + i * math.tau / 8
        x = round(590 + 183 * math.cos(phase))
        y = round(374 + 38 * math.sin(phase))
        pygame.draw.circle(surface, (255, 236, 184), (x, y), 2 if i % 2 else 3)


def conjuring(surface: pygame.Surface, x: float, y: float, amount: float,
              element: Element, time: float, facing: int = 1) -> None:
    amount = max(0.05, min(1.0, amount))
    color = ELEMENT_COLORS[element]
    px, py = round(x + 67 * facing), round(y - 57)
    diameter = 20 + round(amount * 49)
    pygame.draw.circle(surface, color, (px, py), diameter, 2)
    pygame.draw.circle(surface, (255, 246, 216), (px, py), 8 + round(amount * 7), 2)
    for i in range(9):
        angle = time * (1.7 + amount * 2.4) + i * math.tau / 9
        radius = diameter + 5 + math.sin(time * 4 + i) * 3
        pos = (round(px + math.cos(angle) * radius), round(py + math.sin(angle) * radius))
        pygame.draw.circle(surface, color, pos, 2 + round(amount * 2))
    for i in range(int(2 + 8 * amount)):
        angle = -time * 3.3 + i * 2.4
        distance = 17 + (time * 43 + i * 17) % (25 + amount * 24)
        pygame.draw.circle(surface, (255, 242, 199),
                           (round(px + math.cos(angle) * distance), round(py + math.sin(angle) * distance)), 2)


def pulse(surface: pygame.Surface, x: float, y: float, remaining: float, time: float) -> None:
    t = max(0, min(1, remaining / 0.62))
    radius = round(86 + (1 - t) * 60)
    pygame.draw.circle(surface, (239, 218, 255), (round(x), round(y - 26)), radius, 5)
    pygame.draw.circle(surface, (172, 133, 253), (round(x), round(y - 26)), radius + 10, 2)
    for i in range(6):
        angle = time * 9 + i * math.tau / 6
        px = x + math.cos(angle) * radius
        py = y - 26 + math.sin(angle) * radius
        pygame.draw.circle(surface, (255, 252, 216), (round(px), round(py)), 6)


def arena_area(surface: pygame.Surface, area, time: float) -> None:
    x, y = round(area.x), round(area.y)
    t = area.age
    tier = area.tier
    if area.kind == "inferno":
        pygame.draw.ellipse(surface, (200, 84, 45), (x - 123, 404, 246, 40))
        pygame.draw.ellipse(surface, (255, 161, 48), (x - 104, 407, 208, 27))
        for i in range(15):
            dx = (i - 7) * 16 + math.sin(time * 5 + i) * 5
            height = 37 + (i % 4) * 13 + math.sin(time * 11 + i * 2) * 10
            base = 411
            pygame.draw.polygon(surface, (243, 77, 48) if i % 2 else (255, 154, 50),
                                [(x + dx - 12, base), (x + dx, base - height), (x + dx + 12, base)])
            pygame.draw.circle(surface, (255, 230, 114), (round(x + dx), round(base - height * 0.55)), 4)
        for i in range(6):
            fy = 250 + ((i * 29 + time * 115) % 180)
            fx = x + math.sin(time * 3 + i * 2.2) * (45 + i * 12)
            pygame.draw.circle(surface, (255, 171, 53), (round(fx), round(fy)), 4 + i % 3)
    elif area.kind in ("quake", "cataclysm"):
        width = 115 if area.kind == "quake" else 167
        for i in range(7):
            startx = x - width + i * width / 3.5
            displacement = math.sin(time * 22 + i) * (7 if area.kind == "quake" else 13)
            pygame.draw.line(surface, (114, 78, 73), (round(startx), 431),
                             (round(startx + 20 + displacement), 445), 4 if tier == 3 else 6)
            pygame.draw.line(surface, (114, 78, 73), (round(startx + 20 + displacement), 445),
                             (round(startx + 8), 464), 4 if tier == 3 else 6)
            pygame.draw.line(surface, (255, 201, 108), (round(startx), 432),
                             (round(startx + 20 + displacement), 445), 2)
        if area.kind == "cataclysm":
            for i in range(7):
                rock_phase = (time * (140 + 24 * (i % 3)) + i * 57) % 220
                px = x - 126 + i * 41
                py = round(185 + rock_phase)
                r = 8 + (i * 3) % 14
                pygame.draw.polygon(surface, (126, 86, 72), [(px - r, py), (px - r // 2, py - r),
                                                               (px + r, py - r // 2), (px + r, py + r),
                                                               (px - r // 2, py + r)])
                pygame.draw.line(surface, (250, 213, 137), (px - r // 2, py - r), (px + r // 2, py - r), 3)
    elif area.kind in ("surge", "maelstrom"):
        width = 116 if area.kind == "surge" else 157
        for i in range(4):
            drift = math.sin(time * 6 + i) * 13
            ry = y - 11 + i * 19
            rect = (round(x - width + drift), round(ry - 31), width * 2, 66)
            pygame.draw.arc(surface, (57, 149, 228) if i % 2 else (110, 220, 250),
                            rect, 0.15, math.pi * 1.9, 9 if area.kind == "maelstrom" else 5)
        for i in range(12):
            angle = time * (2.7 + (i % 3) * 0.4) + i * math.tau / 12
            r = 35 + (i % 5) * 24
            pygame.draw.circle(surface, (190, 249, 255),
                               (round(x + math.cos(angle) * r), round(y + math.sin(angle) * r * 0.3)), 3 + i % 2)
        if area.kind == "maelstrom":
            for i in range(5):
                r = 35 + i * 17
                pygame.draw.arc(surface, (69, 193, 246), (x - r, y - r, 2 * r, 2 * r),
                                time * 2 + i, time * 2 + i + math.pi * 1.5, 4)
    elif area.kind == "cyclone":
        for i in range(7):
            h = i * 24
            r = 23 + i * 13
            dx = math.sin(time * 4 + i * 0.7) * 10
            pygame.draw.arc(surface, (113, 218, 187) if i % 2 else (235, 253, 205),
                            (round(x - r + dx), y - 110 + h, 2 * r, 28),
                            time * 3 + i, time * 3 + i + math.pi * 1.4, 5)


def elite_projectile(surface: pygame.Surface, shot, time: float) -> bool:
    if shot.familiar:
        x, y = round(shot.x), round(shot.y)
        color = ELEMENT_COLORS[shot.element]
        pygame.draw.circle(surface, color, (x, y), 9)
        pygame.draw.circle(surface, (255, 250, 216), (x, y), 4)
        pygame.draw.circle(surface, color, (x - shot.direction * 13, y), 3)
        return True
    if shot.tier < 3:
        return False
    x = round(shot.x)
    y = round(shot.y + math.sin(time * 8 + shot.age * 3) * 6)
    r = shot.radius
    direction = shot.direction
    element = shot.element
    color = spell_for(element, shot.tier).color
    if element == Element.FIRE and shot.tier == 3:
        points = [(x - direction * 100, y - 20)]
        for i in range(8):
            dx = x - direction * (90 - i * 12)
            dy = y + round(math.sin(time * 25 + i * 3.7 + shot.phase) * 27)
            points.append((dx, dy))
        for p1, p2 in zip(points, points[1:]):
            pygame.draw.line(surface, (255, 151, 67), p1, p2, 11)
            pygame.draw.line(surface, (255, 251, 163), p1, p2, 5)
        for i in range(5):
            px = x - direction * (i * 19)
            py = y + int(math.sin(time * 25 + i * 3.5) * 20)
            pygame.draw.line(surface, (255, 232, 158), (px, py), (px + direction * 13, py - 34), 3)
        pygame.draw.circle(surface, (255, 255, 221), (x, y), 15)
    elif element == Element.FIRE:
        for i in range(8):
            angle = time * 6 + math.tau * i / 8
            orbit = 32 + 7 * math.sin(time * 8 + i)
            fx = round(x + math.cos(angle) * orbit)
            fy = round(y + math.sin(angle) * orbit)
            pygame.draw.polygon(surface, (255, 98 + i * 12, 42),
                                [(fx - 12, fy + 13), (fx, fy - 24), (fx + 12, fy + 13)])
        pygame.draw.circle(surface, (215, 58, 50), (x, y), r + 13)
        pygame.draw.circle(surface, (255, 157, 55), (x, y), r + 4)
        pygame.draw.circle(surface, (255, 251, 158), (x + 5 * direction, y - 3), max(9, r - 8))
        for i in range(5):
            bx = x - direction * (32 + i * 22)
            pygame.draw.circle(surface, (255, 126, 49), (bx, y + int(math.sin(time * 15 + i) * 22)), max(4, 19 - i * 3))
    elif element == Element.EARTH:
        if shot.tier == 3:
            pygame.draw.ellipse(surface, (125, 80, 69), (x - 79, y + 31, 158, 39))
            for i in range(7):
                dx = (i - 3) * 23
                height = 13 + (i % 3) * 14
                pygame.draw.polygon(surface, (174, 131, 89),
                                    [(x + dx - 11, y + 41), (x + dx, y + 34 - height),
                                     (x + dx + 11, y + 42)])
            pygame.draw.arc(surface, (255, 218, 127), (x - 82, y + 30, 164, 44), math.pi, math.tau, 4)
        else:
            pygame.draw.polygon(surface, (108, 75, 69),
                                [(x - 39, y + 30), (x - 32, y - 37), (x + 1, y - 66),
                                 (x + 43, y - 30), (x + 46, y + 26), (x, y + 53)])
            pygame.draw.polygon(surface, color, [(x - 28, y + 21), (x - 20, y - 33),
                                                 (x + 1, y - 52), (x + 33, y - 21),
                                                 (x + 27, y + 26)])
            for i in range(3):
                pygame.draw.line(surface, (255, 215, 130), (x - 16 + i * 17, y - 25),
                                 (x - 2 + i * 10, y + 8), 4)
    elif element == Element.WATER:
        width = 68 if shot.tier == 3 else 100
        for i in range(5):
            dx = x - direction * (i * 19)
            height = 24 + i * 10 + (12 if shot.tier == 4 else 0)
            pygame.draw.arc(surface, (44, 139, 235),
                            (dx - width, y - height, width * 2, height * 2),
                            math.pi * 0.05, math.pi * 1.14, 12)
            pygame.draw.arc(surface, (191, 248, 250),
                            (dx - width, y - height, width * 2, height * 2),
                            math.pi * 0.2, math.pi * 0.95, 5)
        for i in range(6):
            dx = x - i * 16 * direction
            pygame.draw.circle(surface, color, (dx, y + int(math.sin(time * 12 + i) * 22)), 6)
    elif element == Element.AIR:
        for i in range(7 if shot.tier == 3 else 11):
            height = 25 + i * (9 if shot.tier == 3 else 11)
            width = 23 + i * 7
            cy = y - 63 + i * 13
            dx = math.sin(time * 11 + i * 0.8) * 12
            pygame.draw.arc(surface, (183, 255, 219) if i % 2 else (79, 188, 165),
                            (round(x - width + dx), cy, width * 2, height),
                            time * 3 + i, time * 3 + i + math.pi * 1.4, 4)
        pygame.draw.circle(surface, (242, 255, 221), (x, y), 8)
    return True
