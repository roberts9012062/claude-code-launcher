# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on code in this repository.

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

Single-file Textual application (`launcher.py`) with JSON config (`models.json`).

### Key Functions

| Function | Purpose |
|----------|---------|
| `launch_in_wt()` | Creates temp PowerShell script, sets env vars, spawns Claude Code via `wt new-tab` |
| `restore_settings()` | Restores `~/.claude/settings.json` from backup |
| `get_local_version()` / `get_latest_version()` | Version detection via `claude --version` and `npm view` |
| `update_claude_code()` | Runs `npm update -g @anthropic-ai/claude-code` |

### Launch Mechanism

1. Backs up `~/.claude/settings.json` to `~/.claude/launcher_backup.json`
2. Removes `env` section from settings to avoid conflicts
3. Creates temp PowerShell script with env vars: `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`
4. Launches via `wt new-tab` (Windows Terminal) or falls back to PowerShell
5. **Settings restoration is manual** (press `R` in UI) - allows multiple Claude instances with different configs

### Classes

- **`EditScreen`**: ModalScreen for add/edit model configurations
- **`Launcher`**: Main App class with keyboard bindings and action handlers

### Adding New Providers

Add to `PROVIDERS` list:
```python
{"name": "ProviderName", "base_url": "https://api.example.com/anthropic", "model": "model-id"}
```

## Key Patterns

- `ModalScreen.dismiss(data)` returns data to callback
- `ListItem` objects have `.model` attribute attached for data storage
- Threading used for async update operations with `call_from_thread()` for UI updates
- UTF-8 BOM prefix (`\xef\xbb\xbf`) required for PowerShell script encoding
