#!/usr/bin/env python3
import os
import json
import sys


def main():
    """Print environment variables to see what the MCP server sees."""
    env_info = {
        "PULSE_SERVER": os.environ.get("PULSE_SERVER"),
        "USER": os.environ.get("USER"),
        "UID": os.environ.get("UID"),
        "HOME": os.environ.get("HOME"),
        "PATH": os.environ.get("PATH"),
        "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR"),
        "PWD": os.environ.get("PWD"),
        "ALLTALK_URL": os.environ.get("ALLTALK_URL"),
    }

    # Print as JSON so MCP can read it
    print(json.dumps(env_info, indent=2))

    # Also check if we can access PulseAudio socket
    pulse_socket = os.environ.get("PULSE_SERVER", "").replace("unix:", "")
    if pulse_socket and os.path.exists(pulse_socket):
        print(f"\nPulseAudio socket exists: {pulse_socket}")
        print(f"Socket permissions: {oct(os.stat(pulse_socket).st_mode)}")
    else:
        print(f"\nPulseAudio socket not found or PULSE_SERVER not set")


if __name__ == "__main__":
    main()
