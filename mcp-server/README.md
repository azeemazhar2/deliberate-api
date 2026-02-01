# Deliberate MCP Server

Use the Deliberate API as a tool in Claude Desktop or Claude Code.

## Installation

```bash
cd mcp-server
pip install -e .
```

## Add to Claude Desktop

Edit your Claude Desktop config file:

**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "deliberate": {
      "command": "python",
      "args": ["/path/to/deliberate-api/mcp-server/server.py"]
    }
  }
}
```

## Add to Claude Code

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "deliberate": {
      "command": "python",
      "args": ["/path/to/deliberate-api/mcp-server/server.py"]
    }
  }
}
```

## Usage

Once configured, you can ask Claude:

> "Use the deliberate tool to analyze: We should rewrite our backend in Rust"

Claude will call the API and return a structured verdict with agreements and divergences.
