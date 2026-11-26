#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ai-collab bootstrap：一条命令把当前目录接入古珀协作区，零第三方依赖（Mac / Linux / Windows）。

谁来运行：仓库根的 setup.sh / setup.ps1（克隆插件仓库后调用）、ai-collab-setup / ai-collab-doctor skill。
放在 skill 目录而不是仓库根 scripts/：Claude Code 安装插件时只把 plugins/ai-collab 复制进插件缓存，仓库根的文件不在里面。
真正的接入逻辑在协作区的 skills/collab-setup/scripts/setup.py，本脚本只负责找到 / 克隆协作区、问人、调用它。

  1 检查环境   Python、git、项目目录（拒绝用户主目录）
  2 找协作区   项目里的子模块 packages/ai_collab → AI_COLLAB_HOME → 项目里的 .ai-collab → 项目上一级、上两级的
               ai_collab / ai-collab → ~/ai_collab、~/ai-collab → ~/code 等常见目录（setup.py 同一顺序）；
               找到就拉最新（子模块跟着项目走，不拉）；找不到就让人选放哪（默认 ~/ai_collab）、SSH 克隆，
               没权限时带着生成密钥、复制公钥、打开 codeup 设置页
  3 预览       setup.py --dry-run；认不出类型让人选，发现老项目手抄内容问要不要替换
  4 写入       确认后正式运行 setup.py（含环境变量 AI_COLLAB_HOME，以后各项目都按它找到同一份协作区）；
               装 skills（scripts/install-skills.mjs，要 Node 18+）：插件仓库的 skill，加上协作区 skills/ 下的
               （--source 协作区 --label ai_collab，跳过和插件重复的 collab-setup；这些也写 ~/.claude/skills）
  5 收尾       git user.name、钉钉 CLI dws 登录

用法：
  python3 bootstrap.py [项目路径] [--type pc|mobile|screen|backend|tester|product] [--migrate | --no-migrate]
                       [--yes] [--dry-run] [--clone-to <协作区位置>] [--name <钉钉姓名>] [--no-skills]
                       [--repo <协作区 git 地址>] [--no-env] [--non-interactive]
交互：从终端读输入（curl | bash 时 stdin 是管道，改读 /dev/tty）。没有终端（AI 工具里运行）时只做只读检查和预览，
      不写项目文件、不生成密钥、不改 git 配置，把要人决定的事和下一次该加的参数打印出来，退出码 2。
退出码：0 完成 / 1 出错 / 2 需要人决定。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

OK, INFO, WARN, FAIL = "[OK]  ", "[INFO]", "[WARN]", "[FAIL]"
EXIT_OK, EXIT_ERR, EXIT_ASK = 0, 1, 2
IS_WIN = os.name == "nt"
PY = "python" if IS_WIN else "python3"

COLLAB_REPO = "git@codeup.aliyun.com:gupo/middle-platform/official-website/ai_collab.git"
COLLAB_DIR_NAMES = ("ai_collab", "ai-collab")
ENV_NAME = "AI_COLLAB_HOME"
SSH_KEY_PAGE = "https://account-devops.aliyun.com/settings/ssh"
SSH_RETRIES = 3
RAW_BASE = "https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main"
MARKET_URL = "https://gitee.com/z-null/bmo-skills-plugin-demo.git"
SETUP_REL = Path("skills") / "collab-setup" / "scripts" / "setup.py"
FLOW_REL = Path("skills") / "contract-flow" / "scripts" / "flow.py"
SUBMODULE_REL = Path("packages") / "ai_collab"
SUBMODULE_SRC = "项目里的子模块 packages/ai_collab"
# 协作区 skills/ 装进各 AI 工具时的记录名和跳过列表（collab-setup 和插件的 ai-collab-setup 重复）
COLLAB_SKILLS_LABEL = "ai_collab"
COLLAB_SKILLS_SKIP = "collab-setup"
GUPO_SKILLS_CLONE = Path.home() / ".gupo" / "skills" / "bmo-skills-plugin-demo"

# 菜单顺序：最常见的「空文件夹当工作目录」放前面
TYPE_MENU = [
    ("product", "产品工作目录"), ("tester", "测试工作目录"), ("pc", "PC 前端"),
    ("mobile", "移动前端"), ("screen", "大屏前端"), ("backend", "后端"),
]
TYPES = [t for t, _ in TYPE_MENU]
# 这些环境变量说明是 AI 工具在跑命令：即使拿得到终端也不交互，免得卡住等输入
NAME_Q = "git 用户名（git config --global user.name）还没设置，你的钉钉姓名是？"
AI_ENV_VARS = ("CLAUDECODE", "AI_AGENT", "CURSOR_AGENT", "CODEX_SANDBOX", "GUPO_NONINTERACTIVE")


def out(tag, msg):
    print(f"{tag} {msg}", flush=True)


def step(n, title):
    print(f"\n== {n}/5 {title} ==", flush=True)


def indent(text, prefix="  "):
    for line in (text or "").rstrip("\n").splitlines():
        print(prefix + line, flush=True)


# --------------------------------------------------------------------------- 基础工具


def is_collab(p):
    """和 setup.py 的 is_collab 同一判定：目录里同时有 CHANGELOG.md 和 developers.json。"""
    try:
        return bool(p) and (Path(p) / "CHANGELOG.md").is_file() and (Path(p) / "developers.json").is_file()
    except OSError:
        return False


def real(p):
    return Path(os.path.realpath(str(p)))


def same_path(a, b):
    return os.path.normcase(str(real(a))) == os.path.normcase(str(real(b)))


def child_env(extra=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.update(extra or {})
    return env


def run(cmd, cwd=None, timeout=120, env=None):
    """运行并收集输出，返回 (退出码, stdout, stderr)。"""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, env=env or child_env(), stdin=subprocess.DEVNULL)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)


def run_stream(cmd, cwd=None, prefix="  ", keep=None):
    """边运行边缩进打印输出，返回退出码。keep(line) 返回 False 的行不打印。"""
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=child_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        out(FAIL, f"运行失败：{e}")
        return 127
    for line in p.stdout:
        line = line.rstrip("\n")
        if keep is None or keep(line):
            print(prefix + line, flush=True)
    return p.wait()


class AfterPreview:
    """正式运行 setup.py 时，预览里已经打印过的检查和改动明细不再重复，只打印写入结果和告警。"""

    def __init__(self):
        self.started = False

    def __call__(self, line):
        if line.startswith("== 改动 =="):
            self.started = True
            return False
        if "[FAIL]" in line:
            return True
        return self.started and not line.startswith(("[改动]", "        "))   # 8 个空格开头的是 diff 明细


def tilde(p):
    s, h = str(p), str(Path.home())
    return "~" + s[len(h):] if s == h or s.startswith(h + os.sep) else s


def quote(v):
    v = str(v)
    # 反斜杠不算安全字符：Git Bash 里重跑 curl | bash -s -- --clone-to C:\x\y 时，不加引号反斜杠会被 bash 吃掉
    if v and re.fullmatch(r"[\w@%+=:,./~-]+", v):
        return v
    return '"' + v.replace('"', '\\"') + '"'


# --------------------------------------------------------------------------- 交互


def win_console(f):
    """Windows：f 是不是真正的控制台输入（NUL、管道、文件都不算）。"""
    try:
        import ctypes
        import msvcrt
        handle = msvcrt.get_osfhandle(f.fileno())
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(ctypes.c_uint())))
    except (OSError, ValueError, AttributeError, ImportError):
        return False


class Term:
    """问人用的终端。ok=False 表示没有可用的终端（AI 工具里、或指定了 --non-interactive）。"""

    def __init__(self, disabled):
        self.fin = self.fout = None
        self.ok = False
        if disabled:
            return
        if IS_WIN:
            # Windows 没有可靠的 /dev/tty；irm | iex 在 PowerShell 里跑时 stdin 本来就是控制台。
            # 不能只看 isatty()：Git Bash 里 setup.sh 把 stdin 换成 /dev/null（即 NUL），NUL 是字符设备，
            # isatty() 也返回 True，一读就 EOF 直接「已取消」。要真的控制台（GetConsoleMode 成功）才算能问。
            if win_console(sys.stdin):
                self.fin, self.fout, self.ok = sys.stdin, sys.stdout, True
            return
        if sys.stdin.isatty():
            self.fin, self.fout, self.ok = sys.stdin, sys.stdout, True
            return
        try:     # curl | bash：stdin 是管道，直接读控制终端
            self.fin = open("/dev/tty", "r", encoding="utf-8", errors="replace")
            self.fout = open("/dev/tty", "w", encoding="utf-8", errors="replace")
            self.ok = True
        except OSError:
            self.fin = self.fout = None

    def ask(self, prompt, default=""):
        self.fout.write(prompt)
        self.fout.flush()
        line = self.fin.readline()
        if not line:
            raise EOFError
        return line.strip() or default

    def confirm(self, question, default=False):
        """回车取默认值；只认 y / n（及中文同义词），其他输入提示后重问，免得打错字被当成「否」。"""
        prompt = f"{question} {'[Y/n]' if default else '[y/N]'} "
        while True:
            ans = self.ask(prompt).strip().lower()
            if not ans:
                return default
            if ans in ("y", "yes", "是", "好", "确认", "对"):
                return True
            if ans in ("n", "no", "否", "不", "取消"):
                return False
            self.fout.write(f"  请输入 y 或 n（直接回车 = {'y' if default else 'n'}）\n")
            self.fout.flush()


class Pending:
    """要人决定的事：(问题, 说明里写的参数, 是否阻塞写入, 拼进重跑命令的参数)。"""

    def __init__(self):
        self.items = []

    def add(self, question, flag, blocking=True, cmd_flag=None):
        if all(it[0] != question for it in self.items):
            self.items.append((question, flag, blocking, flag if cmd_flag is None else cmd_flag))

    def blocking(self):
        return any(it[2] for it in self.items)

    def __bool__(self):
        return bool(self.items)


def next_command(args, extra_flags):
    """拼出「下一次这样运行」的命令：保留这次的参数，加上待定的参数。"""
    flags = []
    if args.project != ".":
        flags.append(quote(args.project))
    for name, val in (("--type", args.type), ("--clone-to", args.home), ("--name", args.name), ("--repo", args.repo)):
        if val and not any(f.startswith(name + " ") for f in extra_flags):
            flags.append(f"{name} {quote(val)}")
    for name, on in (("--migrate", args.migrate), ("--no-migrate", args.no_migrate), ("--no-skills", args.no_skills),
                     ("--no-env", args.no_env), ("--yes", args.yes)):
        if on and name not in extra_flags:
            flags.append(name)
    flags = [f for f in extra_flags if f] + flags
    tail = " ".join(flags)
    entry = os.environ.get("GUPO_SETUP_ENTRY")
    if entry == "sh":
        return f"curl -fsSL {RAW_BASE}/setup.sh | bash -s -- {tail}"
    if entry == "ps1":
        return f"& ([scriptblock]::Create((irm {RAW_BASE}/setup.ps1))) {tail}"
    return f"{PY} {quote(tilde(Path(__file__).resolve()))} {tail}"


def report_pending(pending, args, dry, wrote=False):
    print("\n== 需要你决定 ==", flush=True)
    flags = []
    for i, (q, flag, _, cmd_flag) in enumerate(pending.items, 1):
        print(f"  {i}. {q}" + (f"\n     → 加 {flag}" if flag else ""), flush=True)
        if cmd_flag:
            flags.append(cmd_flag)
    if dry:
        print("\n这是 --dry-run，什么都没写。正式接入时去掉 --dry-run，上面的事会在终端里问你。", flush=True)
        return
    head = "其他都已写好，只差上面这些。" if wrote else "还没写任何项目文件。"
    print(f"\n{head}决定好后在同一个目录重跑（把 <> 换成实际选择）：", flush=True)
    print("  " + next_command(args, flags), flush=True)
    print("（给 AI：把上面的问题一次问清用户，不要替用户选；用户回答后带上参数重跑。"
          "也可以请用户自己在终端运行入口命令，脚本会逐项询问。）", flush=True)


# --------------------------------------------------------------------------- 1. 环境、项目


def python_ok():
    v = sys.version_info
    out(OK if v >= (3, 8) else FAIL, f"Python {v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 8) else "，需要 3.8+"))
    return v >= (3, 8)


def git_ok():
    code, so, _ = run(["git", "--version"])
    if code == 0:
        out(OK, so)
        return True
    out(FAIL, "没有 git：Mac 运行 xcode-select --install，Windows 运行 winget install --id Git.Git -e，"
              "或到 https://git-scm.com/downloads 下载；装完重开终端再运行")
    return False


def project_root(path):
    code, so, _ = run(["git", "-C", str(path), "rev-parse", "--show-toplevel"])
    if code == 0 and so:
        return real(so), True
    return real(path), False


def looks_like_code(root):
    return any((root / f).exists() for f in ("package.json", "pom.xml", "build.gradle", "build.gradle.kts"))


# --------------------------------------------------------------------------- 2. 协作区


def common_bases():
    h = Path.home()
    bases = [h / n for n in ("code", "code-company", "projects", "workspace", "work", "dev", "src", "Documents/code")]
    if IS_WIN:
        for drive in "DEC":
            bases += [Path(f"{drive}:/") / n for n in ("code", "code-company", "projects", "workspace", "work")]
            bases.append(Path(f"{drive}:/"))
    return bases


def find_collab(root):
    """按顺序找协作区，返回 (路径, 来源)；找不到返回 (None, None)。和协作区 setup.py 的 find_collab 同一顺序。"""
    if is_collab(root / SUBMODULE_REL):
        return real(root / SUBMODULE_REL), SUBMODULE_SRC
    env = (os.environ.get(ENV_NAME) or "").strip()
    if env:
        p = Path(env).expanduser()
        if is_collab(p):
            return real(p), f"环境变量 {ENV_NAME}"
        out(WARN, f"{ENV_NAME}={env} 不是协作区（缺 CHANGELOG.md / developers.json），继续找")
    if is_collab(root / ".ai-collab"):
        return real(root / ".ai-collab"), "项目里的 .ai-collab 链接"
    places = [(root.parent, "项目上一级目录"), (root.parent.parent, "项目上两级目录"), (Path.home(), "个人目录")]
    places += [(b, "常见位置") for b in common_bases()]
    for base, label in places:
        for name in COLLAB_DIR_NAMES:
            if is_collab(base / name):
                return real(base / name), label
    return None, None


def pull_collab(collab):
    flow = collab / FLOW_REL
    if not (collab / ".git").exists():
        out(WARN, f"{collab} 不是 git 工作副本，没法拉最新")
        return
    cmd = [sys.executable, str(flow), "pull"] if flow.is_file() else ["git", "-C", str(collab), "pull", "--ff-only"]
    code, so, se = run(cmd, cwd=str(collab), timeout=300)
    indent((so + "\n" + se).strip())
    if code:
        out(WARN, "协作区没拉成最新（没网或有冲突），用现有版本继续")


def ssh_env(batch):
    extra = {"GIT_TERMINAL_PROMPT": "0"}
    if not os.environ.get("GIT_SSH_COMMAND"):
        # 第一次连 codeup 自动记下主机指纹（known_hosts），不弹 yes/no；没终端时不让 ssh 问口令
        extra["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=accept-new" + (" -o BatchMode=yes" if batch else "")
    return child_env(extra)


def classify_clone_error(err):
    if re.search(r"Permission denied \(publickey|publickey", err):
        return "publickey"
    if re.search(r"Host key verification failed|REMOTE HOST IDENTIFICATION HAS CHANGED", err):
        return "hostkey"
    if re.search(r"Could not resolve hostname|timed out|Network is unreachable|Connection refused|"
                 r"Connection reset|unable to access", err, re.I):
        return "network"
    return "other"


def find_pubkey():
    d = Path.home() / ".ssh"
    for name in ("id_ed25519", "id_rsa", "id_ecdsa"):
        if (d / f"{name}.pub").is_file() and (d / name).is_file():
            return d / f"{name}.pub"
    return None


def copy_clipboard(text):
    if sys.platform == "darwin":
        cands = [["pbcopy"]]
    elif IS_WIN:
        cands = [["clip"]]
    else:
        cands = [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["clip.exe"]]
    for c in cands:
        if shutil.which(c[0]):
            try:
                subprocess.run(c, input=text.encode("utf-8"), check=True, timeout=10,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except (OSError, subprocess.SubprocessError):
                continue
    return False


def open_url(url):
    try:
        if IS_WIN:
            os.startfile(url)  # noqa: S606 只打开固定的 codeup 设置页
            return True
        for c in (["open"] if sys.platform == "darwin" else ["xdg-open", "wslview"]):
            if shutil.which(c):
                subprocess.Popen([c, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
    except OSError:
        pass
    return False


def setup_ssh_key(term, args, pending, first):
    """clone 报 publickey 时：准备好公钥、复制、打开设置页。返回 retry / ask / err。"""
    pub = find_pubkey()
    if not term.ok and not args.yes:
        pending.add("codeup 还没有你的 SSH 公钥（克隆协作区报 Permission denied）。同意的话脚本会生成密钥"
                    "（已有就复用）、复制公钥、打开 codeup 设置页，你粘贴保存后再重跑", "--yes")
        return "ask"
    if pub is None:
        key = Path.home() / ".ssh" / "id_ed25519"
        if term.ok and not args.yes and not term.confirm(f"本机没有 SSH 密钥，生成一把到 {tilde(key)}？", True):
            out(FAIL, "没有 SSH 密钥克隆不了协作区。自己配好 codeup SSH 公钥后重跑")
            return "err"
        key.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _, email, _ = run(["git", "config", "--global", "user.email"])
        code, so, se = run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", email or "gupo-codeup", "-f", str(key)])
        if code or not key.with_suffix(".pub").is_file():
            out(FAIL, f"ssh-keygen 失败：{se or so}")
            return "err"
        out(OK, f"已生成 SSH 密钥 {tilde(key)}")
        pub = key.with_suffix(".pub")
    text = pub.read_text(encoding="utf-8", errors="replace").strip()
    print(f"\n  公钥（{tilde(pub)}）：\n  {text}\n", flush=True)
    if first:
        copied = copy_clipboard(text + "\n")
        out(OK if copied else WARN, "公钥已复制到剪贴板" if copied else "没能复制到剪贴板，请手动复制上面这一行")
        opened = open_url(SSH_KEY_PAGE)
        out(INFO, f"{'已打开' if opened else '请打开'} codeup SSH 公钥设置页：{SSH_KEY_PAGE}")
    out(INFO, "在页面上点「添加 SSH 公钥」，粘贴、保存。没有 ai_collab 仓库权限的，找研发负责人开通")
    if not term.ok:
        pending.add("在 codeup 设置页粘贴公钥并保存（上面已复制、已打开页面）", "")
        return "ask"
    ans = term.ask("贴好后按回车重试（输入 q 放弃）：")
    return "err" if ans.lower() == "q" else "retry"


def clone_collab(dest, repo, term, args, pending):
    """返回 ok / ask / err。"""
    first = True
    for attempt in range(SSH_RETRIES + 1):
        out(INFO, f"克隆协作区：git clone {repo} {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        code, so, se = run(["git", "clone", repo, str(dest)], timeout=900, env=ssh_env(batch=not term.ok))
        if code == 0 and is_collab(dest):
            out(OK, f"已克隆到 {dest}")
            return "ok"
        if code == 0:
            out(FAIL, f"克隆下来的 {dest} 不是协作区（缺 CHANGELOG.md / developers.json），检查 --repo 地址")
            return "err"
        err = se or so
        indent(err, "    | ")
        kind = classify_clone_error(err)
        if kind == "publickey":
            if attempt >= SSH_RETRIES:
                break
            r = setup_ssh_key(term, args, pending, first)
            first = False
            if r != "retry":
                return r
            continue
        if kind == "hostkey":
            out(FAIL, "codeup 的主机指纹和 known_hosts 里记的不一致。确认网络没问题后运行 "
                      "ssh-keygen -R codeup.aliyun.com 删掉旧记录，再重跑")
        elif kind == "network":
            out(FAIL, "连不上 codeup：检查网络 / 代理后重跑")
        else:
            out(FAIL, "克隆失败：多半是没有 ai_collab 仓库权限（找研发负责人在 codeup 上开通），或地址不对")
        return "err"
    out(FAIL, f"重试 {SSH_RETRIES} 次还是没有权限：确认公钥已保存到 codeup，且有 ai_collab 仓库权限（找研发负责人开通）")
    return "err"


def clone_choices(root):
    """找不到协作区时可选的位置：[(路径, 说明)]，第一个是默认。项目就在个人目录下一级时，「上一级」和第一个相同，不重复列。"""
    home_dest = Path.home() / COLLAB_DIR_NAMES[0]
    choices = [(home_dest, "推荐：固定放个人目录，以后所有项目共用")]
    parent_dest = root.parent / COLLAB_DIR_NAMES[0]
    if not same_path(parent_dest, home_dest):
        choices.append((parent_dest, "项目上一级目录"))
    return choices


def usable_dest(p):
    """能克隆过去（不存在 / 空目录）或本来就是协作区。"""
    try:
        return is_collab(p) or not p.exists() or (p.is_dir() and not any(p.iterdir()))
    except OSError:
        return False


def clone_question(root):
    lines = ["协作区放哪？（本机还没有协作区，选一个位置克隆过去）"]
    for i, (p, why) in enumerate(clone_choices(root), 1):
        lines.append(f"{i}) {tilde(p)}（{why}）→ --clone-to {quote(tilde(p))}")
    lines.append(f"{len(clone_choices(root)) + 1}) 自己指定路径 → --clone-to <路径>")
    return "\n     ".join(lines)


def ask_clone_dest(term, root):
    choices = clone_choices(root)
    custom = len(choices) + 1
    print("没找到协作区，要克隆到哪？", flush=True)
    for i, (p, why) in enumerate(choices, 1):
        label = tilde(p) if i == 1 else f"{why} {tilde(p)}"
        print(f"  {i}) {label}" + (f"（{why}）" if i == 1 else ""), flush=True)
    print(f"  {custom}) 自己输入路径", flush=True)
    while True:
        ans = term.ask(f"输入编号（直接回车 = 1）：", "1").strip()
        if ans.isdigit() and 1 <= int(ans) <= len(choices):
            p = choices[int(ans) - 1][0]
        elif ans == str(custom) or not ans.isdigit():
            typed = ans if not ans.isdigit() else term.ask("协作区放哪（完整路径）：").strip()
            if not typed:
                continue
            p = Path(typed).expanduser()
            p = p if p.is_absolute() else (Path.cwd() / p)
        else:
            print(f"  请输入 1–{custom}", flush=True)
            continue
        if usable_dest(p):
            return p
        print(f"  {p} 已存在且不是空目录，换一个位置", flush=True)


def locate_collab(root, args, term, pending, dry):
    """返回 (协作区, 是否已拉最新)；拿不到返回 (None, 退出码)。"""
    if args.home:
        dest = Path(args.home).expanduser()
        dest = dest if dest.is_absolute() else (Path.cwd() / dest)
        if is_collab(dest):
            out(OK, f"协作区：{real(dest)}（来源：--clone-to）")
            collab = real(dest)
            args.collab_source = SUBMODULE_SRC if same_path(dest, root / SUBMODULE_REL) else "--clone-to"
        elif dest.exists() and any(dest.iterdir()):
            out(FAIL, f"--clone-to 指向的 {dest} 不是协作区，也不是空目录，不动它")
            return None, EXIT_ERR
        else:
            collab = None
    else:
        collab, source = find_collab(root)
        if collab:
            out(OK, f"协作区：{collab}（来源：{source}）")
            args.collab_source = source
        dest = None
    if collab:
        if args.collab_source == SUBMODULE_SRC:
            # 子模块的版本跟着项目走（项目里提交的是子模块指针），这里不拉；setup.py 也带 --no-pull
            out(INFO, "子模块跟着项目的版本走，不在这里拉最新（要更新用 git submodule update --remote）")
            return collab, True
        if dry:
            out(INFO, "--dry-run：不拉取，预览时只比较和远端的差异")
            return collab, False
        pull_collab(collab)
        return collab, True

    default = clone_choices(root)[0][0]
    repo = args.repo or os.environ.get("AI_COLLAB_REPO") or COLLAB_REPO
    if dest is None:
        out(INFO, "没找到协作区（找过：项目里的子模块、环境变量 AI_COLLAB_HOME、项目里的 .ai-collab、"
                  "项目上一级 / 上两级目录、~/ai_collab、~/code 等常见位置）")
        if dry:
            pending.add(clone_question(root), "--clone-to <上面选的路径>", cmd_flag="--clone-to <路径>")
            return None, EXIT_ASK
        if term.ok:
            dest = ask_clone_dest(term, root)
        elif args.yes:
            if not usable_dest(default):
                out(FAIL, f"默认位置 {default} 已存在且不是协作区，也不是空目录，不动它。用 --clone-to <路径> 指定别的位置")
                return None, EXIT_ERR
            dest = default
            out(INFO, f"--yes：克隆到默认位置 {tilde(default)}")
        else:
            pending.add(clone_question(root), "--clone-to <上面选的路径>", cmd_flag="--clone-to <路径>")
            if not looks_like_code(root) and not args.type:
                pending.add("这个目录是哪类？" + " / ".join(f"{label}（{t}）" for t, label in TYPE_MENU),
                            "--type <类型>")
            pending.add("克隆好后会预览改动，确认写入", "--yes")
            return None, EXIT_ASK
    if dry:
        out(INFO, f"--dry-run：将克隆到 {dest}")
        return None, EXIT_ASK
    r = clone_collab(dest, repo, term, args, pending)
    if r == "ok":
        args.collab_source = "新克隆"
        return real(dest), True
    return None, (EXIT_ASK if r == "ask" else EXIT_ERR)


# --------------------------------------------------------------------------- 3. 预览


def setup_cmd(collab, root, args, ptype, migrate, dry, pulled):
    cmd = [sys.executable, str(collab / SETUP_REL), str(root), "--home", str(collab)]
    if dry:
        cmd.append("--dry-run")
    if ptype:
        cmd += ["--type", ptype]
    if migrate:
        cmd.append("--migrate")
    if args.no_env:
        cmd.append("--no-env")
    if pulled:
        cmd.append("--no-pull")
    return cmd


def choose_type(term):
    print("这个目录是做什么用的？", flush=True)
    for i, (t, label) in enumerate(TYPE_MENU, 1):
        print(f"  {i}) {label}（{t}）", flush=True)
    while True:
        ans = term.ask("输入编号：").strip().lower()
        if ans.isdigit() and 1 <= int(ans) <= len(TYPE_MENU):
            return TYPE_MENU[int(ans) - 1][0]
        if ans in TYPES:
            return ans
        print(f"  请输入 1–{len(TYPE_MENU)}", flush=True)


def plugin_repo_root():
    """插件仓库根（有 scripts/install-skills.mjs 的那一级）；在 Claude Code 插件缓存里运行时没有，返回 None。"""
    for p in Path(__file__).resolve().parents:
        if (p / "scripts" / "install-skills.mjs").is_file() and (p / ".claude-plugin" / "marketplace.json").is_file():
            return p
    return None


def node_cmd():
    node = shutil.which("node")
    if not node:
        return None
    code, so, _ = run([node, "--version"])
    m = re.match(r"v(\d+)", so or "")
    return node if code == 0 and m and int(m.group(1)) >= 18 else None


def uses_claude_code():
    """本机用 Claude Code：有 claude 命令，或有 Claude Code 自己才会建的东西。
    不看 ~/.claude 目录本身：别的工具（如钉钉 CLI 装 skill）也会建它，不能当作装了 Claude Code 的依据。"""
    h = Path.home()
    return bool(shutil.which("claude")) or (h / ".claude.json").is_file() \
        or (h / ".claude" / "plugins").is_dir() or (h / ".claude" / "projects").is_dir()


def claude_needs_plugin():
    """用 Claude Code 且还没装 ai-collab 插件。"""
    if not uses_claude_code():
        return False
    f = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        return "ai-collab@gupo-bmo" not in f.read_text(encoding="utf-8")
    except OSError:
        return True


def collab_skills_source(args, collab):
    """协作区 skills 链接指向哪份协作区。子模块跟着项目版本走，不能给全机用：改用环境变量指的那份，没有就不装。"""
    if args.collab_source != SUBMODULE_SRC:
        return collab
    env = (os.environ.get(ENV_NAME) or "").strip()
    if env and is_collab(Path(env).expanduser()):
        return real(Path(env).expanduser())
    out(INFO, "协作区是本项目的子模块（只给本项目用），协作区的 skill 不装进各 AI 工具；"
              "本机另有协作区（环境变量 AI_COLLAB_HOME）时会装那一份")
    return None


def skills_preview(args, collab):
    """预览要装的 skills，返回 [(名称, 命令, 是否有改动, 写入的目录)]。
    两个来源：插件仓库自己的 skill、协作区 skills/ 下的（install-skills.mjs --source，逻辑只在那一个脚本里）。"""
    if args.no_skills:
        out(INFO, "--no-skills：不装 skills")
        return []
    repo = plugin_repo_root()
    mjs = repo / "scripts" / "install-skills.mjs" if repo else GUPO_SKILLS_CLONE / "scripts" / "install-skills.mjs"
    jobs = []
    if repo is None:
        out(INFO, "在 Claude Code 插件里运行：插件仓库的 skill 由插件提供，不另外安装")
    node = node_cmd()
    if not node:
        out(INFO, "没有 Node 18+，跳过安装 skills（含协作区的设计规范、PPT 等 skill；不影响接入和使用协作区，"
                  "AI 仍能经 AGENTS.md 读到规则；装了 Node 后重跑即可）")
        return []
    if repo is not None:
        jobs.append(("插件", [node, str(mjs), "install"]))
    src = collab_skills_source(args, collab)
    if src is not None:
        if mjs.is_file():
            jobs.append(("协作区", [node, str(mjs), "install", "--source", str(src), "--label", COLLAB_SKILLS_LABEL,
                                   "--skip", COLLAB_SKILLS_SKIP]))
        else:
            out(INFO, f"协作区的 skill 没装：本机没有插件仓库（{tilde(GUPO_SKILLS_CLONE)}）。"
                      "在终端跑一次一条命令接入（README「快速开始」）会顺带装上")
    res = []
    for name, cmd in jobs:
        code, so, se = run(cmd + ["--dry-run"])
        if code:
            out(WARN, f"{name}的 skills 预览失败，跳过：" + ((se or so).splitlines() or [""])[-1])
            continue
        dirs = ""
        for line in so.splitlines():
            if line.startswith("写入："):
                dirs = line[len("写入："):].strip()
            if line.startswith(("skill：", "跳过：", "写入：", "预计改动", "已是最新")) or "⚠️" in line:
                print(f"  {name} skills {line.strip()}", flush=True)
        res.append((name, cmd, "已是最新" not in so, dirs))
    return res


def change_summary(text, root, skills_jobs):
    """要写的东西一句话列全（和预览里的「改动」一致）：项目文件、本机配置（环境变量、~/.claude/settings.json）、skills 目录。"""
    items = []
    home = str(Path.home())
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln.startswith("[改动]"):
            continue
        head, _, note = ln[len("[改动]"):].strip().partition("：")
        head = head.replace(str(root) + os.sep, "").replace(home, "~")
        note = re.sub(r"^新建，", "", note.split("；")[0])
        items.append(f"{head}（{note}）" if note else head)
    if not items and "认不出项目类型" in text:   # 还没选类型，预览没走到改动那一步：按惯例列
        items = ["项目里的 AGENTS.md、.gitignore、.ai-collab 链接", f"本机环境变量 {ENV_NAME}"]
        if (Path.home() / ".claude").is_dir():
            items.append("~/.claude/settings.json（放行协作区目录）")
    for name, _, changed, dirs in skills_jobs:
        if changed:
            items.append(f"{name}的 skills 链接（{dirs or '~/.agents/skills 等'}）")
    return items


def identity_set(collab):
    if (os.environ.get("AI_COLLAB_DEVELOPER") or "").strip():
        return "环境变量 AI_COLLAB_DEVELOPER"
    whoami = collab / ".ai-whoami" if collab else None
    if whoami and whoami.is_file() and whoami.read_text(encoding="utf-8", errors="replace").strip():
        return f"{whoami}"
    _, name, _ = run(["git", "config", "--global", "user.name"])
    return f"git user.name={name}" if name else ""


# --------------------------------------------------------------------------- 5. 收尾


def dws_logged_in():
    code, so, se = run(["dws", "auth", "status", "--format", "json"], timeout=30)
    txt = so + se
    return bool(re.search(r'"authenticated"\s*:\s*true', txt) and re.search(r'"token_valid"\s*:\s*true', txt))


def check_dws(term, args):
    """钉钉 CLI 登录检查。登录有效期约一个月，过期很常见：交互终端里直接问要不要现在登录（会打开浏览器扫码），
    AI 工具里没法扫码，只提示用户自己在终端运行。测试、产品不发钉钉的可以跳过。"""
    dws = shutil.which("dws")
    if not dws:
        out(INFO, "没有钉钉 CLI dws：不影响接入；要发钉钉通知的（前端、后端、测试）按协作区 MIGRATION.md 安装后运行 dws auth login")
        return
    if dws_logged_in():
        out(OK, "钉钉 CLI dws 已登录")
        return
    out(WARN, "钉钉 CLI dws 未登录或登录过期（有效期约一个月）：不影响接入，只是发不了钉钉通知")
    if not term.ok or args.yes:
        out(INFO, "要发钉钉通知的（前端、后端、测试），在自己的终端运行 dws auth login 扫码登录（AI 工具里没法扫码）")
        return
    if not term.confirm("现在登录钉钉吗？会打开浏览器扫码（测试、产品不发钉钉的可以选 n）", True):
        out(INFO, "跳过；以后要发钉钉时运行 dws auth login")
        return
    try:
        subprocess.run([dws, "auth", "login"], stdin=term.fin, stdout=term.fout, stderr=term.fout)
    except (OSError, KeyboardInterrupt) as e:
        out(WARN, f"登录没完成（{e}）：稍后在终端运行 dws auth login")
        return
    if dws_logged_in():
        out(OK, "钉钉 CLI dws 已登录")
    else:
        out(WARN, "还是没登录上：稍后在终端运行 dws auth login，再 dws auth status 看看")


# --------------------------------------------------------------------------- 主流程


def parse_args():
    ap = argparse.ArgumentParser(description="一条命令把当前目录接入古珀协作区")
    ap.add_argument("project", nargs="?", default=".", help="项目路径，默认当前目录")
    ap.add_argument("--type", choices=TYPES, help="目录类型（认不出或测试 / 产品工作目录时）")
    ap.add_argument("--migrate", action="store_true", help="把老项目照旧模板手抄的协作内容替换成区块")
    ap.add_argument("--no-migrate", action="store_true", help="保留老内容，不替换")
    ap.add_argument("-y", "--yes", action="store_true", help="跳过「确认写入」；没终端时也允许生成 SSH 密钥")
    ap.add_argument("--dry-run", action="store_true", help="只检查和预览，不写任何文件、不克隆、不问问题")
    ap.add_argument("--clone-to", "--home", dest="home", metavar="路径", help="协作区位置：已有就用，没有就克隆到这里")
    ap.add_argument("--name", help="git user.name 没设置时写入的姓名（钉钉姓名）")
    ap.add_argument("--no-skills", action="store_true", help="不装 skills")
    ap.add_argument("--repo", help=f"协作区 git 地址（默认 {COLLAB_REPO}，也可用环境变量 AI_COLLAB_REPO）")
    ap.add_argument("--no-env", action="store_true", help=f"不写环境变量 {ENV_NAME}")
    ap.add_argument("--non-interactive", action="store_true", help="不问问题（等同没有终端）")
    args = ap.parse_args()
    if args.migrate and args.no_migrate:
        ap.error("--migrate 和 --no-migrate 只能选一个")
    args.collab_source = None   # 找到协作区的来源（locate_collab 填）
    return args


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    args = parse_args()
    dry = args.dry_run
    ai = [v for v in AI_ENV_VARS if os.environ.get(v)]
    term = Term(disabled=args.non_interactive or bool(ai) or dry)
    pending = Pending()

    print("古珀协作区接入", flush=True)
    if dry:
        print("（--dry-run：只检查和预览，不写文件、不克隆、不提问）", flush=True)
    elif not term.ok:
        if ai:
            why = f"检测到 AI 工具（{ai[0]}）"
        elif IS_WIN and os.environ.get("GUPO_SETUP_ENTRY") == "sh":
            why = "Git Bash 里没法直接提问（想逐项回答，改在 PowerShell 里运行 setup.ps1 那条命令）"
        else:
            why = "没有可用的终端"
        if args.yes:
            print(f"（{why}，已带 --yes：不再逐项确认；还缺的决定会列在最后）", flush=True)
        else:
            print(f"（{why}：只做检查和预览，要人决定的事列在最后，带上参数重跑才会写入）", flush=True)

    # 1 ---------------------------------------------------------------
    step(1, "检查环境")
    if not (python_ok() and git_ok()):
        return EXIT_ERR
    target = Path(args.project).expanduser()
    if not target.is_dir():
        out(FAIL, f"项目路径不存在：{target}")
        return EXIT_ERR
    root, is_git = project_root(target)
    if same_path(root, Path.home()) or root.parent == root:
        out(FAIL, f"不要把 {root} 当项目目录。测试、产品同学新建一个空文件夹（例如 ~/ai-work），进去再运行")
        return EXIT_ERR
    out(INFO, f"项目：{root}{'' if is_git else '（不是 git 仓库）'}")

    # 2 ---------------------------------------------------------------
    step(2, "找协作区")
    collab, pulled = locate_collab(root, args, term, pending, dry)
    if collab is None:
        if pending:
            if not identity_set(None) and not args.name and not term.ok:
                pending.add(NAME_Q, "--name <钉钉姓名>", blocking=False)
            report_pending(pending, args, dry)
        return pulled   # 这里装的是退出码
    if not (collab / SETUP_REL).is_file():
        out(FAIL, f"协作区里没有 {SETUP_REL.as_posix()}：版本太旧，先在 {collab} 里 git pull 再重跑")
        return EXIT_ERR

    # 3 ---------------------------------------------------------------
    step(3, "预览改动")
    ptype, migrate = args.type, args.migrate
    while True:
        code, so, se = run(setup_cmd(collab, root, args, ptype, migrate, True, pulled), timeout=300)
        text = (so + ("\n" + se if se else "")).strip()
        if "认不出项目类型" in text and term.ok:
            m = re.search(r"认不出项目类型（(.*?)）", text)
            out(INFO, f"认不出这个目录的类型（{m.group(1) if m else '依赖里看不出'}），选一下：")
            ptype = choose_type(term)
            continue
        # setup.py 自己的「去掉 --dry-run 再运行」提示在这里不适用，由本脚本来问
        indent("\n".join(ln for ln in text.splitlines() if "dry-run：未写入任何文件" not in ln))
        if code not in (EXIT_OK, EXIT_ASK):
            out(FAIL, "setup.py 预览出错，按上面 [FAIL] 那行处理后重跑")
            return EXIT_ERR
        if "认不出项目类型" in text:
            pending.add("这个目录是哪类？" + " / ".join(f"{label}（{t}）" for t, label in TYPE_MENU), "--type <类型>")
            break
        if "[迁移]" in text and not migrate and not args.no_migrate:
            if term.ok:
                if term.confirm("上面 [迁移] 列出的是老项目照旧模板手抄的协作内容，换成 ai-collab 区块？", False):
                    migrate = True
                    continue
                args.no_migrate = True
                out(INFO, "保留老内容，只加 ai-collab 区块（以后想换，加 --migrate 重跑）")
            else:
                pending.add("上面 [迁移] 列出的老协作内容：换成 ai-collab 区块，还是保留？",
                            "--migrate（替换）或 --no-migrate（保留）", cmd_flag="<--migrate 或 --no-migrate>")
        break
    setup_changes = "无改动，已经是接入好的状态" not in text
    skills_jobs = skills_preview(args, collab)
    skills_changes = any(j[2] for j in skills_jobs)
    summary = change_summary(text, root, skills_jobs)
    if claude_needs_plugin():
        out(INFO, "要在 Claude Code 里用 bmo 新建项目、环境检查（主要是产品同学）的，再在终端运行这三条装插件；"
                  "开发可以不装，协作区的 skill 已经装进 ~/.claude/skills（本脚本不替你执行）：")
        print(f"         claude plugin marketplace add {MARKET_URL}\n"
              "         claude plugin install bmo@gupo-bmo\n"
              "         claude plugin install ai-collab@gupo-bmo", flush=True)
    who = identity_set(collab)
    if not who and not args.name and not term.ok:
        pending.add(NAME_Q, "--name <钉钉姓名>", blocking=False)
    if (setup_changes or skills_changes) and not term.ok and not args.yes:
        pending.add("确认写入上面列出的改动：" + "；".join(summary or ["见上面预览"]), "--yes")

    if dry:
        if pending:
            report_pending(pending, args, dry)
            return EXIT_ASK
        if setup_changes or skills_changes:
            print("\n--dry-run：什么都没写。去掉 --dry-run 再运行即可写入。", flush=True)
            return EXIT_ASK
        print("\n[OK]   已经接好了，没有要改的", flush=True)
        return EXIT_OK
    if pending.blocking():
        report_pending(pending, args, dry)
        return EXIT_ASK

    # 4 ---------------------------------------------------------------
    step(4, "写入")
    if not (setup_changes or skills_changes):
        out(OK, "没有要写的，已经是接好的状态")
    else:
        if term.ok and not args.yes:
            print("将要写入：", flush=True)
            for x in summary or ["按上面「改动」写入项目和本机配置"]:
                print(f"  - {x}", flush=True)
            if not term.confirm("确认写入？", True):
                out(INFO, "已取消，什么都没写")
                return EXIT_OK
        if setup_changes:
            code = run_stream(setup_cmd(collab, root, args, ptype, migrate, False, pulled), keep=AfterPreview())
            if code not in (EXIT_OK, EXIT_ASK):
                out(FAIL, "setup.py 写入出错，按上面 [FAIL] 那行处理后重跑")
                return EXIT_ERR
        for name, cmd, changed, _ in skills_jobs:
            if not changed:
                continue
            out(INFO, f"安装{name}的 skills：" + " ".join(quote(tilde(c)) for c in cmd[1:]))
            if run_stream(cmd):
                out(WARN, f"{name}的 skills 没装成功，不影响接入；之后可重跑")

    # 5 ---------------------------------------------------------------
    step(5, "收尾检查")
    exit_code = EXIT_OK
    who = identity_set(collab)
    if who:
        out(OK, f"身份：{who}")
    else:
        name = (args.name or "").strip()
        if not name and term.ok:
            name = term.ask("git 用户名还没设置。你的钉钉姓名（直接回车跳过）：").strip()
            if name and not (args.yes or term.confirm(f"运行 git config --global user.name \"{name}\"？", True)):
                name = ""
        if name:
            code, _, se = run(["git", "config", "--global", "user.name", name])
            out(OK if code == 0 else FAIL, f"已设置 git user.name={name}" if code == 0 else f"设置失败：{se}")
        else:
            out(WARN, "git 用户名没设置：协作区认不出你是谁。运行 git config --global user.name \"<钉钉姓名>\"")
            if not term.ok:
                exit_code = EXIT_ASK
    check_dws(term, args)

    print("\n== 接好了 ==", flush=True)
    if is_git:
        print("  - 项目里的 AGENTS.md、.gitignore 有改动的，自己检查后提交（脚本不替你提交）", flush=True)
    if not args.no_env and args.collab_source != SUBMODULE_SRC:
        print(f"  - 协作区位置已写进环境变量 {ENV_NAME}（{collab}）：以后在任何项目跑，"
              "都会通过这个变量找到同一份协作区，不会再下第二份", flush=True)
    print("  - 必须新开一个 AI 会话再用：项目 AGENTS.md 里的协作区规则、环境变量和 skills 都只在会话开始时读取，"
          "接着用现在这个会话，AI 不会按协作区流程走（新开终端、重启 IDE 同理）", flush=True)
    print("  - 别的项目：到那个项目里再跑一次同一条命令，或在那个项目里对 AI 说「接入协作区」（skills 已装好）", flush=True)
    if os.environ.get("GUPO_SETUP_ENTRY") in ("sh", "ps1"):
        print("  - 这条命令本身就是给当前项目接入，不需要再单独跑 ai-collab-setup", flush=True)
    print("  - 验证：在这个目录新开 AI 会话，说「我有哪些接口任务」", flush=True)
    if any(name == "协作区" for name, *_ in skills_jobs):
        print("  - 协作区的 skill（设计规范、PPT、契约流程）也装进了各 AI 工具：平时直接说「做一个 xx 移动端页面」"
              "AI 会自己用规范，想强制用就点名（如「用 gupo-mobile-design」）", flush=True)
    if exit_code == EXIT_ASK:
        pending.add(NAME_Q, "--name <钉钉姓名>", blocking=False)
        report_pending(pending, args, dry, wrote=True)
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n已取消", flush=True)
        sys.exit(EXIT_ERR)
