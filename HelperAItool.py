# Please install OpenAI SDK first: `pip3 install openai`
'''
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

print(response.choices[0].message.content)
'''

#!/usr/bin/env python3
"""
claw - 自然语言风格的电脑操控终端工具
支持文件管理、终端命令、技能录制与回放。
"""

import os
import shutil
import subprocess
import json
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.text import Text

console = Console()

SKILLS_FILE = Path.home() / ".claw_skills.json"

# ---------- 技能管理 ----------
def load_skills():
    if SKILLS_FILE.exists():
        with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_skills(skills):
    with open(SKILLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(skills, f, indent=2, ensure_ascii=False)

# ---------- 文件/系统操作 ----------
def cmd_list(path='.'):
    p = Path(path).expanduser()
    if not p.exists():
        console.print(f"[red]路径不存在: {p}[/red]")
        return
    if p.is_file():
        console.print(f"[cyan]{p}[/cyan]  (文件)")
        return
    table = Table(title=f"目录: {p}", header_style="bold blue")
    table.add_column("名称", style="cyan")
    table.add_column("类型", style="green")
    table.add_column("大小", style="yellow")
    for item in sorted(p.iterdir()):
        if item.is_dir():
            table.add_row(item.name, "文件夹", "-")
        else:
            size = item.stat().st_size
            table.add_row(item.name, "文件", f"{size} bytes")
    console.print(table)

def cmd_read(filepath):
    path = Path(filepath).expanduser()
    if not path.is_file():
        console.print(f"[red]文件不存在: {path}[/red]")
        return
    content = path.read_text(encoding='utf-8', errors='replace')
    # 根据扩展名尝试语法高亮
    ext = path.suffix.lstrip('.') or 'txt'
    syntax = Syntax(content, ext, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=str(path)))

def cmd_create(type_, name):
    path = Path(name).expanduser()
    if path.exists():
        console.print(f"[yellow]'{name}' 已存在，跳过创建。[/yellow]")
        return
    if type_ == 'file':
        path.touch()
        console.print(f"[green]已创建文件: {path}[/green]")
    elif type_ == 'dir':
        path.mkdir(parents=True)
        console.print(f"[green]已创建文件夹: {path}[/green]")
    else:
        console.print(f"[red]无效类型 '{type_}'，请输入 'file' 或 'dir'[/red]")

def cmd_delete(target):
    path = Path(target).expanduser()
    if not path.exists():
        console.print(f"[red]路径不存在: {path}[/red]")
        return
    if not Confirm.ask(f"确认删除 [bold red]{path}[/bold red]? (y/n)"):
        console.print("[yellow]已取消删除[/yellow]")
        return
    if path.is_file():
        path.unlink()
        console.print(f"[green]已删除文件: {path}[/green]")
    elif path.is_dir():
        shutil.rmtree(path)
        console.print(f"[green]已删除文件夹: {path}[/green]")

def cmd_write(filepath, content, mode='w'):
    path = Path(filepath).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding='utf-8') as f:
        f.write(content + '\n')
    action = "写入" if mode == 'w' else "追加"
    console.print(f"[green]已{action}文件: {path}[/green]")

def cmd_run(command):
    console.print(f"[bold]执行命令: {command}[/bold]")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.stdout:
            console.print(Text(result.stdout))
        if result.stderr:
            console.print(Text(result.stderr, style="red"))
        if result.returncode != 0:
            console.print(f"[red]命令退出码: {result.returncode}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]命令超时[/red]")
    except Exception as e:
        console.print(f"[red]执行失败: {e}[/red]")

# ---------- 命令解析 ----------
def parse_input(user_input):
    """简单解析：按空格分词，支持引号内参数字符串"""
    tokens = []
    current = ''
    in_quotes = False
    for ch in user_input:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ' ' and not in_quotes:
            if current:
                tokens.append(current)
                current = ''
        else:
            current += ch
    if current:
        tokens.append(current)
    return tokens

# ---------- 主循环 ----------
def main():
    skills = load_skills()
    console.print(Panel.fit(
        "[bold cyan]Claw[/bold cyan] - 电脑操控终端\n"
        "输入 [yellow]help[/yellow] 查看所有命令，[yellow]exit[/yellow] 退出",
        title="欢迎"
    ))

    recording = False
    skill_name = None
    skill_commands = []

    while True:
        try:
            # 根据状态显示不同提示符
            if recording:
                prompt_str = f"[bold magenta](录制技能 {skill_name})[/bold magenta] > "
            else:
                prompt_str = "[bold green]claw[/bold green] > "
            line = Prompt.ask(prompt_str)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]退出...[/yellow]")
            break

        if not line.strip():
            continue

        # 处理录制模式
        if recording:
            if line.strip().lower() == "skill end":
                # 保存技能
                skills[skill_name] = skill_commands.copy()
                save_skills(skills)
                console.print(f"[green]技能 '{skill_name}' 已保存，包含 {len(skill_commands)} 个命令。[/green]")
                recording = False
                skill_name = None
                skill_commands = []
            else:
                skill_commands.append(line.strip())
                console.print(f"[dim]已记录: {line.strip()}[/dim]")
            continue

        # 普通命令处理
        parts = parse_input(line.strip())
        if not parts:
            continue
        cmd = parts[0].lower()

        # 帮助
        if cmd == "help":
            help_text = """
[bold]可用命令:[/bold]
  read <文件>                    - 阅读文件内容
  create file <路径>             - 创建空文件
  create dir <路径>              - 创建文件夹
  delete <路径>                  - 删除文件或文件夹（需确认）
  write <文件> "内容"            - 写入文件（覆盖）
  append <文件> "内容"           - 追加内容到文件
  list [路径]                    - 列出目录内容（默认当前目录）
  run <系统命令>                 - 执行终端命令
  skill create <技能名>          - 开始录制技能
  skill end                      - 结束技能录制（录制过程中）
  skill run <技能名>             - 运行已保存的技能
  skill list                     - 列出所有技能
  skill delete <技能名>          - 删除指定技能
  exit                           - 退出
            """
            console.print(Panel(help_text.strip(), title="帮助"))
            continue

        # 退出
        if cmd == "exit":
            break

        # 读文件
        if cmd == "read" and len(parts) >= 2:
            cmd_read(parts[1])
            continue

        # 创建
        if cmd == "create" and len(parts) >= 3:
            type_ = parts[1]   # file 或 dir
            name = parts[2]
            cmd_create(type_, name)
            continue

        # 删除
        if cmd == "delete" and len(parts) >= 2:
            cmd_delete(parts[1])
            continue

        # 写入
        if cmd == "write" and len(parts) >= 3:
            filepath = parts[1]
            content = parts[2] if len(parts) >= 3 else ""
            cmd_write(filepath, content, mode='w')
            continue

        # 追加
        if cmd == "append" and len(parts) >= 3:
            filepath = parts[1]
            content = parts[2] if len(parts) >= 3 else ""
            cmd_write(filepath, content, mode='a')
            continue

        # 列出目录
        if cmd == "list":
            path = parts[1] if len(parts) >= 2 else "."
            cmd_list(path)
            continue

        # 执行系统命令
        if cmd == "run" and len(parts) >= 2:
            command_str = ' '.join(parts[1:])  # 保留原始命令，包括空格
            cmd_run(command_str)
            continue

        # 技能管理
        if cmd == "skill":
            if len(parts) < 2:
                console.print("[red]用法: skill <create|run|list|delete> [名称][/red]")
                continue
            subcmd = parts[1].lower()
            if subcmd == "create" and len(parts) >= 3:
                name = parts[2]
                if name in skills:
                    console.print(f"[yellow]技能 '{name}' 已存在，将覆盖[/yellow]")
                recording = True
                skill_name = name
                skill_commands = []
                console.print(f"[yellow]开始录制技能 '{name}'，输入命令后键入 'skill end' 结束录制。[/yellow]")
                continue
            elif subcmd == "run" and len(parts) >= 3:
                name = parts[2]
                if name not in skills:
                    console.print(f"[red]技能 '{name}' 不存在[/red]")
                    continue
                console.print(f"[cyan]正在执行技能: {name}[/cyan]")
                for skill_cmd in skills[name]:
                    console.print(f"[dim]执行: {skill_cmd}[/dim]")
                    # 递归调用主解析逻辑（简易版，直接重新解析）
                    # 注意：这里直接调用 parse_input 并将结果传给主处理会有些 hack，我们改用内联执行
                    skill_parts = parse_input(skill_cmd)
                    if not skill_parts:
                        continue
                    scmd = skill_parts[0].lower()
                    # 简化处理：只支持最常用命令，完整可重新设计调度器
                    if scmd == "read" and len(skill_parts) >= 2:
                        cmd_read(skill_parts[1])
                    elif scmd == "create" and len(skill_parts) >= 3:
                        cmd_create(skill_parts[1], skill_parts[2])
                    elif scmd == "delete" and len(skill_parts) >= 2:
                        cmd_delete(skill_parts[1])
                    elif scmd == "write" and len(skill_parts) >= 3:
                        cmd_write(skill_parts[1], skill_parts[2], mode='w')
                    elif scmd == "append" and len(skill_parts) >= 3:
                        cmd_write(skill_parts[1], skill_parts[2], mode='a')
                    elif scmd == "list":
                        path = skill_parts[1] if len(skill_parts) >= 2 else "."
                        cmd_list(path)
                    elif scmd == "run" and len(skill_parts) >= 2:
                        cmd_run(' '.join(skill_parts[1:]))
                    else:
                        console.print(f"[yellow]技能中包含不支持的命令: {skill_cmd}[/yellow]")
                console.print(f"[green]技能 '{name}' 执行完毕[/green]")
                continue
            elif subcmd == "list":
                if not skills:
                    console.print("[yellow]尚未保存任何技能[/yellow]")
                else:
                    table = Table(title="已保存的技能")
                    table.add_column("名称", style="cyan")
                    table.add_column("命令数", style="green")
                    for name, cmds in skills.items():
                        table.add_row(name, str(len(cmds)))
                    console.print(table)
                continue
            elif subcmd == "delete" and len(parts) >= 3:
                name = parts[2]
                if name in skills:
                    del skills[name]
                    save_skills(skills)
                    console.print(f"[green]已删除技能 '{name}'[/green]")
                else:
                    console.print(f"[red]技能 '{name}' 不存在[/red]")
                continue
            else:
                console.print("[red]无效的技能子命令[/red]")
                continue

        # 未知命令
        console.print(f"[red]未知命令: {line.strip()}[/red]")

if __name__ == "__main__":
    main()
