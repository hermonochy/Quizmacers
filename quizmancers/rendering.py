import math
import random

import pygame

from .combat import Duel, Projectile, Wizard
from .config import (
    AI_X,
    GOLD,
    HEIGHT,
    INK,
    LIGHT_TEXT,
    MAX_HEALTH,
    MUTED_TEXT,
    PANEL,
    PANEL_ALT,
    PLAYER_X,
    Element,
    ELEMENT_KEYS,
    WIDTH,
    WIZARD_Y,
)
from .effects import Effects
from .spells import ELEMENT_COLORS, ELEMENT_ORDER, spell_for
from .spell_visuals import ambient, arena_area, conjuring, elite_projectile, pulse
from .fusion_visuals import fusion_area, fusion_projectile, ultimate_atmosphere, wizard_impact
from .progression import POINTS_PER_RANK, Progress, RankChange, appearance_for_rank, tier_for_rank
from .revision import RevisionSummary
from .curriculum import StudySelection


class Renderer:
    def __init__(self):
        self.fonts = {
            "logo": pygame.font.SysFont("georgia", 29, bold=True),
            "name": pygame.font.SysFont("arial", 18, bold=True),
            "title": pygame.font.SysFont("arial", 16, bold=True),
            "question": pygame.font.SysFont("arial", 46, bold=True),
            "input": pygame.font.SysFont("arial", 26, bold=True),
            "body": pygame.font.SysFont("arial", 18, bold=True),
            "small": pygame.font.SysFont("arial", 14, bold=True),
            "tiny": pygame.font.SysFont("arial", 12, bold=True),
            "popup": pygame.font.SysFont("arial", 23, bold=True),
            "card": pygame.font.SysFont("arial", 13, bold=True),
            "card_small": pygame.font.SysFont("arial", 11, bold=True),
            "winner": pygame.font.SysFont("georgia", 53, bold=True),
        }
        self.background = self._make_background()
        self.spell_rects = {element: pygame.Rect(499 + index * 131, 577, 123, 100)
                            for index, element in enumerate(ELEMENT_ORDER)}
        self.cast_rect = pygame.Rect(300, 629, 174, 46)
        self.choice_rects = [pygame.Rect(48 + (index % 2) * 218, 615 + (index // 2) * 36, 207, 32)
                             for index in range(4)]
        self.menu_selector_rects = {
            field: (pygame.Rect(329, y, 44, 37), pygame.Rect(381, y, 420, 37), pygame.Rect(809, y, 44, 37))
            for field, y in (("course", 281), ("board", 343), ("subject", 405), ("subtopic", 467))
        }
        self.menu_topic_prev_rect, self.menu_topic_rect, self.menu_topic_next_rect = self.menu_selector_rects["subtopic"]
        self.menu_play_rect = pygame.Rect(400, 551, 380, 48)
        self.menu_difficulty_rect = pygame.Rect(400, 611, 181, 40)
        self.menu_pace_rect = pygame.Rect(599, 611, 181, 40)
        self.rematch_rect = pygame.Rect(392, 458, 190, 43)
        self.back_menu_rect = pygame.Rect(604, 458, 190, 43)

    def _text(self, surface, content, x, y, font="body", color=LIGHT_TEXT, center=False, shadow=False):
        rendered = self.fonts[font].render(str(content), True, color)
        if center:
            x -= rendered.get_width() // 2
        if shadow:
            dark = self.fonts[font].render(str(content), True, (51, 32, 65))
            surface.blit(dark, (round(x) + 2, round(y) + 2))
        surface.blit(rendered, (round(x), round(y)))
        return rendered

    def _gradient(self, surface, top, bottom, start_y, stop_y):
        span = max(1, stop_y - start_y)
        for y in range(start_y, stop_y):
            part = (y - start_y) / span
            color = tuple(round(top[n] + (bottom[n] - top[n]) * part) for n in range(3))
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))

    def _pillar(self, canvas, x, bottom):
        pygame.draw.rect(canvas, (167, 113, 70), (x - 34, 65, 68, bottom - 65), border_radius=12)
        pygame.draw.rect(canvas, (230, 185, 119), (x - 28, 70, 56, bottom - 78), border_radius=9)
        pygame.draw.rect(canvas, (255, 222, 154), (x - 22, 78, 15, bottom - 95), border_radius=5)
        pygame.draw.rect(canvas, (138, 94, 67), (x - 43, bottom - 30, 86, 30), border_radius=8)
        pygame.draw.rect(canvas, (241, 191, 114), (x - 39, bottom - 29, 78, 18), border_radius=7)
        pygame.draw.rect(canvas, (138, 94, 67), (x - 42, 57, 84, 21), border_radius=7)
        pygame.draw.rect(canvas, (253, 204, 126), (x - 37, 55, 74, 17), border_radius=6)

    def _banner(self, canvas, x, color):
        pygame.draw.rect(canvas, (124, 86, 67), (x - 17, 106, 34, 8), border_radius=4)
        pygame.draw.polygon(canvas, color, [(x - 15, 112), (x + 15, 112), (x + 15, 176), (x, 165), (x - 15, 176)])
        pygame.draw.polygon(canvas, (255, 223, 136), [(x - 2, 123), (x + 2, 123), (x + 7, 142), (x, 151), (x - 7, 142)])
        pygame.draw.line(canvas, (250, 210, 120), (x - 14, 115), (x - 14, 164), 3)

    def _make_background(self) -> pygame.Surface:
        canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        self._gradient(canvas, (255, 238, 201), (215, 175, 133), 0, HEIGHT)
        pygame.draw.rect(canvas, (171, 116, 75), (0, 98, WIDTH, 17))
        pygame.draw.rect(canvas, (248, 220, 166), (0, 116, WIDTH, 135))
        pygame.draw.rect(canvas, (181, 134, 91), (0, 243, WIDTH, 18))
        pygame.draw.rect(canvas, (255, 243, 204), (0, 118, WIDTH, 9))
        for x in range(0, WIDTH, 100):
            pygame.draw.line(canvas, (229, 190, 136), (x, 119), (x + 30, 243), 1)
        pygame.draw.rect(canvas, (176, 120, 78), (482, 102, 216, 152), border_radius=33)
        pygame.draw.rect(canvas, (232, 179, 108), (493, 105, 194, 148), border_radius=29)
        pygame.draw.rect(canvas, (111, 70, 55), (511, 118, 158, 139), border_radius=19)
        pygame.draw.rect(canvas, (81, 52, 49), (523, 125, 134, 130), border_radius=12)
        for x in range(538, 650, 24):
            pygame.draw.rect(canvas, (158, 102, 67), (x, 130, 13, 123), border_radius=2)
        for y in range(134, 247, 25):
            pygame.draw.line(canvas, (57, 39, 39), (526, y), (656, y), 5)
        pygame.draw.circle(canvas, (238, 177, 79), (590, 172), 8)
        pygame.draw.circle(canvas, (255, 216, 111), (590, 172), 4)
        for x in (47, 274, 906, 1133):
            self._pillar(canvas, x, 266)
        for x, color in ((150, (172, 66, 43)), (215, (167, 102, 49)), (965, (172, 66, 43)), (1030, (167, 102, 49))):
            self._banner(canvas, x, color)
        for x in (326, 854):
            pygame.draw.line(canvas, (138, 103, 65), (x, 143), (x, 195), 7)
            pygame.draw.ellipse(canvas, (125, 85, 49), (x - 12, 183, 24, 11))
            pygame.draw.polygon(canvas, (246, 147, 54), [(x, 152), (x - 10, 175), (x - 4, 188), (x + 8, 184), (x + 12, 170)])
            pygame.draw.polygon(canvas, (255, 222, 94), [(x + 1, 165), (x - 5, 178), (x + 4, 185), (x + 7, 175)])
        pygame.draw.ellipse(canvas, (171, 118, 76), (19, 244, 1142, 305))
        pygame.draw.ellipse(canvas, (231, 181, 105), (24, 236, 1132, 300))
        pygame.draw.ellipse(canvas, (255, 233, 168), (36, 245, 1108, 282))
        pygame.draw.ellipse(canvas, (239, 207, 156), (50, 258, 1080, 251))
        pygame.draw.ellipse(canvas, (250, 227, 183), (62, 261, 1056, 234))
        pygame.draw.arc(canvas, (185, 138, 101), (80, 282, 1020, 194), 0, math.pi, 3)
        pygame.draw.arc(canvas, (254, 239, 196), (77, 278, 1026, 198), math.pi, math.tau, 5)
        rng = random.Random(82)
        for _ in range(68):
            x = rng.randint(82, 1098)
            y = rng.randint(303, 489)
            dx = (x - 590) / 529
            dy = (y - 375) / 118
            if dx * dx + dy * dy > 0.97:
                continue
            color = rng.choice(((209, 169, 124), (232, 165, 149), (230, 191, 136), (197, 154, 137)))
            pygame.draw.ellipse(canvas, color, (x, y, rng.randint(3, 13), rng.randint(2, 6)))
        for x, y in ((189, 438), (322, 474), (736, 452), (1028, 452), (460, 315), (843, 321)):
            pygame.draw.ellipse(canvas, (255, 238, 160), (x - 28, y - 7, 56, 15), 3)
        pygame.draw.ellipse(canvas, (178, 122, 80), (24, 502, 1132, 51), 8)
        pygame.draw.ellipse(canvas, (251, 221, 151), (34, 502, 1110, 43), 3)
        return canvas

    def _wizard(self, surface: pygame.Surface, x: int, y: int, facing: int, time: float, is_player: bool, wizard: Wizard, rank: int = 0):
        hit = max(0.0, min(1.0, wizard.hit_remaining / 0.5))
        casting = max(0.0, min(1.0, wizard.cast_remaining / 0.5))
        knockback = (1 if not is_player else -1) * round(hit * 17)
        x += knockback + round(math.sin(time * 52) * 4 * hit)
        y += round(math.sin(time * 2.8 + (0 if is_player else 1.5)) * 3 + hit * 7 - casting * 4)
        lean = hit * (0.18 if is_player else -0.18)
        p = lambda xx, yy: (round(x + (xx + lean * (yy + 20)) * facing), round(y + yy))
        hat = (91, 50, 139) if is_player else (38, 109, 140)
        cape = (98, 57, 155) if is_player else (46, 118, 160)
        deep = (60, 33, 102) if is_player else (28, 72, 111)
        cream = (255, 218, 165) if is_player else (255, 215, 176)
        trim = (255, 197, 95)
        if rank >= 3:
            cape = (112, 53, 175) if is_player else (37, 121, 165)
            hat = (76, 44, 142) if is_player else (22, 100, 147)
        if rank >= 6:
            cape = (123, 65, 188) if is_player else (46, 130, 183)
            trim = (255, 226, 132)
        if rank >= 8:
            hat = (71, 38, 128) if is_player else (24, 95, 136)
            trim = (255, 238, 161)
        pygame.draw.ellipse(surface, (170, 121, 103), (x - 52, y + 57, 105, 21))
        pygame.draw.ellipse(surface, (255, 239, 167), (x - 47, y + 58, 94, 18), 3)
        if rank > 0:
            pygame.draw.ellipse(surface, (224, 180, 255) if rank < 5 else (255, 221, 121),
                                (x - 53 - rank, y + 54 - rank // 2, 106 + rank * 2, 25 + rank), 2)
            for index in range(min(rank + 1, 8)):
                angle = time * (0.8 + rank * 0.06) + index * math.tau / min(rank + 1, 8)
                px = x + round(math.cos(angle) * (59 + rank * 1.7))
                py = y - 34 + round(math.sin(angle) * (58 + rank * 1.1))
                pygame.draw.circle(surface, (243, 206, 255) if rank < 5 else (255, 230, 146),
                                   (px, py), 2 + rank // 4)
        if wizard.shield > 0:
            aura = pygame.Surface((172, 205), pygame.SRCALPHA)
            wobble = round(math.sin(time * 5) * 3)
            pygame.draw.ellipse(aura, (174, 126, 255, 30), (9 + wobble, 9, 152, 182))
            pygame.draw.ellipse(aura, (215, 174, 255, 150), (9 + wobble, 9, 152, 182), 4)
            pygame.draw.ellipse(aura, (255, 229, 255, 110), (18 + wobble, 17, 134, 166), 1)
            surface.blit(aura, (x - 86, y - 122))
        if wizard.soaked_remaining > 0:
            for index in range(4):
                px = x + round(math.sin(time * 3 + index * 2) * (36 + index * 3))
                py = y - 45 + round((time * 29 + index * 18) % 70)
                pygame.draw.circle(surface, (79, 197, 246), (px, py), 3)
        if wizard.burn_remaining > 0:
            for index in range(3):
                dx = (index - 1) * 29
                py = y + 26 - round(abs(math.sin(time * 7 + index)) * 16)
                pygame.draw.polygon(surface, (255, 115, 66), [(x + dx - 7, py + 13), (x + dx, py - 16), (x + dx + 8, py + 13)])
                pygame.draw.circle(surface, (255, 211, 98), (x + dx, py + 7), 5)
        pygame.draw.polygon(surface, deep, [p(-31, 14), p(26, 12), p(44, 62), p(-41, 64)])
        pygame.draw.polygon(surface, cape, [p(-27, 11), p(21, 10), p(33, 61), p(-33, 60)])
        pygame.draw.polygon(surface, (189, 123, 196) if is_player else (104, 181, 199), [p(-8, 8), p(12, 13), p(11, 58), p(-8, 58)])
        pygame.draw.line(surface, trim, p(-30, 57), p(31, 57), 4)
        if rank >= 3:
            for stripe in range(3):
                py = 24 + stripe * 11
                pygame.draw.line(surface, trim, p(-24, py), p(-19, py + 2), 2)
                pygame.draw.line(surface, trim, p(22, py), p(17, py + 2), 2)
            pygame.draw.polygon(surface, trim, [p(-4, 24), p(0, 16), p(5, 24), p(0, 33)])
        if rank >= 6:
            pygame.draw.arc(surface, (242, 216, 255), (x - 44, y + 7, 88, 59), 0.2, 2.9, 3)
            for side in (-1, 1):
                pygame.draw.polygon(surface, trim, [p(side * 24, 11), p(side * 40, 19),
                                                   p(side * 30, 33), p(side * 16, 25)])
        if rank >= 8:
            for gem_x, gem_y in ((-18, 37), (0, 44), (18, 37)):
                pygame.draw.circle(surface, (255, 255, 217), p(gem_x, gem_y), 3)
        pygame.draw.ellipse(surface, deep, (x - 34, y + 59, 26, 14))
        pygame.draw.ellipse(surface, deep, (x + 12, y + 59, 26, 14))
        staff_y = -55 - round(casting * 20)
        pygame.draw.circle(surface, (98, 57, 55), p(33, 11 - casting * 9), 12)
        pygame.draw.circle(surface, cream, p(33, 8 - casting * 9), 10)
        pygame.draw.line(surface, (96, 56, 54), p(35, 9 - casting * 8), p(66, staff_y), 7)
        pygame.draw.line(surface, (238, 179, 83), p(36, 8 - casting * 8), p(67, staff_y), 3)
        orb_color = ELEMENT_COLORS[wizard.casting_element] if casting > 0 else trim
        pygame.draw.circle(surface, orb_color, p(67, staff_y - 2), 12 + round(casting * 4))
        pygame.draw.circle(surface, (255, 250, 224), p(67, staff_y - 2), 5 + round(casting * 3))
        if casting > 0:
            for angle in range(0, 360, 60):
                rad = math.radians(angle + time * 200)
                px, py = p(67 + math.cos(rad) * (19 + casting * 8), staff_y + math.sin(rad) * (19 + casting * 8))
                pygame.draw.circle(surface, orb_color, (px, py), 3)
        pygame.draw.circle(surface, deep, p(0, -29), 29)
        pygame.draw.circle(surface, cream, p(0, -32), 25)
        pygame.draw.circle(surface, (255, 151, 145), p(-18, -25), 5)
        pygame.draw.circle(surface, (255, 151, 145), p(18, -25), 5)
        if hit > 0.12:
            for offset in (-9, 9):
                pygame.draw.line(surface, (50, 36, 64), (x + offset - 4, y - 36), (x + offset + 4, y - 29), 3)
                pygame.draw.line(surface, (50, 36, 64), (x + offset + 4, y - 36), (x + offset - 4, y - 29), 3)
            pygame.draw.ellipse(surface, (120, 69, 82), (x - 4, y - 22, 8, 9))
        else:
            pygame.draw.ellipse(surface, (43, 31, 60), (x - 13, y - 36, 7, 11))
            pygame.draw.ellipse(surface, (43, 31, 60), (x + 7, y - 36, 7, 11))
            pygame.draw.circle(surface, (255, 255, 255), (x - 11, y - 33), 2)
            pygame.draw.circle(surface, (255, 255, 255), (x + 9, y - 33), 2)
            pygame.draw.arc(surface, (148, 83, 82), (x - 9, y - 27, 18, 10), 0, math.pi, 2)
        pygame.draw.polygon(surface, deep, [p(-42, -56), p(40, -56), p(3, -113)])
        pygame.draw.polygon(surface, hat, [p(-34, -59), p(35, -59), p(3, -108)])
        pygame.draw.polygon(surface, (154, 103, 177) if is_player else (91, 171, 187), [p(2, -109), p(21, -70), p(8, -73)])
        pygame.draw.ellipse(surface, deep, (x - 44, y - 64, 88, 18))
        pygame.draw.ellipse(surface, hat, (x - 42, y - 68, 84, 16))
        pygame.draw.line(surface, trim, p(-28, -66), p(27, -66), 5)
        pygame.draw.circle(surface, (255, 232, 148), p(0, -66), 5)
        pygame.draw.circle(surface, (255, 255, 222), p(0, -66), 2)
        if rank >= 2:
            for i in range(1 + rank // 2):
                pos_x = -23 + i * 14
                pygame.draw.circle(surface, (255, 239, 158), p(pos_x, -64), 2)
        if rank >= 4:
            pygame.draw.polygon(surface, (255, 220, 124), [p(-15, -84), p(-2, -112), p(10, -85), p(0, -89)])
            pygame.draw.circle(surface, (239, 245, 255), p(0, -88), 4)
        if rank >= 6:
            for i in range(3):
                angle = time * 1.4 + i * math.tau / 3
                px = x + round(math.cos(angle) * 28)
                py = y - 121 + round(math.sin(angle) * 12)
                pygame.draw.circle(surface, (255, 239, 174), (px, py), 4)
        if rank >= 8:
            pygame.draw.arc(surface, (255, 228, 125), (x - 48, y - 146, 96, 27), 0, math.tau, 4)
            for offset in (-39, -13, 13, 39):
                pygame.draw.polygon(surface, (255, 241, 172),
                                    [(x + offset - 6, y - 136), (x + offset, y - 152),
                                     (x + offset + 6, y - 136)])
            pygame.draw.circle(surface, (243, 255, 255), p(67, staff_y - 2), 12, 3)
        if hit > 0.25:
            tint = pygame.Surface((90, 147), pygame.SRCALPHA)
            tint.fill((255, 116, 115, round(85 * hit)))
            surface.blit(tint, (x - 45, y - 113))

    def _projectile(self, surface: pygame.Surface, projectile: Projectile, time: float):
        if fusion_projectile(surface, projectile, time):
            return
        if elite_projectile(surface, projectile, time):
            return
        x = round(projectile.x)
        y = round(projectile.y + math.sin(time * 10 + projectile.age * 5) * 5)
        radius = projectile.radius
        direction = projectile.direction
        element = projectile.element
        spec = spell_for(element, projectile.tier)
        color = spec.color
        halo = pygame.Surface((radius * 5, radius * 5), pygame.SRCALPHA)
        center = radius * 5 // 2
        pygame.draw.circle(halo, (*color, 33), (center, center), radius * 2)
        pygame.draw.circle(halo, (*color, 72), (center, center), round(radius * 1.35))
        surface.blit(halo, (x - center, y - center))
        if element == Element.FIRE and spec.trait == "lightning":
            points = [(x - 40 * direction, y + 8)]
            for i in range(1, 6):
                px = x - (38 - i * 10) * direction
                py = y + round(math.sin(time * 28 + i * 4 + projectile.age * 23) * (8 + projectile.tier * 2))
                points.append((px, py))
            for a, b in zip(points, points[1:]):
                pygame.draw.line(surface, (255, 156, 62), a, b, 8)
                pygame.draw.line(surface, (255, 246, 153), a, b, 4)
            for shift in range(-1, 2):
                pygame.draw.line(surface, (255, 224, 147), (x - 4, y), (x + 22 * direction, y + shift * 15), 2)
            pygame.draw.circle(surface, (255, 251, 217), (x, y), max(6, radius - 4))
        elif element == Element.FIRE:
            for i in range(3):
                shift = round(math.sin(time * 21 + i * 2) * (6 + projectile.tier))
                pygame.draw.polygon(surface, (249, 78 + i * 20, 48), [
                    (x - (36 + i * 11) * direction, y + shift),
                    (x - 10 * direction, y - radius - i),
                    (x + radius * direction, y),
                    (x - 9 * direction, y + radius + i),
                ])
            pygame.draw.circle(surface, (253, 146, 55), (x, y), radius)
            pygame.draw.circle(surface, (255, 224, 103), (x + 3 * direction, y - 2), max(5, radius - 6))
            pygame.draw.circle(surface, (255, 255, 215), (x + 6 * direction, y - 4), max(3, radius // 3))
        elif element == Element.EARTH:
            for i in range(4):
                back = (13 + i * 12) * direction
                pygame.draw.circle(surface, (186, 150, 99), (x - back, y + (i % 2) * 9 - 5), max(2, radius // 4 - i))
            points = []
            for index in range(7):
                rad = index * math.tau / 7 + time * 3
                r = radius * (1.0 if index % 2 else 0.85)
                points.append((x + round(math.cos(rad) * r), y + round(math.sin(rad) * r)))
            pygame.draw.polygon(surface, (115, 82, 67), points)
            pygame.draw.polygon(surface, color, [(x - radius // 2, y - radius // 3), (x, y - radius + 3),
                                                  (x + radius - 4, y - 4), (x + 4, y + radius // 2),
                                                  (x - radius + 5, y + 3)])
            pygame.draw.line(surface, (255, 228, 174), (x - 6, y - radius // 2), (x + 4, y - radius + 5), 3)
        elif element == Element.WATER:
            pygame.draw.polygon(surface, (64, 152, 230), [
                (x - (radius + 28) * direction, y), (x - radius * direction, y - radius),
                (x + radius * direction, y - radius // 2), (x + radius * direction, y + radius // 2),
                (x - radius * direction, y + radius),
            ])
            pygame.draw.ellipse(surface, color, (x - radius, y - radius, radius * 2, radius * 2))
            pygame.draw.ellipse(surface, (168, 250, 253), (x - radius // 2, y - radius // 2, radius, radius))
            for i in range(3):
                dx = x - (radius + i * 14) * direction
                pygame.draw.circle(surface, (115, 225, 255), (dx, y + round(math.sin(time * 11 + i) * 10)), 3 + projectile.tier // 2)
        elif element == Element.AIR:
            for i in range(4):
                phase = time * 15 + i * 1.4
                offset = round(math.sin(phase) * (radius * 0.6))
                px = x - (i * 12) * direction
                pygame.draw.arc(surface, (94, 179, 161), (px - radius, y - radius + offset, radius * 2, radius * 2),
                                math.pi * 0.15, math.pi * 1.75, 5)
                pygame.draw.arc(surface, (218, 255, 224), (px - radius, y - radius + offset, radius * 2, radius * 2),
                                math.pi * 0.25, math.pi * 1.6, 2)
            pygame.draw.circle(surface, (250, 255, 234), (x + 5 * direction, y), max(4, radius // 3))

    def _bar(self, surface, x, y, width, height, ratio, color):
        pygame.draw.rect(surface, (23, 19, 38), (x, y, width, height), border_radius=height // 2)
        inner = pygame.Rect(x + 3, y + 3, max(0, round((width - 6) * ratio)), height - 6)
        if inner.width:
            pygame.draw.rect(surface, color, inner, border_radius=max(1, (height - 6) // 2))
            if inner.width > 16:
                pygame.draw.line(surface, (255, 255, 255), (inner.x + 5, inner.y + 2), (inner.right - 5, inner.y + 2), 1)
        pygame.draw.rect(surface, (135, 110, 153), (x, y, width, height), 2, border_radius=height // 2)

    def _hud(self, surface: pygame.Surface, duel: Duel, progress: Progress | None = None):
        for x, wizard, name in ((27, duel.player, "YOUR WIZARD"), (786, duel.ai, "RIVAL WIZARD")):
            pygame.draw.rect(surface, (99, 63, 66), (x, 22, 368, 102), border_radius=16)
            pygame.draw.rect(surface, PANEL, (x + 3, 23, 362, 96), border_radius=14)
            pygame.draw.rect(surface, (221, 170, 99), (x + 3, 23, 362, 96), 2, border_radius=14)
            self._text(surface, name, x + 19, 32, "title", (254, 220, 154))
            if wizard.side == "player" and progress is not None:
                rank_position = f"{progress.points % POINTS_PER_RANK}/{POINTS_PER_RANK}" if progress.next_title else "MAX RANK"
                self._text(surface, f"{progress.title.upper()}  |  {progress.points} PTS  |  {rank_position}",
                           x + 19, 49, "tiny", (219, 183, 250))
            self._text(surface, f"{wizard.health} / {MAX_HEALTH} HP", x + 252, 34, "small", LIGHT_TEXT)
            self._bar(surface, x + 19, 61, 329, 19, wizard.health_ratio,
                      (105, 224, 139) if wizard.health_ratio > 0.3 else (244, 105, 111))
            self._text(surface, f"TIER {wizard.level} SPELLS", x + 20, 91, "small", (245, 212, 143))
            completion = progress.rank_progress if progress is not None else 0.0
            self._bar(surface, x + 151, 97, 124, 9, completion, (186, 145, 255))
            self._text(surface, "PERMANENT", x + 282, 90, "tiny", MUTED_TEXT)
            if wizard.shield > 0:
                pygame.draw.circle(surface, (172, 131, 255), (x + 345, 15), 8)
        pygame.draw.rect(surface, (123, 80, 74), (423, 12, 334, 112), border_radius=23)
        pygame.draw.rect(surface, PANEL, (427, 15, 326, 106), border_radius=21)
        pygame.draw.rect(surface, GOLD, (427, 15, 326, 106), 3, border_radius=21)
        self._text(surface, "QUIZMANCERS", WIDTH // 2, 26, "logo", (255, 223, 145), center=True, shadow=True)
        self._text(surface, f"ROUND {math.ceil(duel.seconds_left)}s    H: GUIDE", WIDTH // 2, 77,
                   "small", (213, 198, 232), center=True)
        pulse_text = "SPACE: PARRY READY" if duel.player.pulse_cooldown <= 0 else f"PARRY RECHARGES {duel.player.pulse_cooldown:.1f}s"
        self._text(surface, pulse_text, WIDTH // 2, 94, "tiny",
                   (167, 251, 214) if duel.player.pulse_cooldown <= 0 else (225, 185, 210), center=True)
        self._text(surface, f"AI: {duel.difficulty.upper()}   ESC: MENU", WIDTH // 2, 109,
                   "tiny", (231, 209, 233), center=True)

    def _spell_icon(self, surface: pygame.Surface, kind: Element, cx: int, cy: int, radius: int = 20):
        colors = {
            Element.FIRE: ((146, 53, 62), (255, 133, 66)),
            Element.EARTH: ((95, 75, 63), (202, 171, 116)),
            Element.WATER: ((41, 87, 139), (125, 229, 255)),
            Element.AIR: ((48, 111, 98), (193, 250, 215)),
            Element.SPIRIT: ((100, 65, 146), (221, 172, 255)),
        }
        outer, inner = colors[kind]
        pygame.draw.circle(surface, outer, (cx, cy), radius)
        if kind == Element.FIRE:
            pygame.draw.polygon(surface, inner, [(cx - 10, cy + 13), (cx - 7, cy - 13), (cx + 3, cy - 2),
                                                 (cx + 9, cy - 17), (cx + 13, cy + 14)])
            pygame.draw.polygon(surface, (255, 246, 183), [(cx - 4, cy + 13), (cx + 3, cy - 1), (cx + 8, cy + 13)])
        elif kind == Element.EARTH:
            pygame.draw.polygon(surface, inner, [(cx - 13, cy + 8), (cx - 5, cy - 13), (cx + 12, cy - 10),
                                                 (cx + 16, cy + 6), (cx, cy + 15)])
            pygame.draw.line(surface, (255, 231, 175), (cx - 6, cy - 9), (cx + 3, cy - 11), 3)
        elif kind == Element.WATER:
            pygame.draw.polygon(surface, inner, [(cx, cy - 18), (cx - 12, cy), (cx - 11, cy + 10),
                                                 (cx, cy + 16), (cx + 11, cy + 10), (cx + 12, cy)])
            pygame.draw.ellipse(surface, (215, 255, 255), (cx - 6, cy - 1, 6, 9))
        elif kind == Element.AIR:
            for offset in (-7, 0, 8):
                pygame.draw.arc(surface, inner, (cx - 14, cy - 12 + offset, 29, 20), 0, math.pi * 1.5, 3)
        else:
            pygame.draw.polygon(surface, inner, [(cx, cy - 17), (cx + 14, cy - 11), (cx + 13, cy + 9),
                                                 (cx, cy + 17), (cx - 13, cy + 9), (cx - 14, cy - 11)])
            pygame.draw.circle(surface, (255, 247, 233), (cx, cy - 2), 6)

    def _spell_card(self, surface, kind: Element, duel: Duel, hover: bool):
        rect = self.spell_rects[kind]
        selected = duel.selected_element == kind
        fusion_ready = any(element == kind for element, _ in duel.player_fusion_options())
        outer = (165, 255, 198) if fusion_ready else (255, 217, 140) if selected else (122, 103, 144)
        fill = (101, 63, 96) if selected else (63, 46, 91) if hover else PANEL_ALT
        pygame.draw.rect(surface, (21, 16, 43), rect.move(0, 4), border_radius=13)
        pygame.draw.rect(surface, fill, rect, border_radius=13)
        pygame.draw.rect(surface, outer, rect, 3 if selected else 2, border_radius=13)
        self._text(surface, ELEMENT_KEYS[kind], rect.x + 12, rect.y + 10, "title", (255, 234, 172))
        self._text(surface, f"LV {duel.player.level}", rect.right - 42, rect.y + 12, "tiny", MUTED_TEXT)
        self._spell_icon(surface, kind, rect.centerx, rect.y + 43, 19)
        name = spell_for(kind, duel.player.level).name
        card_font = "card_small" if self.fonts["card"].render(name.upper(), True, LIGHT_TEXT).get_width() > rect.width - 8 else "card"
        self._text(surface, name.upper(), rect.centerx, rect.y + 72, card_font, LIGHT_TEXT, center=True)
        if fusion_ready:
            self._text(surface, "FUSION READY", rect.centerx, rect.y + 84, "tiny", (160, 255, 199), center=True)
        elif selected:
            pygame.draw.rect(surface, (255, 222, 142), (rect.x + 18, rect.y + 94, rect.width - 36, 3), border_radius=1)

    def _wrapped(self, text: str, font_name: str, max_width: int, lines: int = 2):
        words = text.split()
        result = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if current and self.fonts[font_name].size(trial)[0] > max_width:
                result.append(current)
                current = word
            else:
                current = trial
        if current:
            result.append(current)
        return result[:lines]

    def _question_ui(self, surface: pygame.Surface, duel: Duel, answer: str, effects: Effects, mouse_pos, choice_selected=None):
        pygame.draw.rect(surface, (16, 12, 32), (17, 524, 1146, 184), border_radius=21)
        pygame.draw.rect(surface, PANEL, (22, 525, 1136, 177), border_radius=20)
        pygame.draw.rect(surface, (197, 146, 113), (22, 525, 1136, 177), 2, border_radius=20)
        heading = duel.topic.upper() + " CHALLENGE"
        heading_font = "title" if self.fonts["title"].size(heading)[0] <= 275 else "small"
        if self.fonts[heading_font].size(heading)[0] > 275:
            heading = heading[:35] + "..."
        self._text(surface, heading, 48, 539, heading_font, (255, 220, 141))
        if duel.retry_remaining > 0:
            self._text(surface, "SPELL UNSTABLE!", 312, 540, "tiny", (255, 153, 118))
        elif duel.player_question_active and duel.player_question_is_review:
            self._text(surface, "REVIEW FOCUS", 313, 540, "tiny", (152, 236, 204))
        remaining = duel.question_seconds_left
        timer_color = (255, 139, 143) if remaining < 4 or duel.retry_remaining > 0 else (205, 193, 227)
        self._text(surface, "--" if duel.player_waiting else f"{remaining:04.1f}s", 423, 539, "small", timer_color)
        pygame.draw.rect(surface, (83, 61, 99), (48, 566, 429, 5), border_radius=2)
        ratio = (remaining / max(0.1, duel.pace.retry_seconds) if duel.retry_remaining > 0
                 else remaining / duel.question_duration if duel.player_question_active else 0.0)
        pygame.draw.rect(surface, (252, 193, 95), (48, 566, round(429 * ratio), 5), border_radius=2)
        if duel.player_waiting:
            if duel.player_feedback:
                self._text(surface, "LEARN FROM THE MISCAST", 260, 584, "popup", (255, 182, 150), center=True)
                self._text(surface, duel.player_feedback, 260, 625, "small", (255, 227, 172), center=True)
                self._text(surface, "Take a moment to review before the next question.", 260, 653,
                           "small", (195, 212, 235), center=True)
            else:
                self._text(surface, "WATCH YOUR SPELL!", 260, 584, "popup", (254, 220, 145), center=True)
                waiting = ("Spell travelling... next question after impact."
                           if duel._spell_in_flight("player") else "Preparing the next question...")
                self._text(surface, waiting, 260, 625, "small", (210, 201, 230), center=True)
                self._text(surface, "You can still switch elements or parry.", 260, 653,
                           "small", (158, 237, 213), center=True)
        elif duel.player_question.options:
            for index, line in enumerate(self._wrapped(duel.player_question.prompt, "body", 425, 2)):
                self._text(surface, line, 48, 577 + index * 21, "body", LIGHT_TEXT)
            for index, option in enumerate(duel.player_question.options):
                rect = self.choice_rects[index]
                hover = rect.collidepoint(mouse_pos)
                selected = choice_selected == index + 1
                pygame.draw.rect(surface, (137, 98, 106) if selected else (100, 76, 129) if hover else (64, 47, 91), rect, border_radius=7)
                pygame.draw.rect(surface, (255, 221, 135) if selected else (226, 190, 135) if hover else (129, 105, 151), rect, 3 if selected else 2, border_radius=7)
                font = "card" if self.fonts["card"].size(option)[0] <= 165 else "card_small"
                self._text(surface, str(index + 1), rect.x + 8, rect.y + 8, "card", (255, 221, 145))
                self._text(surface, option, rect.x + 28, rect.y + (8 if font == "card" else 9),
                           font, LIGHT_TEXT)
        else:
            self._text(surface, duel.player_question.prompt, 48, 580, "question", LIGHT_TEXT, shadow=True)
            input_rect = pygame.Rect(48, 630, 237, 45)
            pygame.draw.rect(surface, (255, 246, 226), input_rect, border_radius=10)
            pygame.draw.rect(surface, GOLD, input_rect, 2, border_radius=10)
            visible_answer = answer + ("|" if int(pygame.time.get_ticks() / 550) % 2 == 0 else "")
            self._text(surface, visible_answer or "Type an answer...", 63, 637,
                       "input" if answer else "body", INK if answer else (149, 128, 147))
            hovered = self.cast_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, (232, 168, 78) if hovered else GOLD, self.cast_rect, border_radius=10)
            self._text(surface, "CAST!", self.cast_rect.centerx, 640, "body", (63, 39, 63), center=True)
        if effects.feedback_lifetime > 0:
            text, color = effects.feedback, effects.feedback_color
        elif duel.player_question.options:
            text, color = ("SPELL UNSTABLE! CORRECT IT, THEN ENTER" if duel.retry_remaining > 0
                           else "SELECT 1-4  ·  ENTER OR CLICK AGAIN TO CAST"), MUTED_TEXT
        else:
            text, color = ("SPELL UNSTABLE! CORRECT IT, THEN ENTER" if duel.retry_remaining > 0
                           else "Q W E R T: SPELLS   ·   ENTER: CAST"), MUTED_TEXT
        self._text(surface, text, 49, 685, "small", color)
        if duel.player.combo >= 2:
            self._text(surface, f"{duel.player.combo}x STREAK", 354, 685, "small", (163, 255, 211))
        self._text(surface, "FIVE ELEMENTS · PERMANENT SPELL TIERS", 511, 541, "title", (255, 220, 141))
        self._text(surface, "SPELLS RESOLVE BEFORE NEW QUESTIONS", 915, 543, "tiny", MUTED_TEXT)
        for element in ELEMENT_ORDER:
            self._spell_card(surface, element, duel, self.spell_rects[element].collidepoint(mouse_pos))

    def _fusion_hint(self, surface: pygame.Surface, duel: Duel):
        options = duel.player_fusion_options()
        if not options:
            return
        parts = [f"[{ELEMENT_KEYS[element]}] {fusion.name.upper()}" for element, fusion in options]
        description = "  |  ".join(parts)
        box = pygame.Rect(275, 488, 630, 29)
        pygame.draw.rect(surface, (57, 40, 73), box, border_radius=12)
        pygame.draw.rect(surface, (157, 236, 182), box, 2, border_radius=12)
        self._text(surface, description, WIDTH // 2, 495, "small", (183, 255, 199), center=True)

    def _fusion_banner(self, surface: pygame.Surface, effects: Effects):
        if effects.fusion_banner_lifetime > 0:
            box = pygame.Rect(376, 179, 428, 50)
            pygame.draw.rect(surface, (48, 32, 68), box, border_radius=14)
            pygame.draw.rect(surface, (249, 211, 117), box, 3, border_radius=14)
            self._text(surface, effects.fusion_banner, WIDTH // 2, 188,
                       "popup", (255, 236, 153), center=True)
        elif effects.ultimate_banner_lifetime > 0 and effects.level_banner_lifetime <= 0:
            box = pygame.Rect(395, 178, 390, 45)
            pygame.draw.rect(surface, (57, 35, 65), box, border_radius=12)
            pygame.draw.rect(surface, (255, 190, 113), box, 2, border_radius=12)
            self._text(surface, effects.ultimate_banner, WIDTH // 2, 188,
                       "body", (255, 227, 172), center=True)

    def _level_banner(self, surface: pygame.Surface, effects: Effects):
        if effects.level_banner_lifetime <= 0:
            return
        alpha = min(1.0, effects.level_banner_lifetime * 2)
        panel = pygame.Surface((440, 67), pygame.SRCALPHA)
        pygame.draw.rect(panel, (41, 29, 71, round(227 * alpha)), (0, 0, 440, 67), border_radius=16)
        pygame.draw.rect(panel, (227, 180, 255, round(247 * alpha)), (0, 0, 440, 67), 3, border_radius=16)
        surface.blit(panel, (WIDTH // 2 - 220, 140))
        self._text(surface, effects.level_banner, WIDTH // 2, 158, "popup", (255, 231, 167), center=True)

    def _guide(self, surface: pygame.Surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((23, 17, 37, 142))
        surface.blit(overlay, (0, 0))
        box = pygame.Rect(240, 154, 700, 343)
        pygame.draw.rect(surface, PANEL, box, border_radius=24)
        pygame.draw.rect(surface, GOLD, box, 4, border_radius=24)
        self._text(surface, "ELEMENTAL COMBAT GUIDE", WIDTH // 2, 181, "popup", (255, 218, 142), center=True)
        lines = [
            ("FIRE", "Burns, defeats EARTH. Lightning hits SOAKED targets harder."),
            ("EARTH", "Cracks spirit shields. Stone defeats incoming AIR."),
            ("WATER", "Removes burns, SOAKS targets and extinguishes FIRE."),
            ("AIR", "Fast projectiles pierce shields and defeat WATER."),
            ("SPIRIT", "Protective ward, healing aura, and LV 4 reflection."),
        ]
        for index, (name, desc) in enumerate(lines):
            y = 242 + index * 43
            element = ELEMENT_ORDER[index]
            pygame.draw.circle(surface, ELEMENT_COLORS[element], (278, y + 10), 7)
            self._text(surface, name, 297, y, "title", LIGHT_TEXT)
            self._text(surface, desc, 404, y + 1, "small", (227, 211, 238))
        self._text(surface, "Element combinations activate automatically with compatible correct casts.",
                   WIDTH // 2, 465, "small", (255, 221, 169), center=True)
        self._text(surface, "PRESS H TO CLOSE", WIDTH // 2, 508, "small", (255, 234, 194), center=True)

    def _finish_overlay(self, surface: pygame.Surface, duel: Duel,
                        progress: Progress | None = None, change: RankChange | None = None,
                        save_error: bool = False):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((19, 12, 32, 178))
        surface.blit(overlay, (0, 0))
        rect = pygame.Rect(321, 203, 538, 303)
        pygame.draw.rect(surface, (15, 13, 29), rect.move(0, 9), border_radius=24)
        pygame.draw.rect(surface, PANEL, rect, border_radius=24)
        pygame.draw.rect(surface, GOLD, rect, 4, border_radius=24)
        if duel.winner == "player":
            title, color, subtitle = "VICTORY!", (253, 215, 121), "The arena belongs to you."
        elif duel.winner == "ai":
            title, color, subtitle = "DEFEAT", (255, 148, 149), "The rival wizard wins this round."
        else:
            title, color, subtitle = "DRAW!", (171, 232, 242), "An evenly matched magical battle."
        self._text(surface, title, WIDTH // 2, 236, "winner", color, center=True, shadow=True)
        self._text(surface, subtitle, WIDTH // 2, 317, "body", LIGHT_TEXT, center=True)
        self._text(surface, f"YOU  {duel.player.health} HP (TIER {duel.player.level})    |    "
                   f"RIVAL  {duel.ai.health} HP (TIER {duel.ai.level})", WIDTH // 2, 354, "body",
                   (219, 204, 230), center=True)
        if progress is not None and change is not None:
            if change.promoted:
                status = f"RANK UP! {progress.title.upper()}"
                rank_color = (255, 217, 126)
            elif change.demoted:
                status = f"RANK DOWN: {progress.title.upper()}"
                rank_color = (248, 160, 177)
            else:
                status = f"RANK: {progress.title.upper()}"
                rank_color = (228, 208, 249)
            self._text(surface, status, WIDTH // 2, 388, "popup", rank_color, center=True)
            if change.winner == "player":
                outcome = f"WIN: +1 POINT  |  TOTAL: {progress.points}"
            elif change.winner == "ai":
                outcome = (f"LOSS: -1 POINT  |  TOTAL: {progress.points}" if change.delta < 0
                           else "LOSS: 0 POINTS (MINIMUM REACHED)")
            else:
                outcome = f"DRAW: NO CHANGE  |  TOTAL: {progress.points}"
            self._text(surface, outcome, WIDTH // 2, 419, "small", (222, 214, 237), center=True)
            next_line = (f"{progress.points_to_next} more points to {progress.next_title}"
                         if progress.next_title else "You have reached the highest rank: Archmage")
            self._text(surface, next_line, WIDTH // 2, 440, "small", (214, 182, 248), center=True)
        pygame.draw.rect(surface, (255, 207, 124), self.rematch_rect, border_radius=10)
        pygame.draw.rect(surface, (95, 76, 126), self.back_menu_rect, border_radius=10)
        self._text(surface, "R  REMATCH", self.rematch_rect.centerx, 469, "body", (47, 32, 53), center=True)
        self._text(surface, "M  MAIN MENU", self.back_menu_rect.centerx, 469, "body", LIGHT_TEXT, center=True)
        if save_error:
            self._text(surface, "SAVE FAILED - CHECK FOLDER PERMISSIONS", WIDTH // 2, 488,
                       "tiny", (255, 148, 149), center=True)

    def draw(self, surface: pygame.Surface, duel: Duel, answer: str, effects: Effects, time: float,
             mouse_pos, show_guide: bool = False, progress: Progress | None = None,
             change: RankChange | None = None, save_error: bool = False, choice_selected=None):
        surface.blit(self.background, (0, 0))
        ambient(surface, time)
        ultimate_atmosphere(surface, duel, time)
        for area in duel.areas:
            if not fusion_area(surface, area, time):
                arena_area(surface, area, time)
        jitter_x = round(math.sin(time * 47) * effects.shake * 0.7)
        jitter_y = round(math.sin(time * 39) * effects.shake * 0.3)
        self._wizard(surface, PLAYER_X + jitter_x, WIZARD_Y + jitter_y, 1, time, True, duel.player,
                     progress.rank_index if progress is not None else 0)
        self._wizard(surface, AI_X + jitter_x, WIZARD_Y + jitter_y, -1, time, False, duel.ai,
                     progress.rank_index if progress is not None else 0)
        wizard_impact(surface, PLAYER_X + jitter_x, WIZARD_Y + jitter_y, duel.player, time)
        wizard_impact(surface, AI_X + jitter_x, WIZARD_Y + jitter_y, duel.ai, time)
        player_charge = min(1.0, 0.06 + len(answer) * 0.24 + duel.player_question_elapsed * 0.018)
        conjuring(surface, PLAYER_X, WIZARD_Y, player_charge, duel.selected_element, time, 1)
        conjuring(surface, AI_X, WIZARD_Y, duel.ai_thinking_ratio,
                  duel.ai.casting_element, time, -1)
        if duel.player.pulse_remaining > 0:
            pulse(surface, PLAYER_X, WIZARD_Y, duel.player.pulse_remaining, time)
        if duel.ai.pulse_remaining > 0:
            pulse(surface, AI_X, WIZARD_Y, duel.ai.pulse_remaining, time)
        if duel.player.sanctuary_remaining > 0:
            pygame.draw.circle(surface, (224, 185, 255), (PLAYER_X, WIZARD_Y - 28), 104, 3)
        if duel.ai.sanctuary_remaining > 0:
            pygame.draw.circle(surface, (224, 185, 255), (AI_X, WIZARD_Y - 28), 104, 3)
        self._text(surface, "SPELL IN FLIGHT" if duel.player_waiting else "CHANNELING",
                   PLAYER_X, 231, "small", (98, 67, 116), center=True)
        self._text(surface, "RIVAL SPELL IN FLIGHT" if duel.ai_waiting else "RIVAL CHANNELING",
                   AI_X, 231, "small", (98, 67, 116), center=True)
        self._bar(surface, AI_X - 54, 251, 108, 8, duel.ai_thinking_ratio, (155, 203, 239))
        for projectile in duel.projectiles:
            self._projectile(surface, projectile, time)
        effects.draw(surface, self.fonts["popup"])
        self._hud(surface, duel, progress)
        self._fusion_hint(surface, duel)
        self._question_ui(surface, duel, answer, effects, mouse_pos, choice_selected)
        self._level_banner(surface, effects)
        self._fusion_banner(surface, effects)
        if show_guide and not duel.finished:
            self._guide(surface)
        if duel.finished:
            self._finish_overlay(surface, duel, progress, change, save_error)

    def draw_menu(self, surface: pygame.Surface, progress: Progress, difficulty: str, topic: str, time: float,
                  mouse_pos: tuple[int, int], save_error: bool = False,
                  revision_summary: RevisionSummary | None = None,
                  selection: StudySelection | None = None, active_field: str = "subtopic",
                  pace: str = "Standard") -> None:
        surface.blit(self.background, (0, 0))
        ambient(surface, time)
        rank = progress.rank_index
        tier = tier_for_rank(rank)
        self._wizard(surface, 202, 370, 1, time, True, Wizard("player", 202, level=tier), rank)
        self._wizard(surface, 980, 370, -1, time, False, Wizard("ai", 980, level=tier), rank)
        panel = pygame.Surface((630, 653), pygame.SRCALPHA)
        pygame.draw.rect(panel, (34, 25, 55, 242), panel.get_rect(), border_radius=23)
        pygame.draw.rect(panel, (245, 201, 121, 255), panel.get_rect(), 3, border_radius=23)
        surface.blit(panel, (275, 38))
        self._text(surface, "QUIZMANCERS", WIDTH // 2, 65, "winner", (255, 223, 148), center=True, shadow=True)
        self._text(surface, "CHOOSE WHAT YOU WANT TO REVISE", WIDTH // 2, 120, "small", (232, 203, 243), center=True)
        self._text(surface, progress.title.upper(), WIDTH // 2, 148, "popup", (255, 233, 177), center=True)
        self._text(surface, f"{progress.points} RANK POINTS  ·  {progress.wins} WINS  ·  {progress.losses} LOSSES",
                   WIDTH // 2, 177, "small", (215, 201, 228), center=True)
        self._bar(surface, 396, 200, 388, 11, progress.rank_progress, (185, 138, 249))
        advancement = (f"{progress.points_to_next} points until {progress.next_title}"
                       if progress.next_title else "MAXIMUM RANK: ARCHMAGE")
        self._text(surface, f"SPELL TIER {tier} / 4   ·   {advancement}",
                   WIDTH // 2, 221, "small", (250, 216, 153), center=True)
        if selection is None:
            selection = StudySelection(subtopic=topic)
        values = {
            "course": selection.course,
            "board": selection.board,
            "subject": selection.subject,
            "subtopic": selection.subtopic,
        }
        labels = {
            "course": "COURSE / KEY STAGE",
            "board": "EXAM BOARD",
            "subject": "SUBJECT",
            "subtopic": "SUBTOPIC / QUESTION SET",
        }
        for field, (previous, value, following) in self.menu_selector_rects.items():
            highlight = field == active_field
            label_y = value.y - 18
            self._text(surface, labels[field], WIDTH // 2, label_y, "tiny",
                       (255, 222, 148) if highlight else (216, 191, 226), center=True)
            for rect in (previous, value, following):
                background = (112, 81, 134) if highlight else (67, 50, 96)
                if rect.collidepoint(mouse_pos):
                    background = (136, 102, 160)
                pygame.draw.rect(surface, background, rect, border_radius=9)
                pygame.draw.rect(surface, (233, 189, 119) if highlight else (148, 119, 176),
                                 rect, 2, border_radius=9)
            self._text(surface, "<", previous.centerx, previous.y + 5, "popup", LIGHT_TEXT, center=True)
            self._text(surface, ">", following.centerx, following.y + 5, "popup", LIGHT_TEXT, center=True)
            value_text = values[field]
            font = "body" if self.fonts["body"].size(value_text)[0] <= value.width - 14 else "small"
            self._text(surface, value_text, value.centerx,
                       value.y + (8 if font == "body" else 11), font,
                       (255, 227, 154) if highlight else LIGHT_TEXT, center=True)
        if revision_summary is not None:
            if revision_summary.attempts:
                revision_text = (f"REVISION: {revision_summary.to_review} TO REVISIT   ·   "
                                 f"{revision_summary.mastered} MASTERED   ·   "
                                 f"{revision_summary.accuracy}% ACCURACY")
            else:
                revision_text = "NEW TOPIC · YOUR PRACTICE PROGRESS SAVES AUTOMATICALLY"
            self._text(surface, revision_text, WIDTH // 2, 519, "tiny", (176, 236, 211), center=True)
        pygame.draw.rect(surface, (255, 207, 124) if self.menu_play_rect.collidepoint(mouse_pos)
                         else (238, 181, 106), self.menu_play_rect, border_radius=12)
        self._text(surface, "START DUEL", WIDTH // 2, 559, "popup", (51, 33, 65), center=True)
        self._text(surface, "ENTER", WIDTH // 2, 584, "tiny", (73, 46, 68), center=True)
        for rect, label in ((self.menu_difficulty_rect, f"AI: {difficulty.upper()}"),
                            (self.menu_pace_rect, f"PACE: {pace.upper()}")):
            pygame.draw.rect(surface, (99, 74, 124) if rect.collidepoint(mouse_pos)
                             else (76, 57, 102), rect, border_radius=9)
            pygame.draw.rect(surface, (150, 123, 180), rect, 2, border_radius=9)
            self._text(surface, label, rect.centerx, 622, "small", LIGHT_TEXT, center=True)
        self._text(surface, "UP/DOWN: FIELD  ·  LEFT/RIGHT: CHANGE  ·  TAB: AI  ·  P: PACE",
                   WIDTH // 2, 659, "tiny", (221, 200, 228), center=True)
        self._text(surface, "EXAM-BOARD QUESTIONS ARE SHARED PRACTICE, NOT OFFICIAL PAPERS",
                   WIDTH // 2, 677, "tiny", (221, 200, 228), center=True)
        if save_error:
            self._text(surface, "SAVE FAILED - CHECK PERMISSIONS", WIDTH // 2, 519,
                       "small", (255, 130, 135), center=True)

    def draw_countdown(self, surface: pygame.Surface, countdown: float) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((25, 15, 42, 183))
        surface.blit(overlay, (0, 0))
        current = str(math.ceil(countdown - 0.75)) if countdown > 0.75 else "DUEL!"
        self._text(surface, "GET READY", WIDTH // 2, 213, "popup", (255, 220, 155), center=True)
        large = self.fonts["winner"].render(current, True, (255, 242, 185))
        scaled = pygame.transform.smoothscale(large, (large.get_width() * 2, large.get_height() * 2))
        surface.blit(scaled, (WIDTH // 2 - scaled.get_width() // 2, 274))
        self._text(surface, "Neither wizard can attack until the countdown ends.",
                   WIDTH // 2, 409, "body", (239, 219, 244), center=True)
        self._text(surface, "CHOOSE AN ELEMENT   ·   ANSWER QUESTIONS   ·   CAST WITH ENTER",
                   WIDTH // 2, 457, "small", (255, 221, 166), center=True)
