from array import array
import math

import pygame


class Audio:
    def __init__(self):
        self.sounds = {}
        mixer_info = pygame.mixer.get_init()
        if mixer_info is None:
            return
        rate, _, channels = mixer_info
        notes = {
            "cast": (380, 850, 0.13),
            "hit": (170, 60, 0.18),
            "ward": (390, 510, 0.23),
            "correct": (620, 960, 0.10),
            "wrong": (200, 110, 0.16),
            "finish": (490, 740, 0.34),
            "clash": (540, 180, 0.21),
            "level_up": (450, 1140, 0.42),
            "ultimate": (190, 1270, 0.42),
            "parry": (860, 320, 0.24),
        }
        for name, (start, end, duration) in notes.items():
            frames = max(1, int(rate * duration))
            samples = array("h")
            phase = 0.0
            for index in range(frames):
                progress = index / frames
                frequency = start + (end - start) * progress
                phase += 2 * math.pi * frequency / rate
                envelope = (1.0 - progress) ** 2
                value = int(4900 * envelope * math.sin(phase))
                for _ in range(channels):
                    samples.append(value)
            self.sounds[name] = pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()
