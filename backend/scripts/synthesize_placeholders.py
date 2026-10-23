"""Write short placeholder tones. ElevenLabs replaces them when a key is set."""

import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "audio"
RATE = 22050


def tone(path: Path, frequencies: tuple[float, ...], seconds: float) -> None:
    count = int(RATE * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        frames = bytearray()
        for index in range(count):
            envelope = min(1.0, index / 180) * min(1.0, (count - index) / 500)
            sample = 0.0
            for frequency in frequencies:
                sample += math.sin(2 * math.pi * frequency * index / RATE)
            sample = max(-1, min(1, sample / len(frequencies) * envelope * 0.35))
            frames += struct.pack("<h", int(sample * 32767))
        handle.writeframes(frames)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    tone(ROOT / "sprout.wav", (520, 780), 0.35)
    tone(ROOT / "xp.wav", (660,), 0.22)
    tone(ROOT / "level.wav", (392, 523, 659), 0.7)
    tone(ROOT / "badge.wav", (880, 1174), 0.4)
    tone(ROOT / "bloom.wav", (494, 659), 0.55)
    tone(ROOT / "season.wav", (330, 440), 0.8)
    tone(ROOT / "journal.wav", (587,), 0.3)
    tone(ROOT / "rain.wav", (180, 240, 300), 1.4)
    print(f"wrote placeholder tones in {ROOT}")


if __name__ == "__main__":
    main()
