---
name: new
description: 新建一个接入 bmo 中台的前端项目：下载古珀模板、接入 bmo、安装依赖、挑选功能模块并启动。用户说“帮我创建模板/新建项目/搭一个新项目”时使用。
---

# 新建 bmo 项目

使用者多半是产品同学：用业务语言沟通，只问必须他决定的事。

## 1. 环境

先按 /bmo:doctor 的检查表快速检查（Git、Git 用户信息、Node ≥ 20、pnpm ≥ 9.10、codeup SSH 权限）。有任何一项不满足，先按 doctor 的流程修好再继续。

## 2. 问清三件事（一次问完）

- **项目名称**：英文小写加中划线，如 `weight-clinic`；用户给中文名就帮他起一个英文名并确认。
- **放在哪里**：默认当前目录下；用户有习惯的目录就用他的。
- **界面风格**：旧版界面（bmo 的 docs 分支）还是新版界面（docs-ui 分支）。用户说不清就默认新版。

## 3. 创建

运行（耗时几分钟，用较长的超时时间）：

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/new-project.mjs" --name <项目名称> --dir <父目录> [--ui]
```

脚本会依次：从 codeup 下载模板并初始化 git → 接入 bmo（摘 bmo 模板分支的提交，package.json 冲突自动合并）→ 拉取 bmo 子模块 → `pnpm install` → 同步 bmo 的 AI skill。

出错时：

- `cherry-pick 有冲突`（package.json 以外的文件）：打开冲突文件，两边改动都保留，同一处以模板（HEAD）为准、补上 bmo 新增的内容；`git add` 后 `git -c core.editor=true cherry-pick --continue`，再在项目目录执行 `git submodule update --init`、`pnpm install`、`node packages/bmo-business-pc/scripts/bmo-skills.mjs`（文件存在时）。
- 拉代码提示没有权限：回到 doctor 第 3 步。
- `pnpm install` 失败：看报错，多半是网络或 Node 版本问题，修好后在项目目录重跑 `pnpm install`。

## 4. 挑功能模块

在项目目录运行 `node packages/bmo-business-pc/scripts/bmo-add.mjs --list`，按业务分组把可用模块介绍给用户，让他挑需要的（选项多就列编号让他回复），然后：

```bash
node packages/bmo-business-pc/scripts/bmo-add.mjs <模块1> <模块2> ...
```

文件不存在说明项目里的 bmo 版本较旧，跳过这一步，告诉用户模板已默认带了一组常用模块，以后可以再调整。

## 5. 启动并交付

1. 在项目目录后台启动 `pnpm dev`，等出现本地地址（一般是 `http://localhost:8080`），把地址给用户在浏览器打开。
2. 告诉用户项目位置和已接入的模块。
3. **提醒用户之后在项目目录里打开 Claude Code**（`cd <项目目录>` 后运行 `claude`，或在编辑器里打开这个文件夹）。项目自带的 bmo-add / bmo-compose / bmo-page 只在项目目录里生效，之后说“帮我加入患者管理”“做一个转诊监管页面”都在那里进行。
4. 不要替用户推送代码；需要关联远程仓库时，请用户提供仓库地址再操作。
