#!/usr/bin/env python3
import sys
import os

# Test playsound library
print("Testing playsound library...")

try:
    from playsound import playsound

    print("✓ playsound imported successfully")

    # Create a simple test tone using sox if available
    test_file = "/tmp/test_tone.wav"

    # Try to create a test tone with sox
    import subprocess

    try:
        subprocess.run(
            ["sox", "-n", "-r", "44100", test_file, "synth", "0.5", "sin", "440"],
            check=True,
            capture_output=True,
        )
        print(f"✓ Created test tone: {test_file}")

        # Try to play it
        print("Attempting to play audio...")
        playsound(test_file, block=True)
        print("✓ Audio played successfully!")

        # Clean up
        os.unlink(test_file)

    except (FileNotFoundError, subprocess.CalledProcessError):
        print("✗ sox not available, trying with existing test file")
        # Try with an existing audio file
        import tempfile
        import wave
        import numpy as np

        # Create a simple sine wave
        sample_rate = 44100
        duration = 0.5
        frequency = 440.0

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.5 * np.sin(2 * np.pi * frequency * t)
        audio = (audio * 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            with wave.open(f.name, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio.tobytes())
            test_file = f.name

        print(f"✓ Created test tone: {test_file}")
        print("Attempting to play audio...")
        playsound(test_file, block=True)
        print("✓ Audio played successfully!")
        os.unlink(test_file)

except Exception as e:
    print(f"✗ Error with playsound: {e}")
    import traceback

    traceback.print_exc()
