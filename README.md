# bmo 项目助手（Claude Code 插件）

让产品同学在 Claude Code 里用聊天的方式完成 bmo 项目的环境准备和新建：

| 命令 | 说法示例 | 做什么 |
|---|---|---|
| `/bmo:doctor` | “帮我检查环境” | 检查并安装 Git、Node、pnpm，配置 Git 用户信息和 codeup 仓库权限 |
| `/bmo:new` | “帮我创建一个新项目” | 下载古珀模板、接入 bmo（自动更新到最新）、设置病种、安装依赖、挑选功能模块、启动并登录打开 |

项目建好之后，在项目目录里打开 Claude Code，还能用项目自带的 skill（随 bmo 子模块同步）：接入现有模块（bmo-add）、组合现有功能做新页面（bmo-compose）、开发自定义页面（bmo-page）。

## 安装

- **桌面应用**（Windows / Mac）：切到 **Code** 标签页（不是 Cowork），新建会话，文件夹选一个本机目录（Windows 上不要选 WSL 里的，WSL 会话用不了插件）。输入框旁的 **+ → 插件**能管理已装的插件，但添加这个市场要用命令行，把下面这段原样发送：

  > 帮我安装 bmo 项目助手插件，要真正执行安装命令，不要只改 settings.json：
  > 1. 依次运行 `claude plugin marketplace add https://gitee.com/z-null/bmo-skills-plugin-demo.git` 和 `claude plugin install bmo@gupo-bmo`。命令行里找不到 `claude` 的话，用 Claude 桌面应用安装目录里自带的 claude 程序执行；没有 git 就先帮我装上 git（Windows 用 winget、Mac 用 xcode-select）。
  > 2. 在用户目录 `.claude/settings.json` 的 `extraKnownMarketplaces.gupo-bmo` 里加上 `"autoUpdate": true`，以后自动更新。
  > 3. 确认用户目录 `.claude/plugins/installed_plugins.json` 里有 `bmo@gupo-bmo`，然后提醒我新建会话。

- **终端**（Claude Code CLI，需要已装 git）：

  ```
  /plugin marketplace add https://gitee.com/z-null/bmo-skills-plugin-demo.git
  /plugin install bmo@gupo-bmo
  ```

  再在 `/plugin` → Marketplaces → 选 `gupo-bmo` → Enable auto-update 打开自动更新。

安装时会弹确认框，命令和上面写的一致再点允许。装好后**新建一个会话**，直接说“帮我检查环境”或“帮我创建一个新项目”即可，也可以输入 `/bmo:doctor`、`/bmo:new`。

## 更新

- 开了自动更新：后台自动拉新版本。
- 没开：桌面应用对 AI 说“帮我更新 bmo 插件”（执行 `claude plugin marketplace update gupo-bmo`）；终端输入 `/plugin marketplace update gupo-bmo`。

## 维护

- 主仓库在 Gitee（`git@gitee.com:z-null/bmo-skills-plugin-demo.git`），GitHub（`git@github.com:zch233/bmo-skills-plugin-demo.git`）只做备份。`origin` 配了两个推送地址，`git push` 一次推到两边，保持同步。新机器 clone 后要重新配：

  ```bash
  git clone git@gitee.com:z-null/bmo-skills-plugin-demo.git
  git remote set-url --add --push origin git@gitee.com:z-null/bmo-skills-plugin-demo.git
  git remote set-url --add --push origin git@github.com:zch233/bmo-skills-plugin-demo.git
  ```

- 插件没写版本号，**推送到 main 即发布**，开了自动更新的人都会拿到：在 `dev` 分支上改，验证过再合进 main。
- 发布前：`claude plugin validate .`，再实际建一次项目：`node plugins/bmo/scripts/new-project.mjs --name t --skip-install`；发布时打 `plugin-<日期>` tag。
- 出了问题用 `git revert` 撤回再推送，不强推。
- 用到 bmo 脚本新参数的改动，等 bmo master 推送后再发布。
- `scripts/new-project.mjs` 复刻了 `@gupo-admin/cli` 的 `new`：**cli 的建项目逻辑改了，这里要跟着改**。
- 影响使用的改动，在群里通知大家更新（命令见上）。
- 完整说明：使用见 bmo 仓库 `docs/bmo-ai-usage.md`，维护、发布与回退见 `docs/bmo-ai-maintain.md`。

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
