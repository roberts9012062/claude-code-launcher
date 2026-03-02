"""
Claude Code Multi-Model Launcher - Windows Terminal Tabs
"""
import json
import os
import shutil
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
    """查找 Claude Code CLI，返回 (路径, 是否找到)"""
    for d in os.environ.get("PATH", "").split(";"):
        p = Path(d) / "claude.cmd"
        if p.exists():
            return str(p), True
    return "claude", False


def check_first_run():
    """检查是否首次运行（models.json 不存在）"""
    return not CONFIG_PATH.exists()


def restore_settings():
    """Restore settings.json from backup"""
    settings_path = Path.home() / ".claude" / "settings.json"
    backup_path = Path.home() / ".claude" / "launcher_backup.json"

    if backup_path.exists():
        try:
            shutil.copy(backup_path, settings_path)
            backup_path.unlink()
            return True
        except Exception:
            return False
    return None  # No backup exists


def launch_in_wt(model, skip_permissions=False):
    """Launch Claude Code in Windows Terminal tab"""
    settings_path = Path.home() / ".claude" / "settings.json"
    backup_path = Path.home() / ".claude" / "launcher_backup.json"

    # Backup and modify settings
    if settings_path.exists():
        try:
            shutil.copy(settings_path, backup_path)
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings.pop("env", None)
            settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # Build claude command
    claude_path, _ = find_claude()
    claude_cmd = f"'{claude_path}'"
    if skip_permissions:
        claude_cmd += " --dangerously-skip-permissions"

    # Create PowerShell command
    ps_script = f'''
$Host.UI.RawUI.WindowTitle = '{model["name"]} - Claude Code'
$env:ANTHROPIC_AUTH_TOKEN = '{model["api_key"]}'
$env:ANTHROPIC_BASE_URL = '{model["base_url"]}'
$env:ANTHROPIC_MODEL = '{model["model"]}'

& {claude_cmd}

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
        yield Label("添加模型" if not self.model else "编辑模型", classes="ttl")
        yield Label("供应商:", classes="lbl")
        yield Select([(p["name"], p["name"]) for p in PROVIDERS],
                     value=self.model.get("provider", PROVIDERS[0]["name"]), id="prov")
        yield Label("名称:", classes="lbl")
        yield Input(value=self.model.get("name", ""), id="name")
        yield Label("API Key:", classes="lbl")
        yield Input(value=self.model.get("api_key", ""), id="key", password=True)
        yield Label("Base URL:", classes="lbl")
        yield Input(value=self.model.get("base_url", ""), id="url")
        yield Label("模型:", classes="lbl")
        yield Input(value=self.model.get("model", ""), id="model")
        with Horizontal(classes="btns"):
            yield Button("保存", variant="primary", id="save")
            yield Button("取消", id="cancel")

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

    .toggle-btn.on { background: $success; }
    .toggle-btn.off { background: $warning; }

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
        ("q", "quit", "退出"),
        ("a", "add", "添加"),
        ("e", "edit", "编辑"),
        ("d", "delete", "删除"),
        ("enter", "launch", "启动"),
        ("s", "toggle_skip", "跳过权限"),
        ("r", "restore", "还原"),
    ]

    def __init__(self):
        super().__init__()
        self.skip_permissions = False

    def compose(self) -> ComposeResult:
        with Container(classes="header"):
            yield Label("Claude Code 多模型启动器")
        with Container(classes="list-container"):
            yield ListView(id="model-list")
        with Horizontal(classes="buttons"):
            yield Button("启动", variant="success", id="launch")
            yield Button("添加", variant="primary", id="add")
            yield Button("编辑", id="edit")
            yield Button("删除", variant="error", id="delete")
            yield Button("还原配置", id="restore")
            yield Button("跳过权限: 关", id="toggle-skip", classes="toggle-btn off")
            yield Button("退出", id="quit")
        yield Label("选择模型后按 Enter 或点击启动", classes="status", id="status")
        yield Label("↑↓ 选择模型 | 在 Windows Terminal 标签页中打开", classes="info")

    def on_mount(self):
        self.claude_path, self.claude_found = find_claude()
        self.is_first_run = check_first_run()
        self.load_models()
        self.check_environment()
        self.query_one("#model-list").focus()

    def check_environment(self):
        """检测环境并显示相应提示"""
        messages = []

        if not self.claude_found:
            messages.append("[bold red]⚠ 未检测到 Claude Code CLI[/]")
            messages.append("请先安装: npm install -g @anthropic-ai/claude-code")

        if self.is_first_run:
            messages.append("[bold yellow]🎉 欢迎首次使用！[/]")
            messages.append("按 'A' 添加你的第一个模型配置")

        if messages:
            self.query_one("#status").update("\n".join(messages))
        elif not load_config().get("models"):
            self.query_one("#status").update("暂无模型配置，按 'A' 添加")

    def load_models(self):
        lst = self.query_one("#model-list")
        lst.clear()
        cfg = load_config()
        for m in cfg.get("models", []):
            item = ListItem(Static(f"[bold]{m['name']}[/] - {m['model']}"))
            item.model = m
            lst.append(item)

    def on_button_pressed(self, e):
        actions = {
            "launch": self.action_launch,
            "add": self.action_add,
            "edit": self.action_edit,
            "delete": self.action_delete,
            "restore": self.action_restore,
            "toggle-skip": self.action_toggle_skip,
            "quit": self.action_quit,
        }
        if e.button.id in actions:
            actions[e.button.id]()

    def on_list_view_selected(self, e):
        if e.list_view.id == "model-list":
            self.action_launch()

    def action_launch(self):
        # 检查 Claude Code 是否安装
        if not self.claude_found:
            self.query_one("#status").update("[bold red]⚠ 请先安装 Claude Code CLI[/]\nnpm install -g @anthropic-ai/claude-code")
            self.app.bell()
            return

        lst = self.query_one("#model-list")
        if lst.highlighted_child and hasattr(lst.highlighted_child, "model"):
            model = lst.highlighted_child.model
            success = launch_in_wt(model, self.skip_permissions)
            if success:
                mode = " (跳过权限)" if self.skip_permissions else ""
                self.query_one("#status").update(f"已启动: {model['name']}{mode}")
            else:
                self.query_one("#status").update(f"启动失败: {model['name']}")

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

    def action_restore(self):
        """还原 settings.json 配置"""
        result = restore_settings()
        if result is True:
            self.query_one("#status").update("配置已还原")
        elif result is False:
            self.query_one("#status").update("还原失败")
        else:
            self.query_one("#status").update("未找到备份文件")

    def action_toggle_skip(self):
        """切换跳过权限模式"""
        self.skip_permissions = not self.skip_permissions
        btn = self.query_one("#toggle-skip")
        if self.skip_permissions:
            btn.label = "跳过权限: 开"
            btn.set_class(True, "on")
            btn.set_class(False, "off")
            self.query_one("#status").update("模式: 跳过权限验证")
        else:
            btn.label = "跳过权限: 关"
            btn.set_class(False, "on")
            btn.set_class(True, "off")
            self.query_one("#status").update("模式: 正常模式")


if __name__ == "__main__":
    Launcher().run()
