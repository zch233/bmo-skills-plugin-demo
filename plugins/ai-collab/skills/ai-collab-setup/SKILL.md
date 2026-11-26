---
name: ai-collab-setup
description: 把当前项目（或测试、产品自己的工作目录）接入古珀协作区：运行本 skill 目录下的 scripts/bootstrap.py，找到或 clone 协作区，预览后写环境变量、建 .ai-collab 链接、写 AGENTS.md 区块，并装好 skills（含协作区的设计规范、PPT、契约流程 skill）。用户说「接入协作区」「接入 ai-collab」「配一下协作区」「项目里没有 .ai-collab」时使用。
---

# 接入协作区

先更新：本 skill 目录（本文件所在目录）在 git 工作副本里时，运行 `git -C <本 skill 目录> pull --ff-only`；拉到了新内容就重新读一遍本文件再开始。失败（不是 git 仓库、没网、有本地改动）就忽略，继续往下做。

所有逻辑都在本 skill 目录下的 `scripts/bootstrap.py`（和一条命令接入 `setup.sh` / `setup.ps1` 调的是同一个文件）：找协作区、clone、配 SSH 公钥、调用协作区的 `setup.py` 预览和写入、装 skills、检查 git 用户名和钉钉 CLI。**不要自己去找协作区、建链接、改 AGENTS.md。**

使用者可能是开发、测试或产品同学：用大白话说明在做什么，必须他决定的事一次问清。命令写 `python3`，Windows 用 `python`。先查 `python3 --version`（Windows `python --version`），要求 3.8 及以上；没有就装：Windows `winget install --id Python.Python.3.12 -e`，macOS `xcode-select --install`，Linux 用系统包管理器；装完复查（Windows 可能要重开终端 / AI 工具）。

## 1. 先跑一次，看要做什么

在项目目录（测试、产品可以是自己的工作文件夹，空文件夹也行；**不要用用户主目录**）运行：

```bash
python3 <本 skill 目录>/scripts/bootstrap.py
```

AI 工具里没有终端，脚本只做检查和预览，不写项目文件、不生成密钥、不改 git 配置。按退出码处理：

- **0**：已经接好，或这次没有要改的。跳到第 3 步。
- **2**：输出最后有「需要你决定」清单和「下一次这样运行」的命令。把清单里的问题**一次问清用户**（不要替用户选），同时把预览里的「改动」用大白话讲给他：项目里通常只改 `AGENTS.md` 和 `.gitignore`；本机写环境变量 `AI_COLLAB_HOME`，用 Claude Code 的还会在 `~/.claude/settings.json` 放行协作区目录；装 skills（插件仓库的，加上协作区 `skills/` 下的，后者也会链到 `~/.claude/skills`）。「确认写入」那一条会把这些逐项列出来，照着讲。
- **1**：按 `[FAIL]` 那行处理，处理不了就把那一行原样告诉用户。

清单里常见的问题和对应参数：

| 问题 | 参数 |
|---|---|
| 协作区放哪（本机还没有协作区）：① `~/ai_collab`（推荐：固定放个人目录，以后所有项目共用）② 项目上一级目录 ③ 自己指定 | `--clone-to <路径>` |
| 这个目录是哪类：产品 / 测试 / PC 前端 / 移动前端 / 大屏前端 / 后端 | `--type product\|tester\|pc\|mobile\|screen\|backend` |
| 老项目里照旧模板手抄的协作内容：替换还是保留（把 `[迁移]` 列出的文件和段落给用户看） | `--migrate` / `--no-migrate` |
| 确认写入预览里的改动 | `--yes` |
| git 用户名没设置，问钉钉姓名 | `--name <姓名>` |

## 2. 用户回答后带参数重跑

```bash
python3 <本 skill 目录>/scripts/bootstrap.py --yes --type tester --name 张三   # 按用户的回答组合
```

- **codeup SSH 公钥没配好**（clone 报 `Permission denied (publickey)`）：带 `--yes` 时脚本会生成密钥（已有就复用，不覆盖）、把公钥复制到剪贴板、打开 codeup 设置页，然后退出码 2。请用户在页面上点「添加 SSH 公钥」粘贴保存，回复「好了」后用同样的参数再跑一次。SSH 通了还 clone 不下来，请用户找研发负责人开通 ai_collab 仓库。
- 用户更想自己在终端里一步步确认的，请他在项目目录运行一条命令接入（Mac / Linux `curl -fsSL https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.sh | bash`，Windows PowerShell `irm https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.ps1 | iex`），脚本会逐项询问。
- 再次退出码 2 就重复第 1 步的处理，直到 0。

## 3. 收尾

- 把输出里「项目里待提交的改动」给用户看，提醒他自己检查后提交。**不要替用户 commit / push。**
- 提醒**必须新开一个 AI 会话**：项目 `AGENTS.md` 里的协作区规则、环境变量和 skills 都只在会话开始时读取，当前会话（包括你自己）不会按新规则走。不要跟用户说「不用重启、可以直接用」。
- 告诉用户：协作区位置写进了环境变量 `AI_COLLAB_HOME`，以后在任何项目跑都会找到同一份，不会再下第二份；**别的项目**到那个项目里再说一次「接入协作区」即可。
- 协作区的 skill（`gupo-*-design`、`gupo-ppt`、`contract-*`）也装进了各 AI 工具：平时直接说「做一个 xx 移动端页面」AI 会自己用规范，想强制用就点名「用 gupo-mobile-design」。
- 输出提示用 Claude Code 的要装插件时，把那三条 `claude plugin …` 命令转告用户（脚本不替用户执行）。
- 钉钉 CLI 没登录的，提醒要发钉钉通知的同学运行 `dws auth login`。
- 告诉用户怎么验证和日常使用：在项目里对 AI 说「我有哪些接口任务」（测试说「我有哪些待测任务」），AI 会按 AGENTS.md 里的区块去读协作区的规则。
