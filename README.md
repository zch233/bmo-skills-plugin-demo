# bmo 项目助手（Claude Code 插件）

让产品同学在 Claude Code 里用聊天的方式完成 bmo 项目的环境准备和新建：

| 命令 | 说法示例 | 做什么 |
|---|---|---|
| `/bmo:doctor` | “帮我检查环境” | 检查并安装 Git、Node、pnpm，配置 Git 用户信息和 codeup 仓库权限 |
| `/bmo:new` | “帮我创建一个新项目” | 下载古珀模板、接入 bmo、安装依赖、挑选功能模块、启动项目 |

项目建好之后，在项目目录里打开 Claude Code，还能用项目自带的 skill（随 bmo 子模块同步）：接入现有模块（bmo-add）、组合现有功能做新页面（bmo-compose）、开发自定义页面（bmo-page）。

## 安装

前提：已安装 [Claude Code](https://code.claude.com) 和 [Git](https://git-scm.com/downloads)（Windows 版 Claude Code 本身也依赖 Git）。

在 Claude Code 里依次输入：

```
/plugin marketplace add zch233/bmo-skills-plugin-demo
/plugin install bmo@gupo-bmo
```

电脑上没有配置 GitHub SSH key 时，先设置环境变量 `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` 再执行，否则插件下载或更新可能失败。

装好后直接说“帮我检查环境”或“帮我创建一个新项目”即可，也可以输入 `/bmo:doctor`、`/bmo:new`。

## 更新

插件没有固定版本号，跟随仓库最新提交。更新：

```
/plugin marketplace update gupo-bmo
```

或在 `/plugin` → Marketplaces 里给 `gupo-bmo` 打开自动更新。

## 目录

```
.claude-plugin/marketplace.json     插件市场清单
plugins/bmo/
  .claude-plugin/plugin.json        插件清单
  skills/doctor/SKILL.md            /bmo:doctor
  skills/new/SKILL.md               /bmo:new
  scripts/new-project.mjs           新建项目脚本（复刻 @gupo-admin/cli new 的逻辑，cli 改了这里要跟着改）
```

`new-project.mjs` 也可以单独运行：`node plugins/bmo/scripts/new-project.mjs --name my-project [--ui] [--dir <父目录>] [--skip-install]`。
