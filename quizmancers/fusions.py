from dataclasses import dataclass

from .config import Element


@dataclass(frozen=True)
class Fusion:
    name: str
    kind: str
    color: tuple[int, int, int]
    lifetime: float
    interval: float


FUSIONS = {
    frozenset((Element.FIRE, Element.AIR)): Fusion(
        "Flaming Tornado", "flame_tornado", (255, 142, 73), 2.3, 0.81
    ),
    frozenset((Element.FIRE, Element.WATER)): Fusion(
        "Chain Lightning", "chain_lightning", (255, 235, 132), 1.7, 0.72
    ),
    frozenset((Element.EARTH, Element.WATER)): Fusion(
        "Mudslide", "mudslide", (174, 137, 91), 2.3, 0.81
    ),
}

FUSION_KINDS = {fusion.kind: fusion for fusion in FUSIONS.values()}
FUSION_ELEMENTS = {
    "flame_tornado": Element.FIRE,
    "chain_lightning": Element.FIRE,
    "mudslide": Element.EARTH,
}
FUSION_WINDOW = 20.0
FUSION_COOLDOWN = 11.5


def fusion_for(first: Element | None, second: Element) -> Fusion | None:
    if first is None or first == second:
        return None
    return FUSIONS.get(frozenset((first, second)))


def potential_fusions(element: Element | None) -> tuple[tuple[Element, Fusion], ...]:
    if element is None:
        return ()
    options = []
    for pair, fusion in FUSIONS.items():
        if element in pair:
            for other in pair:
                if other != element:
                    options.append((other, fusion))
    return tuple(options)
