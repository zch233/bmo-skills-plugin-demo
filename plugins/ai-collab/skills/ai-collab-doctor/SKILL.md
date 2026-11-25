---
name: ai-collab-doctor
description: 检查当前项目和本机的协作区接入状态（协作区工作副本、是否最新、身份、钉钉 CLI、.ai-collab 链接、AGENTS.md 区块），只检查不修改。用户说「检查协作区」「协作区接好了吗」「AI 找不到接口文档 / 任务」时使用。
---

# 检查协作区接入

先更新：本 skill 目录（本文件所在目录）在 git 工作副本里时，运行 `git -C <本 skill 目录> pull --ff-only`；拉到了新内容就重新读一遍本文件再开始。失败（不是 git 仓库、没网、有本地改动）就忽略，继续往下做。

除了上面的更新，只检查、不写任何文件。命令写 `python3`，Windows 用 `python`。

1. 用和接入同一个脚本做只读检查（ai-collab-setup 的 `scripts/bootstrap.py`，在本 skill 旁边）：

   ```bash
   python3 <本 skill 目录>/../ai-collab-setup/scripts/bootstrap.py <当前目录> --dry-run --no-skills
   ```

   `--dry-run` 不写文件、不 clone、不拉取（只和远端比较）、不提问。找协作区的顺序和接入时完全一样。

2. 按输出给用户一张清单，例如：

   ```
   ✅ 协作区：~/code/ai_collab（与远端一致）
   ✅ 当前开发者：张超
   ❌ 钉钉 CLI 未登录         → 运行 dws auth login
   ❌ 项目里没有 .ai-collab   → 说「接入协作区」
   ✅ AGENTS.md 区块是最新的
   ```

   对应关系：`[OK]` 是 ✅，`[WARN]` / `[FAIL]` 和「改动」里列出的每一项是 ❌；`[迁移]` 说明项目里还有照旧模板手抄的协作内容，也算 ❌。「需要你决定」里出现「协作区克隆到哪」说明本机还没有协作区，出现「这个目录是哪类」说明这个目录还没接入过。

3. 退出码 0 就告诉用户已接好；退出码 2（有 ❌）就建议说「接入协作区」（ai-collab-setup；钉钉、身份这类本机问题按提示单独处理）；退出码 1 把 `[FAIL]` 那行原样告诉用户。
