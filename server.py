import os
import sys
import json
import asyncio
import subprocess
import time
import tempfile
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
    """Play audio file using system audio player."""
    import os
    import subprocess

    env = os.environ.copy()
    env.setdefault("PULSE_SERVER", "unix:/run/user/1000/pulse/native")
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
    env["PATH"] = "/usr/bin:/bin:" + env.get("PATH", "")

    for player in [
        "/usr/bin/ffplay",
        "/usr/bin/paplay",
        "/usr/bin/aplay",
        "/usr/bin/mpg123",
    ]:
        cmd = (
            [player, "-nodisp", "-autoexit", file_path]
            if "ffplay" in player
            else [player, file_path]
        )

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, timeout=30)
            if result.returncode == 0:
                return True
        except Exception:
            continue

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
    streaming: bool = False,
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
        streaming: Use streaming endpoint for real-time audio (no RVC/narrator support)
    """
    if streaming:
        return await stream_tts_v2(
            text=text_input,
            voice=character_voice_gen,
            language=language,
            autoplay=autoplay,
        )
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

        # Let AllTalk handle audio playback if autoplay=True
        # Removed local playback to prevent double playing

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


@mcp.tool()
async def stream_tts_v2(
    text: str,
    voice: str = "female_03.wav",
    language: str = "auto",
    output_file: str = "",
    autoplay: bool = True,
) -> str:
    """Stream TTS audio in real-time for immediate playback.

    This endpoint generates and streams TTS audio directly for real-time playback.
    It does not support narration or RVC voice conversion.

    Args:
        text: The text to convert to speech (required)
        voice: The voice type to use (e.g., "female_03.wav")
        language: Language code or "auto"
        output_file: Optional name for the output file
        autoplay: Auto-play the audio after generation

    Returns:
        Path to the generated audio file with playback instructions.
    """
    if not text.strip():
        return "Error: Text cannot be empty"

    output = output_file or f"stream_{int(time.time() * 1000)}.wav"

    url = f"{ALLTALK_URL}/api/tts-generate-streaming"
    params = {
        "text": text,
        "voice": voice,
        "language": language,
        "output_file": output,
    }

    # Use streaming to get chunks as they arrive
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        try:
            # Stream the response
            async with client.stream("GET", url, params=params) as response:
                content_type = response.headers.get("content-type", "")

                if content_type.startswith("audio"):
                    # Pipe audio directly to ffplay as chunks arrive
                    import subprocess

                    ffplay_proc = subprocess.Popen(
                        ["/usr/bin/ffplay", "-nodisp", "-autoexit", "-"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if chunk:
                            ffplay_proc.stdin.write(chunk)

                    ffplay_proc.stdin.close()
                    ffplay_proc.wait()

                    return (
                        f"Streaming TTS completed!\n"
                        f"Text: {text[:50]}...\n"
                        f"Played in real-time via streaming"
                    )
                else:
                    # Fallback: non-streaming response
                    result = await response.json()
                    if result.get("output_file_path"):
                        audio_url = f"{ALLTALK_URL}/audio/{result['output_file_path']}"
                        return f"Streaming ready! URL: {audio_url}"
                    return f"Error: {result}"

        except Exception as e:
            return f"Error: {str(e)}"


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
