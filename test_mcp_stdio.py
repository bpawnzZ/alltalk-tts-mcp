#!/usr/bin/env python3
import subprocess
import time
import json
import sys


def test_mcp_stdio():
    """Test MCP server in stdio mode."""
    print("Starting MCP server in stdio mode...")

    # Start the MCP server as OpenCode would
    cmd = [
        "/home/insomnia/git/custom_tts_mcp_tool/alltalk-mcp-server/.venv/bin/python",
        "/home/insomnia/git/custom_tts_mcp_tool/alltalk-mcp-server/server.py",
        "--transport",
        "stdio",
    ]

    env = {
        **os.environ,
        "ALLTALK_URL": "http://lucabrasi.vahalla.local:7851",
        "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }

    try:
        # Start process
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
        )

        # Give it time to start
        time.sleep(1)

        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        print(f"Sending: {json.dumps(init_request)}")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read response
        line = proc.stdout.readline()
        print(f"Received: {line}")

        # Send tools/list request
        tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        print(f"\nSending: {json.dumps(tools_request)}")
        proc.stdin.write(json.dumps(tools_request) + "\n")
        proc.stdin.flush()

        # Read response
        line = proc.stdout.readline()
        print(f"Received: {line}")

        # Clean up
        proc.terminate()
        proc.wait(timeout=2)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import os

    test_mcp_stdio()
