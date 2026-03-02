# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Windows TUI launcher for Claude Code CLI that supports multiple AI providers. Built with Python's Textual framework, it allows users to configure and launch different AI models in Windows Terminal tabs.

## Commands

```bash
# Run the launcher
python launcher.py

# Or use the batch file (Windows)
启动器.bat

# Install the only dependency
pip install textual
```

## Architecture

### Main Components

- **`launcher.py`**: Single-file Textual TUI application containing:
  - `PROVIDERS` - List of pre-configured AI provider templates with base URLs and default models
  - `load_config()` / `save_config()` - JSON config file I/O
  - `launch_in_wt()` - Core launch logic that sets environment variables and spawns Claude Code
  - `EditScreen` - Modal dialog for adding/editing model configurations
  - `Launcher` - Main TUI application class

- **`models.json`**: User's model configurations (name, provider, api_key, base_url, model)

### Launch Mechanism

1. Backs up `~/.claude/settings.json` and removes `env` section to avoid conflicts
2. Creates a temporary PowerShell script that sets:
   - `ANTHROPIC_AUTH_TOKEN`
   - `ANTHROPIC_BASE_URL`
   - `ANTHROPIC_MODEL`
3. Launches Claude Code via `wt new-tab` (Windows Terminal) or falls back to PowerShell
4. Restores original settings when Claude Code exits

### Adding New Providers

Add entries to the `PROVIDERS` list in `launcher.py`:
```python
{"name": "ProviderName", "base_url": "https://api.example.com/anthropic", "model": "model-id"}
```

## Key Patterns

- Textual's `ModalScreen.dismiss()` for returning data from dialogs
- `ListView` with custom model data attached to `ListItem` objects
- JSON file for persistent configuration storage
