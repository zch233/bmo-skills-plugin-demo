#!/usr/bin/env bash
# 古珀协作区一条命令接入（Mac / Linux；Windows 用 setup.ps1）。在项目目录执行：
#   curl -fsSL https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.sh | bash
#   curl -fsSL https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.sh | bash -s -- --type tester
#
# 本文件是薄壳，只做三件事，其余逻辑都在 bootstrap.py：
#   1. 检查 git、Python 3.8+，缺了尽量帮着装，装不了就说明去哪下载
#   2. 把插件仓库 https 克隆到 ~/.gupo/skills/bmo-skills-plugin-demo，已有就 git pull --ff-only
#   3. 运行仓库里的 plugins/ai-collab/skills/ai-collab-setup/scripts/bootstrap.py，参数原样透传
#      （放在 skill 目录里：Claude Code 插件缓存只有 plugins/ai-collab，ai-collab-setup skill 也调它）
#
# 本地试跑可覆盖：GUPO_SKILLS_REPO（插件仓库地址，可以是本地路径或 file://）、GUPO_SKILLS_DIR（克隆位置）。
# 整个流程包在 main 里、最后一行才调用：curl | bash 时保证脚本全部读完再执行。

main() {
  local repo="${GUPO_SKILLS_REPO:-https://gitee.com/z-null/bmo-skills-plugin-demo.git}"
  local dir="${GUPO_SKILLS_DIR:-$HOME/.gupo/skills/bmo-skills-plugin-demo}"
  local rel="plugins/ai-collab/skills/ai-collab-setup/scripts/bootstrap.py"
  local os
  os="$(uname -s 2>/dev/null || echo unknown)"

  echo "== 准备：git、Python、插件仓库 =="

  # 1. git（Mac 上 /usr/bin/git 是占位程序，没装命令行工具时会失败，所以要真跑一次）
  if ! git --version >/dev/null 2>&1; then
    case "$os" in
      Darwin)
        echo "[FAIL] 没有 git。已弹出「命令行开发者工具」安装窗口，点安装，装完后重新运行这条命令"
        xcode-select --install >/dev/null 2>&1 || true ;;
      Linux)
        echo "[FAIL] 没有 git。先安装：Debian / Ubuntu 运行 sudo apt install -y git，CentOS / RHEL 运行 sudo yum install -y git，装完重新运行" ;;
      *)
        echo "[FAIL] 没有 git。到 https://git-scm.com/downloads 下载安装，装完重新运行（Windows 建议在 PowerShell 里用 setup.ps1）" ;;
    esac
    return 1
  fi
  echo "[OK]   $(git --version)"

  # 2. Python 3.8+（Windows 的 Git Bash 里可能只有 py 启动器）
  local py=()
  find_python() {
    py=()
    local c
    for c in python3 python; do
      if command -v "$c" >/dev/null 2>&1 \
        && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
        py=("$c"); return 0
      fi
    done
    if command -v py >/dev/null 2>&1 \
      && py -3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      py=(py -3); return 0
    fi
    return 1
  }
  if ! find_python; then
    if [ "$os" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
      echo "[INFO] 没有 Python 3.8+，用 Homebrew 安装：brew install python"
      brew install python && hash -r
      find_python
    fi
  fi
  if [ ${#py[@]} -eq 0 ]; then
    case "$os" in
      Darwin) echo "[FAIL] 没有 Python 3.8+。到 https://www.python.org/downloads/ 下载安装包，装完重新运行" ;;
      Linux)  echo "[FAIL] 没有 Python 3.8+。Debian / Ubuntu 运行 sudo apt install -y python3，CentOS / RHEL 运行 sudo yum install -y python3，装完重新运行" ;;
      *)      echo "[FAIL] 没有 Python 3.8+。到 https://www.python.org/downloads/ 下载安装，装完重新运行" ;;
    esac
    return 1
  fi
  echo "[OK]   $("${py[@]}" --version 2>&1)"

  # 3. 插件仓库：公开仓库，https 克隆，不需要 SSH；更新失败不阻断
  if [ -d "$dir/.git" ]; then
    if GIT_TERMINAL_PROMPT=0 git -C "$dir" pull --ff-only -q; then
      echo "[OK]   插件仓库已是最新：$dir"
    else
      echo "[WARN] 插件仓库没更新成（没网、有本地改动或分叉），用现有版本继续：$dir"
    fi
  elif [ -e "$dir" ] && [ -n "$(ls -A "$dir" 2>/dev/null)" ]; then
    echo "[WARN] $dir 已存在但不是 git 仓库，直接用里面的文件"
  else
    echo "[INFO] 下载插件仓库到 $dir"
    mkdir -p "$(dirname "$dir")"
    if ! GIT_TERMINAL_PROMPT=0 git clone -q "$repo" "$dir"; then
      echo "[FAIL] 下载失败：检查网络后重跑（地址 $repo）"
      return 1
    fi
  fi
  if [ ! -f "$dir/$rel" ]; then
    echo "[FAIL] 找不到 $dir/$rel：插件仓库版本不对，删掉 $dir 后重跑"
    return 1
  fi

  # 4. 交给 bootstrap.py。curl | bash 时 stdin 是脚本管道，不传给 Python（它会改从 /dev/tty 读输入）
  export GUPO_SETUP_ENTRY=sh
  if [ -t 0 ]; then
    "${py[@]}" "$dir/$rel" "$@"
  else
    "${py[@]}" "$dir/$rel" "$@" </dev/null
  fi
}

main "$@"
