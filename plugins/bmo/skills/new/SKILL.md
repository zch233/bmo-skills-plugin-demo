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

脚本输出里有“⚠️ … 接入要求有变化”：说明模板分支建得早，之后 bmo 的接入要求变了。按提示运行那条 `git diff`，只看「接入方式2」里新增或修改的部分，用业务语言告诉用户“bmo 新增了 xx 接入要求，我补到项目里”，然后改**项目自己的文件**（如 `env/.env` 加接口地址、`package.json` 加依赖后重新 `pnpm install`、`src/stores/permission.ts`、`src/router/index.ts`），改完单独提交 `chore: 补齐 bmo 新的接入要求`，并在交付时提醒用户转告 bmo 维护者更新模板分支。

病种没设置成功（三项和清单对不上、同名有多条）时项目照常创建：把脚本给出的相近组合给用户看，请他回智元矩阵表核对，然后按项目里 `.claude/skills/bmo-disease/SKILL.md` 设置。不要自己改用户给的值去凑。

出错时：

- `接入 bmo 时有冲突`（package.json 以外的文件，package.json 会自动合并）：**能继续接入**。打开冲突文件，两边改动都保留，同一处以模板（HEAD）为准、补上 bmo 新增的内容。bmo 在这个文件里**必须保留什么，以 bmo README 的「接入方式2」为准**（`git fetch bmo master && git show bmo/master:README.md`）：冲突文件基本都对应其中某一步，如 `stores/permission.ts` 是第 7 步的 glob 和 `isBmoBusiness` 分流、`src/router/index.ts` 是第 6 步的 `businessStore.init` 和第 7 步的 `bmoRoutes`、`vite.config.ts` 是第 2 步的别名和代理、`env/.env` 是第 5 步的接口地址，解决后逐条核对那一步要求的内容都还在；`git add` 这些文件后，**用同样的参数加 `--resume` 再运行一次脚本**（不要手动 `cherry-pick --continue`），它会接着摘完剩下的提交（再冲突就重复这一步），并做完后续所有步骤。
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
4. **让项目自带的功能在这个窗口里也能用**：项目自带的 skill（加模块、做页面、打开项目、改病种、提交、发版）放在项目的 `.claude/skills/`，当前窗口启动时项目还不存在，所以还没加载。斜杠命令只能用户自己输入，把下面这段原样发给用户（路径换成实际的项目绝对路径）：

   > 项目自带的助手功能（加模块、做页面、发版等）需要加载一下，**请在输入框里输入下面这行并回车**：
   >
   > ```
   > /add-dir <项目绝对路径>
   > ```
   >
   > 以后打开这个项目：桌面应用新建会话时选择项目文件夹；终端里 `cd <项目绝对路径>` 然后 `claude`。

   用户输入后，后续要求按项目 skill 来处理。用户如果是在项目目录里启动的当前窗口（工作目录就是项目），改成让他输入 `/reload-skills`。
   `/add-dir` 只加载 skill，项目里禁止修改 bmo 子模块的防护配置要在项目目录里启动才生效：在这个窗口里继续做时你自己也要遵守，不要改 `packages/bmo-business-pc`。
   **之后的提醒**：用户在这个窗口里接着提项目上的要求（加模块、做页面、改病种、打开项目、提交、发版等），而你可用的 skill 里还没有 `bmo-add` / `bmo-compose` 这些项目 skill（说明用户还没输入 `/add-dir`），先简短提醒一次再继续：

   > 小提示：项目自带的助手功能还没加载，加载后做得更准（会优先复用现有功能、按项目规范提交）。在输入框输入 `/add-dir <项目绝对路径>` 回车即可；不加载我也可以先按通用方式帮你做。

   同一个窗口只提醒一次，用户说不用就照常继续。
5. 不要替用户推送代码。之后要保存到公司仓库、发版时，在项目里说“关联仓库”“发版”即可（项目自带 bmo-git、bmo-release）：仓库和发版流水线要先请**运维**建好、配好。
