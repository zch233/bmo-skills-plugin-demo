---
name: new
description: 新建一个接入 bmo 中台的前端项目：下载古珀模板、接入 bmo、设置病种、安装依赖、挑选功能模块、启动并登录打开。用户说“帮我创建模板/新建项目/搭一个新项目”时使用。
---

# 新建 bmo 项目

使用者多半是产品同学：用业务语言沟通，只问必须他决定的事。

## 1. 环境

先按 /bmo:doctor 的检查表快速检查（Git、Git 用户信息、Node ≥ 20、pnpm ≥ 9.10、codeup SSH 权限）。有任何一项不满足，先按 doctor 的流程修好再继续。

## 2. 问清四件事（一次问完）

- **项目名称**：让用户直接说中文名，如“基层慢病管理系统”。这个中文名就是**系统名称**（浏览器标签标题、页面左上角的系统名，传给 `--title`）；文件夹名由你起成英文小写加中划线（如 `primary-chronic-care`，传给 `--name`），告诉用户一声即可。用户只给了英文名时，再问一句中文系统名称。
- **放在哪里**：默认当前目录下；用户有习惯的目录就用他的。
- **界面风格**：旧版界面（bmo 的 docs 分支）还是新版界面（docs-ui 分支）。用户说不清就默认新版。
- **病种**：项目落地的病种场景，要三项——场景名称、基线编号（disease_code）、场景编码（scene_code），**必须和智元矩阵病种场景表一致**（https://alidocs.dingtalk.com/i/nodes/NZQYprEoWoeA9yzNTq4R4n9xJ1waOeDk ），例如“慢病全科 CHRONIC CHRONIC_ALL”。用户不清楚就请他在那张表里找到项目那一行发过来；用户说先随便用就默认 **糖尿病 DM SLOW_DM**，并提醒之后要换成实际的。

## 3. 创建

运行（耗时几分钟，用较长的超时时间）：

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/new-project.mjs" --name <项目名称> --title "<系统名称>" --dir <父目录> [--ui] [--disease "<病种>"]
```

`--disease` 写三项（如 `--disease "慢病全科 CHRONIC CHRONIC_ALL"`）；用户默认糖尿病时不传。

脚本会依次：从 codeup 下载模板并初始化 git → 接入 bmo（摘 bmo 模板分支的提交，package.json 冲突自动合并）→ 补齐 `bmo:*` 命令后运行 `pnpm bmo:init`（拉 bmo 子模块、`bmo:update` 更新到最新 master、同步 bmo 的 AI skill）→ 设置默认病种和系统名称（`env/.env` 的 `VITE_APP_NAME`）→ `pnpm install`。

病种没设置成功（三项和清单对不上、同名有多条）时项目照常创建：把脚本给出的相近组合给用户看，请他回智元矩阵表核对，然后按项目里 `.claude/skills/bmo-disease/SKILL.md` 设置。不要自己改用户给的值去凑。

出错时：

- `接入 bmo 时有冲突`（package.json 以外的文件，package.json 会自动合并）：**能继续接入**。打开冲突文件，两边改动都保留，同一处以模板（HEAD）为准、补上 bmo 新增的内容；`git add` 这些文件后，**用同样的参数加 `--resume` 再运行一次脚本**（不要手动 `cherry-pick --continue`），它会接着摘完剩下的提交（再冲突就重复这一步），并做完后续所有步骤。
  完成后告诉用户：“这次接入时模板和 bmo 有冲突，已经处理好了，不影响使用；请转告 bmo 维护者更新 docs / docs-ui 分支，免得下次建项目再遇到。”
- 拉代码提示没有权限：回到 doctor 第 3 步。
- `pnpm install` 失败：看报错，多半是网络或 Node 版本问题，修好后在项目目录重跑 `pnpm install`。

## 4. 挑功能模块

在项目目录运行 `node packages/bmo-business-pc/scripts/bmo-add.mjs --list`，按业务分组把可用模块介绍给用户，让他挑需要的（选项多就列编号让他回复），然后：

```bash
node packages/bmo-business-pc/scripts/bmo-add.mjs <模块1> <模块2> ...
```

文件不存在说明 bmo 拉取失败或版本异常，检查 `packages/bmo-business-pc` 后再继续。

## 5. 启动并交付

1. 在项目目录后台启动 `pnpm dev`，从输出里读到本地地址和端口（一般是 8080，被占用会自动换）。
2. **登录打开**：项目接了真实接口，直接打开本地地址会跳到统一登录页。按项目里 `.claude/skills/bmo-open/SKILL.md` 的第 3 步做：打开 `https://demo.group-ds.com/bmo-auth-pc/#/`，把那一步里给用户的说明**原样**发给用户（包括加粗的“手速一定要快”和链接示例）。项目里没有那个文件时，至少要告诉用户：登录后在「中台应用」里点任意一个应用，**⚠️ 页面一打开就马上复制地址栏链接，手速一定要快**，对的链接很长，形如 `https://demo.group-ds.com/bmo-business-pc/#/auth?system_code=xxx&org_id=xxx&arc_code=xxx&token=eyJ0eXAi...`。拿到后在项目目录运行：

   ```bash
   node packages/bmo-business-pc/scripts/bmo-login.mjs "<用户粘贴的链接>" --port <端口> --open
   ```

   脚本会把链接换成本地地址并在浏览器打开，有效期内之后直接打开 `http://localhost:<端口>/` 即可。链接里带登录凭证，不要写进文件。
3. 告诉用户项目位置、系统名称、病种（三项）、已接入的模块。
4. **提醒用户之后在项目目录里打开 Claude Code**（`cd <项目目录>` 后运行 `claude`，或在编辑器里打开这个文件夹）。项目自带的 skill 只在项目目录里生效，之后说“帮我加入患者管理”“做一个转诊监管页面”“帮我打开项目”“把病种改成高血压”都在那里进行。
5. 不要替用户推送代码。之后要保存到公司仓库、发版时，在项目里说“关联仓库”“发版”即可（项目自带 bmo-git、bmo-release）：仓库和发版流水线要先请**运维**建好、配好。
