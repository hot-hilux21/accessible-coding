"""Write the small interface sounds the app plays.

They are bundled, not downloaded, so a reader who works offline still hears
them. Each one is generated from a fading sine tone: a couple of thousand
samples, a few kilobytes on disk, quiet enough not to startle. Run this after
changing a tone and commit the result - the .wav files are the artifact, this
is only how they were made.

    python scripts/make_sounds.py
"""
import math
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path(__file__).resolve().parent.parent / 'src' / 'accessible_ide' / 'static' / 'audio'


def tone(freq, ms, volume=0.22, fade=0.5):
    """One sine tone, `ms` long, faded in and out over `fade` of its length.

    The fade is what stops the speaker making a click at each end: a tone that
    starts and stops at full amplitude is heard as a pop, not a note.
    """
    count = int(RATE * ms / 1000)
    samples = []
    for i in range(count):
        position = i / count
        if fade:
            edge = min(position, 1 - position) / fade
            envelope = max(0.0, min(1.0, edge))
        else:
            envelope = 1.0
        samples.append(volume * envelope * math.sin(2 * math.pi * freq * i / RATE))
    return samples


def glide(start, end, ms, volume=0.22):
    """One tone that slides from `start` to `end`, with the same fade."""
    count = int(RATE * ms / 1000)
    samples = []
    for i in range(count):
        position = i / count
        edge = min(position, 1 - position) / 0.5
        envelope = max(0.0, min(1.0, edge))
        freq = start + (end - start) * position
        samples.append(volume * envelope * math.sin(2 * math.pi * freq * i / RATE))
    return samples


def write(name, samples):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        frames = b''.join(
            struct.pack('<h', int(max(-1.0, min(1.0, sample)) * 32767))
            for sample in samples)
        handle.writeframes(frames)
    print('%-12s %5d bytes' % (name, path.stat().st_size))


if __name__ == '__main__':
    # A button being pressed: the shortest sound here, low enough to sit under
    # every other one and take no attention of its own.
    write('press.wav', tone(880, 45, volume=0.14, fade=0.6))
    # A run that finished cleanly: two notes going up.
    write('success.wav', tone(587, 70) + tone(880, 110))
    # A run that fell over: one low note, longer, so it reads as a stop rather
    # than a nudge.
    write('error.wav', tone(196, 200, volume=0.2))
    # The program is waiting on an answer: a short middle note, less final
    # than either result.
    write('pause.wav', glide(520, 660, 120, volume=0.18))
