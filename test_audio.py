#!/usr/bin/env python3
import os
import subprocess
import tempfile
import wave
import numpy as np


def create_test_tone():
    """Create a simple test tone WAV file."""
    sample_rate = 44100
    duration = 2.0
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    audio = (audio * 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        with wave.open(f.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())
        return f.name


def play_audio_file(file_path: str) -> bool:
    """Play audio file using system default player."""
    players = [
        ["paplay", file_path],
        ["aplay", "-q", file_path],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path],
    ]

    for player_cmd in players:
        try:
            print(f"Trying: {' '.join(player_cmd)}")
            result = subprocess.run(
                player_cmd, check=True, timeout=30, capture_output=True
            )
            print(f"Success with {player_cmd[0]}")
            return True
        except (
            FileNotFoundError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as e:
            print(f"Failed with {player_cmd[0]}: {e}")
            continue

    return False


def test_audio_playback():
    """Test if audio playback works in current environment."""
    print("Testing audio playback...")
    print(f"PULSE_SERVER: {os.environ.get('PULSE_SERVER')}")
    print(f"USER: {os.environ.get('USER')}")
    print(f"UID: {os.environ.get('UID')}")

    # Create test tone
    test_file = create_test_tone()
    print(f"Created test file: {test_file}")

    # Try to play it
    success = play_audio_file(test_file)

    # Clean up
    os.unlink(test_file)

    return success


if __name__ == "__main__":
    if test_audio_playback():
        print("✓ Audio playback works!")
    else:
        print("✗ Audio playback failed")
