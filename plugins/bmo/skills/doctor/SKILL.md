---
name: doctor
description: 检查并修好开发 bmo 项目需要的电脑环境：Git、Node、pnpm、Git 用户信息、codeup 代码仓库权限（SSH key）。用户第一次使用、说“帮我检查环境”“装不上/拉不下代码/跑不起来”，或者 /bmo:new 之前使用。
---

# 环境检查与修复

使用者多半是第一次接触开发环境的产品同学：**能自动做的直接做，必须他动手的一次只给一步**，每步做完都复查。不要甩命令和报错原文给对方，用大白话说明在做什么。

开始前先说一句：接下来会安装一些开发工具，期间 Claude Code 可能会弹出“是否允许执行命令”的确认框，选允许即可。

## 1. 先全部检查一遍，再列清单

先判断系统：Windows（PowerShell）、macOS、Linux/WSL。逐项检查，**全部查完再汇总**，不要发现一个问题就停下：

| 项目 | 检查方式 | 要求 |
|---|---|---|
| Git | `git --version` | 已安装 |
| Git 用户信息 | `git config --global user.name` / `user.email` | 都有值 |
| Node | `node -v` | 不低于 v20，推荐 v22 |
| pnpm | `pnpm -v` | 不低于 9.10 |
| codeup 权限 | `ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -T git@codeup.aliyun.com` | 输出包含 `Welcome` 或成功认证字样 |

用清单告诉用户结果，例如：

```
✅ Git 已安装
❌ Node 未安装        → 我来装
❌ pnpm 未安装        → 我来装
❌ 代码仓库权限        → 需要你操作一步（约 1 分钟）
```

## 2. 能自动修的直接修

- **Git**：Windows `winget install --id Git.Git -e`；macOS `xcode-select --install` 或 `brew install git`；Linux 用系统包管理器。装完提醒用户可能需要重开终端 / Claude Code。
- **Node**：Windows `winget install OpenJS.NodeJS.LTS`；macOS `brew install node@22`；Linux/WSL 用 nvm 安装 v22。装完复查 `node -v`。
- **pnpm**：`corepack enable && corepack prepare pnpm@latest --activate`；不行就 `npm install -g pnpm`。
- **Git 用户信息**：问用户的姓名和公司邮箱，再 `git config --global user.name "…"`、`git config --global user.email "…"`。
- 安装需要管理员权限、或 winget/brew 不可用时，告诉用户去哪里下载安装包（git-scm.com、nodejs.org），装完回来说一声。

## 3. 必须用户动手的：codeup 仓库权限

模板和 bmo 都在阿里云 codeup 上，用 SSH 拉取。

1. 没有 SSH key 就生成：`ssh-keygen -t ed25519 -C "<用户邮箱>" -N "" -f ~/.ssh/id_ed25519`（已有就复用，不要覆盖）。
2. 把公钥 `~/.ssh/id_ed25519.pub` 的内容复制到剪贴板（Windows `Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard`，macOS `pbcopy < ~/.ssh/id_ed25519.pub`，WSL `clip.exe < ~/.ssh/id_ed25519.pub`），同时把公钥内容贴在对话里备用。
3. 打开 codeup 的 SSH 公钥设置页（Windows `start`、macOS `open`、WSL `explorer.exe` + 网址）：`https://account-devops.aliyun.com/settings/ssh`
4. 只给一句话：“页面已打开，点『添加 SSH 公钥』，粘贴，保存，然后回复我『好了』。”
5. 用户回复后复查第 1 步表格里的 ssh 命令：
   - 成功：继续。
   - `Permission denied (publickey)`：公钥没加上或加错了账号，带用户再检查一遍。
   - 认证成功但后续拉代码提示没有权限 / 仓库不存在：说明账号还没被加进代码组，请用户找研发负责人开通 bmo 和模板仓库的权限，这一步 AI 解决不了。

## 4. 收尾

全部 ✅ 后告诉用户环境已就绪，可以说“帮我创建项目”开始（对应 /bmo:new）。

每一项都可以重复执行：先检查，已经满足就跳过，不要重复安装或覆盖已有配置。
