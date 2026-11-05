from dataclasses import dataclass

from .config import Element


@dataclass(frozen=True)
class Spell:
    name: str
    power: int
    speed_bonus: int
    travel_speed: int
    color: tuple[int, int, int]
    radius: int
    trait: str
    heal: int = 0


SPELLBOOK = {
    Element.FIRE: (
        Spell("Fireball", 13, 9, 535, (255, 117, 65), 15, "burn"),
        Spell("Lightning Strike", 17, 11, 910, (255, 223, 90), 12, "lightning"),
        Spell("Lightning Storm", 23, 12, 785, (255, 195, 85), 19, "lightning"),
        Spell("Firestorm", 29, 14, 560, (255, 82, 71), 27, "burn"),
    ),
    Element.EARTH: (
        Spell("Stone Shot", 15, 8, 415, (197, 154, 91), 16, "shatter"),
        Spell("Boulder", 20, 9, 470, (184, 145, 87), 21, "shatter"),
        Spell("Earthquake", 26, 10, 590, (207, 169, 102), 22, "shatter"),
        Spell("Cataclysm", 33, 10, 520, (239, 181, 95), 29, "shatter"),
    ),
    Element.WATER: (
        Spell("Splash", 12, 9, 650, (78, 191, 239), 14, "soak"),
        Spell("Water Lance", 17, 11, 720, (88, 201, 248), 15, "soak"),
        Spell("Tidal Wave", 22, 12, 620, (70, 178, 238), 23, "soak"),
        Spell("Maelstrom", 28, 13, 640, (80, 219, 245), 26, "soak"),
    ),
    Element.AIR: (
        Spell("Gust", 12, 9, 860, (165, 236, 215), 13, "pierce"),
        Spell("Wind Blade", 16, 11, 920, (157, 249, 215), 15, "pierce"),
        Spell("Cyclone", 21, 12, 825, (126, 238, 200), 21, "pierce"),
        Spell("Tempest", 27, 13, 870, (193, 249, 209), 25, "pierce"),
    ),
    Element.SPIRIT: (
        Spell("Ward", 21, 11, 0, (178, 137, 255), 0, "shield"),
        Spell("Aegis", 28, 11, 0, (173, 151, 255), 0, "shield"),
        Spell("Soul Bloom", 30, 12, 0, (198, 160, 255), 0, "shield", 8),
        Spell("Astral Sanctuary", 38, 14, 0, (220, 175, 255), 0, "shield", 14),
    ),
}


ELEMENT_COLORS = {element: stages[0].color for element, stages in SPELLBOOK.items()}
ELEMENT_ORDER = tuple(Element)
COUNTERS = {
    Element.WATER: Element.FIRE,
    Element.FIRE: Element.EARTH,
    Element.EARTH: Element.AIR,
    Element.AIR: Element.WATER,
}


def spell_for(element: Element, level: int) -> Spell:
    return SPELLBOOK[element][min(4, max(1, level)) - 1]
