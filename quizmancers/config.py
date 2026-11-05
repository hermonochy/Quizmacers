from enum import Enum


WIDTH = 1180
HEIGHT = 720
FPS = 60
TITLE = "Quizmancers — Knowledge Arena v1.2"
MAX_HEALTH = 340
MAX_SHIELD = 72
QUESTION_SECONDS = 16.0
CHOICE_QUESTION_SECONDS = 23.0
ROUND_SECONDS = 210.0
PLAYER_X = 232
AI_X = 948
WIZARD_Y = 367
PROJECTILE_Y = 347


class Element(str, Enum):
    FIRE = "fire"
    EARTH = "earth"
    WATER = "water"
    AIR = "air"
    SPIRIT = "spirit"


ELEMENT_KEYS = {
    Element.FIRE: "Q",
    Element.EARTH: "W",
    Element.WATER: "E",
    Element.AIR: "R",
    Element.SPIRIT: "T",
}

BACKGROUND = (244, 222, 179)
INK = (35, 24, 59)
GOLD = (240, 185, 92)
PANEL = (39, 29, 67)
PANEL_ALT = (56, 40, 87)
LIGHT_TEXT = (255, 248, 234)
MUTED_TEXT = (194, 176, 213)
