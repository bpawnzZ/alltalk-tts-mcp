import os
import sys
import json
import asyncio
import subprocess
import time
from typing import Any, Optional
from pathlib import Path
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

mcp = FastMCP("alltalk-tts")

ALLTALK_URL = os.environ.get("ALLTALK_URL", "http://localhost:7851")
USER_AGENT = "alltalk-mcp/1.0"


def play_audio_file(file_path: str) -> bool:
    """Play audio file using system audio player with proper environment.

    This function ensures the subprocess has access to the PulseAudio
    socket by setting the PULSE_SERVER environment variable.

    Args:
        file_path: Path to the audio file to play

    Returns:
        True if playback succeeded, False otherwise
    """
    # Copy current environment
    env = os.environ.copy()

    # Ensure PULSE_SERVER is set
    if "PULSE_SERVER" not in env:
        # Try common PulseAudio socket locations
        pulse_sockets = [
            "/run/user/1000/pulse/native",  # User session
            "/run/user/$(id -u)/pulse/native",  # Current user
            "/var/run/pulse/native",  # System-wide
        ]

        for socket in pulse_sockets:
            # Expand $(id -u) if present
            if "$(id -u)" in socket:
                try:
                    uid = subprocess.check_output(["id", "-u"], text=True).strip()
                    socket = socket.replace("$(id -u)", uid)
                except:
                    continue

            if os.path.exists(socket):
                env["PULSE_SERVER"] = f"unix:{socket}"
                break

    # Also ensure XDG_RUNTIME_DIR is set
    if "XDG_RUNTIME_DIR" not in env:
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"

    # Try different audio players in order of preference
    players = [
        ["paplay", file_path],  # PulseAudio
        ["aplay", "-q", file_path],  # ALSA
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path],  # FFmpeg
        ["mpv", "--no-video", "--really-quiet", file_path],  # MPV
        ["cvlc", "--play-and-exit", "--quiet", file_path],  # VLC
    ]

    for player_cmd in players:
        try:
            # Log what we're trying
            print(f"Attempting to play with: {player_cmd[0]}", file=sys.stderr)
            print(
                f"PULSE_SERVER: {env.get('PULSE_SERVER', 'Not set')}", file=sys.stderr
            )

            result = subprocess.run(
                player_cmd,
                check=True,
                timeout=30,
                capture_output=True,
                text=True,
                env=env,
            )
            print(f"Successfully played audio with {player_cmd[0]}", file=sys.stderr)
            return True
        except FileNotFoundError:
            print(f"Player not found: {player_cmd[0]}", file=sys.stderr)
            continue
        except subprocess.CalledProcessError as e:
            print(f"Player error with {player_cmd[0]}: {e.stderr}", file=sys.stderr)
            continue
        except subprocess.TimeoutExpired:
            print(f"Player timeout with {player_cmd[0]}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Unexpected error with {player_cmd[0]}: {e}", file=sys.stderr)
            continue

    print(f"All audio players failed. File is at: {file_path}", file=sys.stderr)
    print(f"You can play it manually with: paplay {file_path}", file=sys.stderr)
    return False


async def make_alltalk_request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
) -> dict[str, Any]:
    """Make a request to the AllTalk API with proper error handling."""
    url = f"{ALLTALK_URL}{endpoint}"
    headers = {"User-Agent": USER_AGENT}

    # Debug: log what we're sending
    print(f"DEBUG: Making {method} request to {url}", file=sys.stderr)
    if data:
        print(f"DEBUG: Data: {data}", file=sys.stderr)

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                if files:
                    response = await client.post(
                        url, data=data, files=files, headers=headers
                    )
                else:
                    # Explicitly set Content-Type for form data
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                    response = await client.post(url, data=data, headers=headers)

            print(f"DEBUG: Response status: {response.status_code}", file=sys.stderr)
            print(f"DEBUG: Response text: {response.text[:200]}...", file=sys.stderr)

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(
                f"DEBUG: HTTP error: {e.response.status_code} - {e.response.text}",
                file=sys.stderr,
            )
            return {
                "status": "error",
                "message": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            print(f"DEBUG: Exception: {e}", file=sys.stderr)
            return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_voices() -> str:
    """Get available TTS voices from AllTalk.

    Returns a list of all available voice files that can be used for TTS generation.
    """
    result = await make_alltalk_request("GET", "/api/voices")

    if result.get("status") == "success" and "voices" in result:
        voices = result["voices"]
        return f"Available TTS Voices ({len(voices)}):\n" + "\n".join(
            f"  - {v}" for v in voices
        )
    return f"Error fetching voices: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def list_rvc_voices() -> str:
    """Get available RVC (Realtime Voice Conversion) models from AllTalk.

    Returns a list of all available RVC voice models for voice conversion.
    """
    result = await make_alltalk_request("GET", "/api/rvcvoices")

    if result.get("status") == "success" and "rvcvoices" in result:
        voices = result["rvcvoices"]
        return f"Available RVC Voices ({len(voices)}):\n" + "\n".join(
            f"  - {v}" for v in voices
        )
    return f"Error fetching RVC voices: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def get_current_settings() -> str:
    """Get current AllTalk engine, model, and configuration settings.

    Returns detailed information about the currently loaded engine, available engines,
    models, DeepSpeed status, VRAM settings, and audio configuration.
    """
    result = await make_alltalk_request("GET", "/api/currentsettings")

    if result.get("status") == "success" or "engines_available" in result:
        lines = ["AllTalk Current Settings:"]

        engines = result.get("engines_available", [])
        lines.append(f"\nEngines Available: {', '.join(engines)}")
        lines.append(f"Current Engine: {result.get('current_engine_loaded', 'N/A')}")

        models = result.get("models_available", [])
        lines.append(f"\nModels Available ({len(models)}):")
        for m in models:
            model_name = m.get("name", str(m)) if isinstance(m, dict) else m
            lines.append(f"  - {model_name}")
        lines.append(f"Current Model: {result.get('current_model_loaded', 'N/A')}")

        lines.append(f"\nManufacturer: {result.get('manufacturer_name', 'N/A')}")
        lines.append(f"Audio Format: {result.get('audio_format', 'N/A')}")

        lines.append(
            f"\nDeepSpeed: enabled={result.get('deepspeed_enabled')}, available={result.get('deepspeed_available')}"
        )
        lines.append(
            f"Low VRAM: enabled={result.get('lowvram_enabled')}, capable={result.get('lowvram_capable')}"
        )

        lines.append(f"\nGeneration Speed: {result.get('generationspeed_set')}")
        lines.append(f"Temperature: {result.get('temperature_set')}")
        lines.append(f"Repetition Penalty: {result.get('repetitionpenalty_set')}")
        lines.append(f"Pitch: {result.get('pitch_set')}")

        lines.append(f"\nCapabilities:")
        lines.append(f"  Streaming: {result.get('streaming_capable')}")
        lines.append(f"  Multi-Voice: {result.get('multivoice_capable')}")
        lines.append(f"  Multi-Model: {result.get('multimodel_capable')}")

        return "\n".join(lines)
    return f"Error fetching settings: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def generate_tts(
    text_input: str,
    character_voice_gen: str = "female_01.wav",
    narrator_enabled: bool = False,
    narrator_voice_gen: str = "male_01.wav",
    text_not_inside: str = "silent",
    language: str = "auto",
    output_file_name: str = "",
    output_file_timestamp: bool = True,
    autoplay: bool = True,
    autoplay_volume: float = 1.0,
    rvccharacter_voice_gen: str = "",
    rvccharacter_pitch: int = 0,
    rvcnarrator_voice_gen: str = "",
    rvcnarrator_pitch: int = 0,
    text_filtering: str = "standard",
    speed: float = 1.0,
    pitch: int = 0,
    temperature: float = 0.8,
    repetition_penalty: float = 5.0,
) -> str:
    """Generate TTS audio using AllTalk with full parameter support.

    Primary TTS generation endpoint with support for character voices, narrator,
    RVC voice conversion, and all advanced parameters.

    Args:
        text_input: The text to synthesize (required)
        character_voice_gen: Voice file for character (e.g., "female_03.wav")
        narrator_enabled: Enable narrator mode
        narrator_voice_gen: Voice for narrator
        text_not_inside: How to handle non-dialogue ("character"/"narrator"/"silent")
        language: Language code or "auto"
        output_file_name: Custom output filename
        output_file_timestamp: Include timestamp in filename
        autoplay: Auto-play after generation
        autoplay_volume: Volume for autoplay (0.1-1.0)
        rvccharacter_voice_gen: RVC model for character voice
        rvccharacter_pitch: Pitch shift for RVC (-24 to 24)
        rvcnarrator_voice_gen: RVC model for narrator
        rvcnarrator_pitch: Pitch shift for narrator RVC
        text_filtering: Text filtering mode ("none"/"standard"/"html")
        speed: Speech speed (0.25-2.0)
        pitch: Voice pitch adjustment (-10 to 10)
        temperature: Sampling temperature (0.1-1.0)
        repetition_penalty: Repetition penalty (1.0-20.0)
    """
    narrator_val = "true" if narrator_enabled else "silent"
    if narrator_enabled and text_not_inside != "silent":
        narrator_val = "true"

    # Start with minimal required parameters
    data = {
        "text_input": text_input,
        "character_voice_gen": character_voice_gen,
        "autoplay": str(autoplay).lower(),
    }

    # Only add narrator parameters if narrator is enabled
    if narrator_enabled:
        data["narrator_enabled"] = narrator_val
        data["narrator_voice_gen"] = narrator_voice_gen
        data["text_not_inside"] = text_not_inside

    # Only add non-default parameters
    if language != "auto":
        data["language"] = language
    if output_file_name:
        data["output_file_name"] = output_file_name
    if not output_file_timestamp:  # Default is True, only send if False
        data["output_file_timestamp"] = "false"
    if autoplay_volume != 1.0:
        data["autoplay_volume"] = str(autoplay_volume)
    if text_filtering != "standard":
        data["text_filtering"] = text_filtering
    if speed != 1.0:
        data["speed"] = str(speed)
    if pitch != 0:
        data["pitch"] = str(pitch)
    if temperature != 0.8:
        data["temperature"] = str(temperature)
    if repetition_penalty != 5.0:
        data["repetition_penalty"] = str(repetition_penalty)

    # Always add cache busting
    data["cache_bust"] = str(int(time.time() * 1000))

    if rvccharacter_voice_gen:
        data["rvccharacter_voice_gen"] = rvccharacter_voice_gen
        # Only send pitch if it's not 0 (default)
        if rvccharacter_pitch != 0:
            data["rvccharacter_pitch"] = str(rvccharacter_pitch)

    if rvcnarrator_voice_gen:
        data["rvcnarrator_voice_gen"] = rvcnarrator_voice_gen
        # Only send pitch if it's not 0 (default)
        if rvcnarrator_pitch != 0:
            data["rvcnarrator_pitch"] = str(rvcnarrator_pitch)

    result = await make_alltalk_request("POST", "/api/tts-generate", data=data)

    if result.get("status") in ("success", "generate-success"):
        output = result.get("output_file_url", result.get("output_file", ""))
        output_path = result.get("output_file_path", "")

        if output_path and autoplay:
            if os.path.exists(output_path):
                play_audio_file(output_path)
            elif output:
                full_url = f"{ALLTALK_URL}{output}"
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        audio_data = await client.get(full_url)
                        if audio_data.status_code == 200:
                            import tempfile

                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as tmp:
                                tmp.write(audio_data.content)
                                tmp_path = tmp.name
                            play_audio_file(tmp_path)
                            os.unlink(tmp_path)
                except Exception:
                    pass

        return f"TTS Generated Successfully!\nOutput: {output}\nFile: {output_path}\n{ALLTALK_URL}{output}"
    return f"Error generating TTS: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def set_deepspeed(enabled: bool = True) -> str:
    """Enable or disable DeepSpeed optimization.

    DeepSpeed can significantly improve generation speed on compatible systems.

    Args:
        enabled: True to enable DeepSpeed, False to disable
    """
    value = "true" if enabled else "false"
    result = await make_alltalk_request(
        "POST", f"/api/deepspeed?new_deepspeed_value={value}"
    )

    status = "enabled" if enabled else "disabled"
    if result.get("status") == "success" or "message" in result:
        msg = result.get("message", f"DeepSpeed {status}")
        return f"DeepSpeed {status}!\n{msg}"
    return f"Error setting DeepSpeed: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def set_low_vram(enabled: bool = True) -> str:
    """Enable or disable Low VRAM mode.

    Low VRAM mode reduces memory usage at the cost of performance.
    Useful for systems with limited GPU memory.

    Args:
        enabled: True to enable Low VRAM, False to disable
    """
    value = "true" if enabled else "false"
    result = await make_alltalk_request(
        "POST", f"/api/lowvramsetting?new_lowvram_value={value}"
    )

    status = "enabled" if enabled else "disabled"
    if result.get("status") == "success" or "message" in result:
        msg = result.get("message", f"Low VRAM {status}")
        if "missing" not in msg.lower() and "required" not in msg.lower():
            return f"Low VRAM mode {status}!\n{msg}"
        return f"Low VRAM mode is already {status} (API returned: {msg})"
    return f"Error setting Low VRAM: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def switch_model(model_name: str) -> str:
    """Switch the AllTalk TTS model.

    Reloads AllTalk with a different model. Available models can be checked
    with get_current_settings.

    Args:
        model_name: The model to switch to (e.g., "xtts - xttsv2_2.0.3")
    """
    result = await make_alltalk_request("POST", f"/api/reload?model_name={model_name}")

    if result.get("status") == "success" or "message" in result:
        msg = result.get("message", "Model reloaded")
        return f"Model switch attempted to: {model_name}\n{msg}"
    return f"Error switching model: {result.get('message', 'Unknown error')}"


@mcp.tool()
async def quick_tts(
    text: str,
    voice: str = "female_01.wav",
    language: str = "auto",
    rvc_model: str = "",
    rvc_pitch: int = 0,
) -> str:
    """Quick TTS generation with minimal parameters.

    Convenience function for basic TTS generation without all the advanced options.
    Uses RVC voice conversion by default with the character RVC model.

    Args:
        text: Text to synthesize
        voice: Voice file to use
        language: Language code or "auto"
        rvc_model: RVC model for voice conversion
        rvc_pitch: Pitch adjustment for RVC
    """
    return await generate_tts(
        text_input=text,
        character_voice_gen=voice,
        language=language,
        rvccharacter_voice_gen=rvc_model,
        rvccharacter_pitch=rvc_pitch,
    )


@mcp.tool()
async def generate_with_rvc(
    text: str,
    voice: str = "female_01.wav",
    rvc_model: str = "",
    rvc_pitch: int = 0,
    language: str = "auto",
) -> str:
    """Generate TTS with RVC voice conversion.

    Synthesizes text and applies RVC voice conversion for more natural results.
    Defaults to no RVC model (empty string).

    Args:
        text: Text to synthesize
        voice: Base voice file
        rvc_model: RVC model to apply
        rvc_pitch: Pitch shift for RVC (-24 to 24)
        language: Language code or "auto"
    """
    return await generate_tts(
        text_input=text,
        character_voice_gen=voice,
        rvccharacter_voice_gen=rvc_model,
        rvccharacter_pitch=rvc_pitch,
        language=language,
    )


@mcp.tool()
async def generate_narrator(
    text: str,
    character_text: str,
    character_voice: str = "female_01.wav",
    narrator_voice: str = "male_01.wav",
    language: str = "auto",
) -> str:
    """Generate TTS with narrator mode.

    Synthesizes text with separate voices for character dialogue and narrator.

    Args:
        text: Full text with both narration and dialogue
        character_text: Portion to speak as character (used for detection)
        character_voice: Voice for character dialogue
        narrator_voice: Voice for narration
        language: Language code or "auto"
    """
    return await generate_tts(
        text_input=text,
        character_voice_gen=character_voice,
        narrator_enabled=True,
        narrator_voice_gen=narrator_voice,
        text_not_inside="narrator",
        language=language,
    )


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided MCP server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    import argparse

    parser = argparse.ArgumentParser(description="AllTalk TTS MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--alltalk-url",
        default=None,
        help="AllTalk server URL (default: http://localhost:7851)",
    )
    args = parser.parse_args()

    if args.alltalk_url:
        ALLTALK_URL = args.alltalk_url

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        starlette_app = create_starlette_app(mcp_server, debug=True)
        uvicorn.run(starlette_app, host=args.host, port=args.port)
