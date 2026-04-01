# AllTalk TTS MCP Server

A Model Context Protocol (MCP) server for AllTalk TTS, providing full-featured text-to-speech with RVC voice conversion, narrator mode, and advanced audio generation capabilities.

## Features

- **Full AllTalk API Support**: All parameters from SillyTavern's AllTalk integration
- **RVC Voice Conversion**: Real-Time Voice Cloning with GPU acceleration
- **Narrator Mode**: Separate voices for character dialogue and narration
- **Multiple Output Formats**: WAV audio with configurable parameters
- **Performance Optimizations**: DeepSpeed and Low VRAM modes
- **Cross-platform Audio Playback**: Automatic audio playback after generation

## Prerequisites

1. **AllTalk TTS Server**: Running locally or remotely
   - Default: `http://localhost:7851`
   - [AllTalk GitHub](https://github.com/erew123/alltalk_tts)

2. **Python 3.8+** with virtual environment support
3. **Audio System**: PulseAudio, ALSA, or compatible audio backend

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/alltalk-tts-mcp.git
cd alltalk-tts-mcp
```

### 2. Set up Python environment

#### Option A: Using uv (recommended - faster)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or using pip: pip install uv

# Create virtual environment and install dependencies
uv sync
```

#### Option B: Using pip (traditional)
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file or set environment variables:
```bash
# Required: AllTalk server URL
export ALLTALK_URL="http://localhost:7851"

# Optional: Audio playback settings
export PULSE_SERVER="unix:/run/user/$(id -u)/pulse/native"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
```

## Configuration

### Claude Desktop (`~/.config/claude/desktop-config.json` or `~/.mcp.json`)
```json
{
  "mcpServers": {
    "alltalk-tts": {
      "command": "/path/to/alltalk-tts-mcp/.venv/bin/python",
      "args": ["/path/to/alltalk-tts-mcp/server.py", "--transport", "stdio"],
      "env": {
        "ALLTALK_URL": "http://localhost:7851",
        "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
        "XDG_RUNTIME_DIR": "/run/user/1000"
      }
    }
  }
}
```

### OpenCode (`~/.config/opencode/opencode.json`)
```json
{
  "mcp": {
    "alltalk-tts": {
      "type": "local",
      "command": [
        "/path/to/alltalk-tts-mcp/.venv/bin/python",
        "/path/to/alltalk-tts-mcp/server.py",
        "--transport",
        "stdio"
      ],
      "environment": {
        "ALLTALK_URL": "http://localhost:7851",
        "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
        "XDG_RUNTIME_DIR": "/run/user/1000"
      },
      "enabled": true
    }
  }
}
```

## Available Tools

### Core TTS Generation
- `generate_tts` - Full-featured TTS with all parameters
- `quick_tts` - Simplified TTS with RVC
- `generate_with_rvc` - TTS with RVC voice conversion
- `generate_narrator` - TTS with narrator mode

### Configuration & Information
- `list_voices` - List available TTS voices
- `list_rvc_voices` - List available RVC models
- `get_current_settings` - Get current AllTalk configuration
- `switch_model` - Switch TTS model
- `set_deepspeed` - Enable/disable DeepSpeed optimization
- `set_low_vram` - Enable/disable Low VRAM mode

## Usage Examples

### OpenCode Style
```bash
# List available voices
alltalk-tts_list_voices

# Generate TTS with RVC
alltalk-tts_generate_tts \
  --text_input "Hello, this is a test" \
  --character_voice_gen "female_01.wav" \
  --rvccharacter_voice_gen "" \
  --autoplay true

# Quick TTS generation
alltalk-tts_quick_tts \
  --text "Quick test" \
  --voice "male_01.wav" \
  --rvc_model "eminem/eminem-new-era-v2-48k.pth"
```

### Claude Code Style
```python
# Using the MCP tools in Claude
voices = alltalk_tts.list_voices()
print(voices)

# Generate TTS with specific parameters
result = alltalk_tts.generate_tts(
    text_input="Hello from Claude!",
    character_voice_gen="female_01.wav",
    narrator_enabled=True,
    narrator_voice_gen="male_01.wav",
    rvccharacter_voice_gen="",
    speed=1.2,
    pitch=2
)
print(f"Generated: {result}")
```

### Advanced Example: Narrator Mode
```python
result = alltalk_tts.generate_narrator(
    text="\"Hello,\" said the character. The narrator continued the story.",
    character_text="Hello,",
    character_voice="female_01.wav",
    narrator_voice="male_01.wav",
    language="auto"
)
```

## Parameters Reference

### `generate_tts` Parameters:
- `text_input` (required): Text to synthesize
- `character_voice_gen`: Voice file for character (default: "female_01.wav")
- `narrator_enabled`: Enable narrator mode (default: false)
- `narrator_voice_gen`: Voice for narrator (default: "male_01.wav")
- `rvccharacter_voice_gen`: RVC model for character voice (default: "")
- `rvccharacter_pitch`: Pitch shift for RVC (-24 to 24, default: 0)
- `language`: Language code or "auto" (default: "auto")
- `speed`: Speech speed (0.25-2.0, default: 1.0)
- `pitch`: Voice pitch adjustment (-10 to 10, default: 0)
- `temperature`: Sampling temperature (0.1-1.0, default: 0.8)
- `autoplay`: Auto-play after generation (default: true)

## Troubleshooting

### Audio Playback Issues
1. **No sound after generation**: Check audio system and permissions
   ```bash
   # Test audio system
   paplay --version
   # Check PulseAudio socket
   ls -la /run/user/$(id -u)/pulse/
   ```

2. **Permission errors**: Ensure user has access to audio system
   ```bash
   groups | grep audio
   sudo usermod -a -G audio $USER
   ```

### API Connection Issues
1. **AllTalk server not responding**: Verify server is running
   ```bash
   curl http://localhost:7851/api/voices
   ```

2. **GPU not utilized**: Check RVC parameters and GPU drivers
   ```bash
   nvidia-smi  # For NVIDIA GPUs
   ```

### MCP Integration Issues
1. **Tools not appearing**: Check MCP configuration file syntax
2. **Connection errors**: Verify Python path and virtual environment
3. **Timeout errors**: Increase timeout in MCP client configuration

## Development

### Custom Configuration

To create your own custom configuration:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bpawnzZ/alltalk-tts-mcp.git
   cd alltalk-tts-mcp
   ```

2. **Set up environment**:
   ```bash
   
   uv sync  # or use pip: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
   ```

3. **Configure for your system**:
   - Edit `server.py` to change default values (voice, RVC model, etc.)
   - Set environment variables for your AllTalk server URL
   - Update MCP client configuration with your specific paths

4. **Common customizations**:
   - Change `ALLTALK_URL` to your server address
   - Modify default voice in `server.py` parameters
   - Set your preferred RVC model
   - Adjust audio playback settings for your system

### Testing
```bash
# Test server directly

python server.py --help

# Test with stdio transport (for MCP clients)
python server.py --transport stdio

# Test with SSE transport (for HTTP clients)
python server.py --transport sse --host 0.0.0.0 --port 8080
```

### Adding New Features
1. Create feature branch from `main`
2. Implement changes in `server.py`
3. Update documentation
4. Test with both OpenCode and Claude Desktop
5. Merge to appropriate branch

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [AllTalk TTS](https://github.com/erew123/alltalk_tts) for the amazing TTS engine
- [Model Context Protocol](https://spec.modelcontextprotocol.io/) for the protocol specification
- Claude Desktop and OpenCode for MCP client implementations