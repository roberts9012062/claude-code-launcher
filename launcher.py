"""
Claude Code Multi-Model Launcher - Windows Terminal Tabs
"""
import json
import os
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, Static
from textual.screen import ModalScreen

PROVIDERS = [
    {"name": "GLM", "base_url": "https://open.bigmodel.cn/api/anthropic", "model": "glm-4.6"},
    {"name": "MiniMax", "base_url": "https://api.minimaxi.com/anthropic", "model": "MiniMax-M2.5"},
    {"name": "DeepSeek", "base_url": "https://api.deepseek.com/anthropic", "model": "DeepSeek-V3.2-Exp"},
    {"name": "Kimi", "base_url": "https://api.moonshot.cn/anthropic", "model": "kimi-k2-turbo-preview"},
    {"name": "Qwen", "base_url": "https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy", "model": "qwen3-max"},
    {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
    {"name": "xAI Grok", "base_url": "https://api.x.ai/v1", "model": "grok-4.1"},
    {"name": "OpenRouter", "base_url": "https://openrouter.ai/api", "model": "anthropic/claude-sonnet-4.5"},
    {"name": "Custom", "base_url": "", "model": ""},
]

CONFIG_PATH = Path(__file__).parent / "models.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"models": []}


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def find_claude():
    for d in os.environ.get("PATH", "").split(";"):
        p = Path(d) / "claude.cmd"
        if p.exists():
            return str(p)
    return "claude"


def launch_in_wt(model):
    """Launch Claude Code in Windows Terminal tab"""
    settings_path = Path.home() / ".claude" / "settings.json"
    backup_path = Path.home() / ".claude" / "launcher_backup.json"

    # Backup and modify settings
    if settings_path.exists():
        try:
            import shutil
            shutil.copy(settings_path, backup_path)
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings.pop("env", None)
            settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # Create PowerShell command
    ps_script = f'''
$Host.UI.RawUI.WindowTitle = '{model["name"]} - Claude Code'
$env:ANTHROPIC_AUTH_TOKEN = '{model["api_key"]}'
$env:ANTHROPIC_BASE_URL = '{model["base_url"]}'
$env:ANTHROPIC_MODEL = '{model["model"]}'

& '{find_claude()}'

$bp = "$env:USERPROFILE\\.claude\\launcher_backup.json"
if (Test-Path $bp) {{ Copy-Item $bp "$env:USERPROFILE\\.claude\\settings.json" -Force; Remove-Item $bp -Force }}
'''

    # Write temp script
    import tempfile
    tmp = Path(tempfile.gettempdir()) / f"claude_launch_{os.getpid()}.ps1"
    tmp.write_text(ps_script, encoding="utf-8")

    # Launch in Windows Terminal new tab
    try:
        subprocess.Popen([
            "wt", "new-tab",
            "--title", f"{model['name']}",
            "powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", str(tmp)
        ])
        return True
    except FileNotFoundError:
        # Fallback: launch in separate PowerShell window
        subprocess.Popen([
            "powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", str(tmp)
        ], creationflags=subprocess.CREATE_NEW_CONSOLE)
        return True
    except Exception as e:
        return False


class EditScreen(ModalScreen):
    """Modal for adding/editing models"""

    CSS = """
    EditScreen { align: center middle; }
    .dlg { width: 50; border: thick $primary; background: $surface; padding: 1 2; }
    .ttl { text-align: center; text-style: bold; margin-bottom: 1; }
    .lbl { margin-top: 1; }
    .btns { margin-top: 1; height: 3; align: center middle; }
    Button { margin: 0 1; }
    """

    def __init__(self, model=None):
        super().__init__()
        self.model = model or {}

    def compose(self):
        yield Label("Add Model" if not self.model else "Edit Model", classes="ttl")
        yield Label("Provider:", classes="lbl")
        yield Select([(p["name"], p["name"]) for p in PROVIDERS],
                     value=self.model.get("provider", PROVIDERS[0]["name"]), id="prov")
        yield Label("Name:", classes="lbl")
        yield Input(value=self.model.get("name", ""), id="name")
        yield Label("API Key:", classes="lbl")
        yield Input(value=self.model.get("api_key", ""), id="key", password=True)
        yield Label("Base URL:", classes="lbl")
        yield Input(value=self.model.get("base_url", ""), id="url")
        yield Label("Model:", classes="lbl")
        yield Input(value=self.model.get("model", ""), id="model")
        with Horizontal(classes="btns"):
            yield Button("Save", variant="primary", id="save")
            yield Button("Cancel", id="cancel")

    def on_mount(self):
        self.query_one("#name").focus()

    def on_select_changed(self, e):
        if e.select.id == "prov":
            p = next((x for x in PROVIDERS if x["name"] == e.value), None)
            if p:
                self.query_one("#name").value = p["name"]
                self.query_one("#url").value = p["base_url"]
                self.query_one("#model").value = p["model"]

    def on_button_pressed(self, e):
        if e.button.id == "save":
            n = self.query_one("#name").value.strip()
            k = self.query_one("#key").value.strip()
            if n and k:
                self.dismiss({
                    "name": n,
                    "provider": self.query_one("#prov").value,
                    "api_key": k,
                    "base_url": self.query_one("#url").value.strip(),
                    "model": self.query_one("#model").value.strip(),
                })
            else:
                self.app.bell()
        else:
            self.dismiss(None)


class Launcher(App):
    """Main launcher application"""

    CSS = """
    Screen { background: $surface; }

    .header {
        height: 3;
        background: $primary;
        padding: 1 2;
        align: center middle;
    }

    .header Label {
        color: white;
        text-style: bold;
    }

    .list-container {
        height: 1fr;
        margin: 1 2;
        border: solid $primary;
    }

    ListView { height: 1fr; }

    ListItem { padding: 1 2; }
    ListItem:hover { background: $primary-darken-2; }
    ListItem.-active { background: $primary; color: white; }

    .buttons {
        height: 3;
        margin: 1 2;
        align: center middle;
    }

    Button { margin: 0 1; min-width: 10; }

    .status {
        text-align: center;
        color: $text-muted;
        margin: 1;
    }

    .info {
        text-align: center;
        color: $text-muted;
        margin: 1;
        height: 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("enter", "launch", "Launch"),
    ]

    def compose(self) -> ComposeResult:
        with Container(classes="header"):
            yield Label("Claude Code Multi-Model Launcher")
        with Container(classes="list-container"):
            yield ListView(id="model-list")
        with Horizontal(classes="buttons"):
            yield Button("Launch", variant="success", id="launch")
            yield Button("Add", variant="primary", id="add")
            yield Button("Edit", id="edit")
            yield Button("Delete", variant="error", id="delete")
            yield Button("Quit", id="quit")
        yield Label("Select model and press Enter or click Launch", classes="status", id="status")
        yield Label("Opens in Windows Terminal tabs - Ctrl+Shift+T for new tab", classes="info")

    def on_mount(self):
        self.load_models()
        self.query_one("#model-list").focus()

    def load_models(self):
        lst = self.query_one("#model-list")
        lst.clear()
        cfg = load_config()
        for m in cfg.get("models", []):
            item = ListItem(Static(f"[bold]{m['name']}[/] - {m['model']}"))
            item.model = m
            lst.append(item)
        if not cfg.get("models"):
            self.query_one("#status").update("No models. Press 'A' to add one.")

    def on_button_pressed(self, e):
        actions = {
            "launch": self.action_launch,
            "add": self.action_add,
            "edit": self.action_edit,
            "delete": self.action_delete,
            "quit": self.action_quit,
        }
        if e.button.id in actions:
            actions[e.button.id]()

    def on_list_view_selected(self, e):
        if e.list_view.id == "model-list":
            self.action_launch()

    def action_launch(self):
        lst = self.query_one("#model-list")
        if lst.highlighted_child and hasattr(lst.highlighted_child, "model"):
            model = lst.highlighted_child.model
            success = launch_in_wt(model)
            if success:
                self.query_one("#status").update(f"Launched: {model['name']}")
            else:
                self.query_one("#status").update(f"Failed to launch: {model['name']}")

    def action_add(self):
        def cb(r):
            if r:
                cfg = load_config()
                cfg["models"].append(r)
                save_config(cfg)
                self.load_models()
        self.push_screen(EditScreen(), cb)

    def action_edit(self):
        lst = self.query_one("#model-list")
        if lst.highlighted_child and hasattr(lst.highlighted_child, "model"):
            model = lst.highlighted_child.model
            cfg = load_config()
            idx = cfg["models"].index(model)

            def cb(r):
                if r:
                    cfg = load_config()
                    cfg["models"][idx] = r
                    save_config(cfg)
                    self.load_models()
            self.push_screen(EditScreen(model), cb)

    def action_delete(self):
        lst = self.query_one("#model-list")
        if lst.highlighted_child and hasattr(lst.highlighted_child, "model"):
            model = lst.highlighted_child.model
            cfg = load_config()
            cfg["models"] = [m for m in cfg["models"] if m != model]
            save_config(cfg)
            self.load_models()


if __name__ == "__main__":
    Launcher().run()
