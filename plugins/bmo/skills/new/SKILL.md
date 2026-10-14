---
name: new
description: 新建一个接入 bmo 中台的前端项目：下载古珀模板、接入 bmo、设置病种、安装依赖、挑选功能模块、启动并登录打开。用户说“帮我创建模板/新建项目/搭一个新项目”时使用。
---

# 新建 bmo 项目

使用者多半是产品同学：用业务语言沟通，只问必须他决定的事。

## 1. 环境

先按 /bmo:doctor 的检查表快速检查（Git、Git 用户信息、Node ≥ 20、pnpm ≥ 9.10、codeup SSH 权限）。有任何一项不满足，先按 doctor 的流程修好再继续。

## 2. 问清四件事（一次问完）

- **项目名称**：英文小写加中划线，如 `weight-clinic`；用户给中文名就帮他起一个英文名并确认。
- **放在哪里**：默认当前目录下；用户有习惯的目录就用他的。
- **界面风格**：旧版界面（bmo 的 docs 分支）还是新版界面（docs-ui 分支）。用户说不清就默认新版。
- **病种**：这个项目做哪个病种，如冠心病、高血压、糖尿病、慢病全科、减重管理。用户说不清就默认**冠心病**。

## 3. 创建

运行（耗时几分钟，用较长的超时时间）：

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/new-project.mjs" --name <项目名称> --dir <父目录> [--ui] [--disease "<病种>"]
```

`--disease` 写病种名（如 `--disease 高血压`）；用户默认冠心病时不传。

脚本会依次：从 codeup 下载模板并初始化 git → 接入 bmo（摘 bmo 模板分支的提交，package.json 冲突自动合并）→ 拉取 bmo 子模块并更新到最新 → 补齐 `bmo:*` 命令、设置默认病种 → `pnpm install` → 同步 bmo 的 AI skill。

病种没设置成功（同名有多条、清单里没有）时项目照常创建：在项目目录运行 `node packages/bmo-business-pc/scripts/bmo-disease.mjs --list`，把候选（带落地区域）给用户选，再运行 `node packages/bmo-business-pc/scripts/bmo-disease.mjs <名称> <编码> <场景>`；清单里没有的病种要问用户编码和场景编码。

出错时：

- `cherry-pick 有冲突`（package.json 以外的文件）：打开冲突文件，两边改动都保留，同一处以模板（HEAD）为准、补上 bmo 新增的内容；`git add` 后 `git -c core.editor=true cherry-pick --continue`，再在项目目录执行 `git submodule update --init`、`pnpm install`、`node packages/bmo-business-pc/scripts/bmo-skills.mjs`（文件存在时）。
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
2. **登录打开**：项目接了真实接口，直接打开本地地址会跳到统一登录页。按项目里 `.claude/skills/bmo-open/SKILL.md` 的第 3 步做：打开 `https://demo.group-ds.com/bmo-auth-pc/#/`，请用户登录后在「中台应用」里点任意一个应用、**页面一打开就马上复制地址栏链接**发过来，然后在项目目录运行：

   ```bash
   node packages/bmo-business-pc/scripts/bmo-login.mjs "<用户粘贴的链接>" --port <端口> --open
   ```

   脚本会把链接换成本地地址并在浏览器打开，有效期内之后直接打开 `http://localhost:<端口>/` 即可。链接里带登录凭证，不要写进文件。
3. 告诉用户项目位置、病种、已接入的模块。
4. **提醒用户之后在项目目录里打开 Claude Code**（`cd <项目目录>` 后运行 `claude`，或在编辑器里打开这个文件夹）。项目自带的 skill 只在项目目录里生效，之后说“帮我加入患者管理”“做一个转诊监管页面”“帮我打开项目”“把病种改成高血压”都在那里进行。
5. 不要替用户推送代码；需要关联远程仓库时，请用户提供仓库地址再操作。
