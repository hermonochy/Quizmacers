from dataclasses import dataclass


@dataclass(frozen=True)
class Viewport:
    virtual_width: int
    virtual_height: int
    window_width: int
    window_height: int

    @property
    def size(self) -> tuple[int, int]:
        scale = min(self.window_width / self.virtual_width, self.window_height / self.virtual_height)
        return (max(1, round(self.virtual_width * scale)),
                max(1, round(self.virtual_height * scale)))

    @property
    def origin(self) -> tuple[int, int]:
        width, height = self.size
        return ((self.window_width - width) // 2, (self.window_height - height) // 2)

    def to_virtual(self, point: tuple[int, int]) -> tuple[int, int] | None:
        ox, oy = self.origin
        width, height = self.size
        x, y = point
        if not (ox <= x < ox + width and oy <= y < oy + height):
            return None
        return (min(self.virtual_width - 1, (x - ox) * self.virtual_width // width),
                min(self.virtual_height - 1, (y - oy) * self.virtual_height // height))
