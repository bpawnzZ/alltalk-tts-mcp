# Configuration Guide

This document provides detailed configuration examples for different MCP clients.

## Environment Variables

### Required
- `ALLTALK_URL`: URL of your AllTalk TTS server (default: `http://localhost:7851`)

### Optional (for audio playback)
- `PULSE_SERVER`: PulseAudio socket path (e.g., `unix:/run/user/1000/pulse/native`)
- `XDG_RUNTIME_DIR`: XDG runtime directory (e.g., `/run/user/1000`)
- `USER`: Username for audio permissions
- `HOME`: Home directory path

## MCP Client Configurations

### 1. Claude Desktop (`~/.mcp.json`)

**Basic Configuration:**
```json
{
  "mcpServers": {
    "alltalk-tts": {
      "command": "/path/to/alltalk-mcp-server/.venv/bin/python",
      "args": ["/path/to/alltalk-mcp-server/server.py", "--transport", "stdio"],
      "env": {
        "ALLTALK_URL": "http://localhost:7851"
      }
    }
  }
}
```

**Advanced Configuration (with audio):**
```json
{
  "mcpServers": {
    "alltalk-tts": {
      "command": "/home/user/alltalk-tts-mcp/alltalk-mcp-server/.venv/bin/python",
      "args": [
        "/home/user/alltalk-tts-mcp/alltalk-mcp-server/server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "ALLTALK_URL": "http://192.168.1.100:7851",
        "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
        "XDG_RUNTIME_DIR": "/run/user/1000",
        "USER": "user",
        "HOME": "/home/user"
      }
    }
  }
}
```

### 2. OpenCode (`~/.config/opencode/opencode.json`)

**Basic Configuration:**
```json
{
  "mcp": {
    "alltalk-tts": {
      "type": "local",
      "command": [
        "/path/to/alltalk-mcp-server/.venv/bin/python",
        "/path/to/alltalk-mcp-server/server.py",
        "--transport",
        "stdio"
      ],
      "environment": {
        "ALLTALK_URL": "http://localhost:7851"
      },
      "enabled": true
    }
  }
}
```

**Advanced Configuration (with audio):**
```json
{
  "mcp": {
    "alltalk-tts": {
      "type": "local",
      "command": [
        "/home/user/alltalk-tts-mcp/alltalk-mcp-server/.venv/bin/python",
        "/home/user/alltalk-tts-mcp/alltalk-mcp-server/server.py",
        "--transport",
        "stdio"
      ],
      "environment": {
        "ALLTALK_URL": "http://192.168.1.100:7851",
        "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
        "XDG_RUNTIME_DIR": "/run/user/1000",
        "USER": "user",
        "HOME": "/home/user",
        "PATH": "/usr/bin:/bin:/usr/local/bin:/home/user/.local/bin"
      },
      "enabled": true
    }
  }
}
```

### 3. Cursor IDE

Create `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "alltalk-tts": {
      "command": "python",
      "args": [
        "/path/to/alltalk-mcp-server/server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "ALLTALK_URL": "http://localhost:7851"
      }
    }
  }
}
```

### 4. Windsurf IDE

Create `~/.windsurf/mcp.json`:
```json
{
  "mcpServers": {
    "alltalk-tts": {
      "command": "/path/to/alltalk-mcp-server/.venv/bin/python",
      "args": ["/path/to/alltalk-mcp-server/server.py"],
      "env": {
        "ALLTALK_URL": "http://localhost:7851"
      }
    }
  }
}
```

## Platform-Specific Configurations

### Linux (PulseAudio)
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851",
    "PULSE_SERVER": "unix:/run/user/$(id -u)/pulse/native",
    "XDG_RUNTIME_DIR": "/run/user/$(id -u)"
  }
}
```

### Linux (PipeWire)
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851",
    "PULSE_SERVER": "unix:/run/user/$(id -u)/pipewire-0",
    "XDG_RUNTIME_DIR": "/run/user/$(id -u)"
  }
}
```

### macOS
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851"
    // macOS uses Core Audio, no PulseAudio configuration needed
  }
}
```

### Windows
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851"
    // Windows uses Windows Audio, no additional configuration needed
  }
}
```

## Network Configurations

### Local Server
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851"
  }
}
```

### Remote Server (LAN)
```json
{
  "env": {
    "ALLTALK_URL": "http://192.168.1.100:7851"
  }
}
```

### Remote Server (Internet)
```json
{
  "env": {
    "ALLTALK_URL": "https://alltalk.example.com"
  }
}
```

## Testing Your Configuration

### 1. Test AllTalk Server
```bash
curl http://localhost:7851/api/voices
```

### 2. Test MCP Server Directly
```bash
cd /path/to/alltalk-mcp-server
python server.py --help
```

### 3. Test with Environment Variables
```bash
export ALLTALK_URL="http://localhost:7851"
export PULSE_SERVER="unix:/run/user/$(id -u)/pulse/native"
python server.py --transport stdio
```

### 4. Verify Audio System
```bash
# Check PulseAudio
pactl info

# Test audio playback
paplay /usr/share/sounds/freedesktop/stereo/audio-volume-change.oga
```

## Troubleshooting Configuration

### Common Issues

1. **"Command not found"**: Ensure Python virtual environment is activated
2. **"Connection refused"**: Check AllTalk server is running
3. **No audio playback**: Verify audio environment variables
4. **Permission denied**: Check file permissions and audio group membership
5. **Timeout errors**: Increase timeout in client configuration

### Debug Mode

Enable debug logging by adding to environment:
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851",
    "DEBUG": "1"
  }
}
```

### Path Resolution

Use absolute paths for reliability:
```json
{
  "command": "/home/user/alltalk-tts-mcp/alltalk-mcp-server/.venv/bin/python",
  "args": [
    "/home/user/alltalk-tts-mcp/alltalk-mcp-server/server.py",
    "--transport",
    "stdio"
  ]
}
```

## Security Considerations

1. **Local vs Remote**: For security, prefer local AllTalk servers
2. **Environment Variables**: Avoid storing sensitive data in config files
3. **File Permissions**: Restrict read access to configuration files
4. **Network Access**: Use firewalls to restrict access to AllTalk server

## Performance Tuning

### Timeout Settings
Some clients allow timeout configuration:
```json
{
  "timeout": 30000,
  "env": {
    "ALLTALK_URL": "http://localhost:7851"
  }
}
```

### Memory Limits
For systems with limited RAM:
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851",
    "LOW_VRAM": "true"
  }
}
```

### GPU Optimization
For better GPU performance:
```json
{
  "env": {
    "ALLTALK_URL": "http://localhost:7851",
    "DEEPSPEED": "true"
  }
}
```