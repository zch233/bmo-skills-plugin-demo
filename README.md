# 古珀 AI 插件 / skills（gupo-bmo）

一套 skill，六个 AI 工具都能用：**Claude Code** 通过插件市场安装（见「安装（Claude Code）」）；**Codex、Cursor、Grok、WorkBuddy / CodeBuddy、Qoder** 由一条命令接入时顺带装好（见「其他 AI 工具」）。skill 都是标准的 Agent Skills（`SKILL.md`）格式，直接说中文就会自动触发，不用记命令。

## 快速开始：一条命令接入协作区

每台电脑、每个项目（测试、产品用一个空文件夹当工作目录，脚本会让你选类型）做一次，两种方法选一种。

**方法一：用 AI**（推荐）。在项目目录新建 AI 会话，把这句发过去：

> 在当前项目目录运行 `curl -fsSL https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.sh | bash`（Windows 用 `irm https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.ps1 | iex`），需要我确认或操作的地方停下来问我。

**方法二：手动**。在项目目录的终端里执行：

```bash
# Mac / Linux（终端）
curl -fsSL https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.sh | bash
```

```powershell
# Windows（PowerShell）
irm https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.ps1 | iex
```

它会：检查 git、Python 3.8+（缺了帮着装）→ 把本仓库克隆到 `~/.gupo/skills/bmo-skills-plugin-demo` → 找到或 clone 协作区（codeup 没配 SSH 公钥时帮你生成、复制并打开设置页）→ 先预览、你确认后写入（项目里只改 `AGENTS.md`、`.gitignore`，本机写环境变量 `AI_COLLAB_HOME`）→ 装好 skills（有 Node 18+ 时）→ 检查 git 用户名和钉钉 CLI。不替你提交。在 AI 工具里运行时脚本不能直接提问，会把要你决定的事列出来，AI 问过你再带参数重跑。

接好了吗：在项目里对 AI 说「我有哪些接口任务」。要发钉钉通知的再运行 `dws auth login`。

带参数（一般用不到，脚本会问）：Mac / Linux 写成 `curl -fsSL …/setup.sh | bash -s -- --type tester`；Windows 写成 `& ([scriptblock]::Create((irm …/setup.ps1))) --type tester`。常用参数：`--type product|tester|pc|mobile|screen|backend`、`--yes`（跳过确认）、`--dry-run`（只看不改）、`--clone-to <协作区位置>`、`--migrate` / `--no-migrate`（老项目手抄内容替换 / 保留）、`--name <钉钉姓名>`、`--no-skills`。

## 有哪些 skill

**bmo 项目助手（插件 `bmo`）**：用聊天的方式完成 bmo 项目的环境准备和新建：

| skill | Claude Code | 其他工具的说法 | 做什么 |
|---|---|---|---|
| `bmo-doctor` | `/bmo-doctor` 或说“帮我检查环境” | “帮我检查环境” | 检查并安装 Git、Node、pnpm，配置 Git 用户信息和 codeup 仓库权限；最后可选接入协作区 |
| `bmo-new` | `/bmo-new` 或说“帮我创建一个新项目” | “帮我创建一个新项目” | 下载古珀模板、接入 bmo（自动更新到最新）、设置病种、安装依赖、挑选功能模块、启动并登录打开 |

**协作区接入（插件 `ai-collab`）**：把项目或自己的工作目录接上团队协作区（接口契约、需求、设计规范、协作流程）。skill 和上面的一条命令跑的是同一个 `skills/ai-collab-setup/scripts/bootstrap.py`（找到或 clone 协作区、问人），真正写文件的是协作区里的 `skills/collab-setup/scripts/setup.py`：

| skill | Claude Code | 其他工具的说法 | 做什么 |
|---|---|---|---|
| `ai-collab-setup` | `/ai-collab-setup` 或说“接入协作区” | “接入协作区” | 找到 / clone 协作区并拉最新，先预览再写入：环境变量 `AI_COLLAB_HOME`、项目里的 `.ai-collab` 链接、`AGENTS.md` 里的 ai-collab 区块 |
| `ai-collab-doctor` | `/ai-collab-doctor` 或说“检查协作区接好了吗” | “检查协作区接好了吗” | 只检查不修改：工作副本、身份、钉钉 CLI、链接、区块 |

> Claude Code 的 `/` 菜单里也可能显示成带插件名的 `/bmo:bmo-doctor`、`/ai-collab:ai-collab-setup`，是同一个。改名前的旧命令（`/bmo:` 后面直接跟 doctor、new 的那种）已经不再可用。

项目建好之后，在项目目录里打开 AI 工具，还能用项目自带的 skill（在项目的 `.claude/skills/` 里，随 bmo 子模块同步）：接入现有模块（bmo-add）、组合现有功能做新页面（bmo-compose）、开发自定义页面（bmo-page）等。Claude Code 自动加载；其他工具暂时要让 AI 直接读对应的 `SKILL.md`。

## 安装（Claude Code）

- **桌面应用**（Windows / Mac）：切到 **Code** 标签页（不是 Cowork），新建会话，文件夹选一个本机目录（Windows 上不要选 WSL 里的，WSL 会话用不了插件）。输入框旁的 **+ → 插件**能管理已装的插件，但添加这个市场要用命令行，把下面这段原样发送：

  > 帮我安装 bmo 项目助手插件，要真正执行安装命令，不要只改 settings.json：
  > 1. 依次运行 `claude plugin marketplace add https://gitee.com/z-null/bmo-skills-plugin-demo.git`、`claude plugin install bmo@gupo-bmo` 和 `claude plugin install ai-collab@gupo-bmo`。命令行里找不到 `claude` 的话，用 Claude 桌面应用安装目录里自带的 claude 程序执行；没有 git 就先帮我装上 git（Windows 用 winget、Mac 用 xcode-select）。
  > 2. 在用户目录 `.claude/settings.json` 的 `extraKnownMarketplaces.gupo-bmo` 里加上 `"autoUpdate": true`，以后自动更新。
  > 3. 确认用户目录 `.claude/plugins/installed_plugins.json` 里有 `bmo@gupo-bmo` 和 `ai-collab@gupo-bmo`，然后提醒我新建会话。

- **终端**（Claude Code CLI，需要已装 git）：

  ```
  /plugin marketplace add https://gitee.com/z-null/bmo-skills-plugin-demo.git
  /plugin install bmo@gupo-bmo
  /plugin install ai-collab@gupo-bmo
  ```

  再在 `/plugin` → Marketplaces → 选 `gupo-bmo` → Enable auto-update 打开自动更新。

安装时会弹确认框，命令和上面写的一致再点允许。装好后**新建一个会话**，直接说“帮我检查环境”或“帮我创建一个新项目”即可，也可以输入 `/bmo-doctor`、`/bmo-new`。

> 一条命令接入时也会跑下面的安装脚本，它只写 `~/.agents/skills` 等目录、绝不写 `~/.claude/skills`，所以 Claude Code 里不会出现两份；Claude Code 的 skill 以插件为准。

## 其他 AI 工具（Codex / Cursor / Grok / WorkBuddy / Qoder）

这些工具不装插件。**跑过「快速开始」的一条命令就已经装好了**（要有 Node 18+；没有 Node 时会跳过并提示，不影响接入协作区），新建一个会话，说“帮我检查环境”开始。

只想装 skills、不接协作区的：没有 Node 先装（Windows `winget install OpenJS.NodeJS.LTS`，Mac `brew install node@22` 或到 nodejs.org 下载），然后 `git clone https://gitee.com/z-null/bmo-skills-plugin-demo.git ~/.gupo/skills/bmo-skills-plugin-demo`，再 `node ~/.gupo/skills/bmo-skills-plugin-demo/scripts/install-skills.mjs install`（Windows 把 `~` 换成 `%USERPROFILE%`）。

### 安装脚本参考（`scripts/install-skills.mjs`）

- 默认放在 `~/.gupo/skills/bmo-skills-plugin-demo`（`~/.gupo/skills/` 用来放古珀的各个 skill 仓库，以后别的仓库也克隆到 `~/.gupo/skills/<仓库名>`）。仓库是公开的，用 https 克隆，不需要 SSH。已经有一份克隆的（比如维护者自己的工作副本），直接在那份里运行脚本即可，链接以脚本所在的仓库为准。
- 脚本自动检测装了哪些工具：总是写 `~/.agents/skills`；检测到 WorkBuddy / CodeBuddy 再写 `~/.codebuddy/skills`，检测到 Qoder 再写 `~/.qoder/skills`。也可以手动指定：`--tools codex,cursor,grok,qoder,codebuddy`。
- Mac / Linux 建软链，Windows 建目录联接（junction，不需要管理员）。工具不认链接时加 `--copy` 改成复制（复制的不会自己更新，要定期跑 `update`）。
- 同名目录已经存在、又不是脚本建的，会跳过并提示，不覆盖。装了哪些记在 `~/.agents/skills/.gupo-skills.json`，卸载只删记录里的。

| 子命令 | 做什么 |
|---|---|
| `install [--tools …] [--copy] [--dry-run]` | 安装 / 修复；重复运行只补差。`--dry-run` 只列出会做什么 |
| `update [--dry-run]` | 在仓库里 `git pull --ff-only`，再按上次的工具和方式重新链接：增补新 skill、清理已删的 skill |
| `uninstall [--dry-run]` | 只删脚本自己建的链接 / 复制，别人的不碰 |
| `status` | 看每个 skill 在每个目录的状态 |

例：`node ~/.gupo/skills/bmo-skills-plugin-demo/scripts/install-skills.mjs status`（Windows 把 `~` 换成 `%USERPROFILE%`）。

各工具读 skill 的位置：

| 工具 | 读的目录 | 脚本怎么装 |
|---|---|---|
| Claude Code | 插件市场 `gupo-bmo` | 不用脚本，见「安装」；脚本**绝不写** `~/.claude/skills` |
| Codex | `~/.agents/skills` | 总是写 |
| Cursor | `~/.agents/skills` | 总是写 |
| Grok | `~/.agents/skills` | 总是写 |
| Qoder 桌面版 | `~/.agents/skills` | 总是写 |
| Qoder IDE / CLI | `~/.qoder/skills` | 检测到 Qoder 才写，链接到 `~/.agents/skills` 里的同名目录 |
| WorkBuddy / CodeBuddy | `~/.codebuddy/skills` | 检测到才写，链接到 `~/.agents/skills` 里的同名目录 |

## 更新

- **Claude Code**：开了自动更新的，后台自动拉新版本；没开的，桌面应用对 AI 说“帮我更新 bmo 插件”（执行 `claude plugin marketplace update gupo-bmo`），终端输入 `/plugin marketplace update gupo-bmo`。
- **其他工具**（链接方式）：每个 skill 开头会先 `git pull --ff-only` 自己所在的仓库，平时不用管；仓库里新增或删掉了 skill，运行一次 `install-skills.mjs update` 补齐链接。复制方式（`--copy`）每次都要 `update`。

## 维护

- 主仓库在 Gitee（`git@gitee.com:z-null/bmo-skills-plugin-demo.git`），GitHub（`git@github.com:zch233/bmo-skills-plugin-demo.git`）只做备份。`origin` 配了两个推送地址，`git push` 一次推到两边，保持同步。新机器 clone 后要重新配：

  ```bash
  git clone git@gitee.com:z-null/bmo-skills-plugin-demo.git
  git remote set-url --add --push origin git@gitee.com:z-null/bmo-skills-plugin-demo.git
  git remote set-url --add --push origin git@github.com:zch233/bmo-skills-plugin-demo.git
  ```

- 插件没写版本号，**推送到 main 即发布**，开了自动更新的人都会拿到：在 `dev` 分支上改，验证过再合进 main。
- 发布前：`claude plugin validate .`；`node scripts/install-skills.mjs install --dry-run` 确认平铺安装没有重名、没有跳过；再实际建一次项目：`node plugins/bmo/skills/bmo-new/scripts/new-project.mjs --name t --skip-install`；发布时打 `plugin-<日期>` tag。
- **写 skill 的约束**（要让六个工具都能用）：`SKILL.md` 里不写 `${CLAUDE_PLUGIN_ROOT}` 等 `${CLAUDE_*}` 变量，脚本放在 skill 自己的目录里（如 `skills/bmo-new/scripts/`），正文写「本 skill 目录下的 `scripts/xxx`」；skill 名全仓库唯一并带前缀（平铺安装后不再有插件名区分）；skill 之间按名字引用，不写 `/插件:命令`；确认框之类说成「AI 工具」，Claude 专属的操作标明「Claude Code」。新增 skill 后，其他工具的用户要跑一次 `update`。
- 出了问题用 `git revert` 撤回再推送，不强推。
- 用到 bmo 脚本新参数的改动，等 bmo master 推送后再发布。
- `ai-collab` 插件只是薄壳：写文件的逻辑改在协作区的 `skills/collab-setup/scripts/setup.py`，协作区 `git pull` 即生效，不用发布插件；找协作区的顺序、clone 地址、SSH 公钥引导、问人的方式在 `plugins/ai-collab/skills/ai-collab-setup/scripts/bootstrap.py`，`setup.py` 的参数变了也要改它。
- **一条命令接入**：根目录 `setup.sh`（Mac / Linux）、`setup.ps1`（Windows）只检查 git / Python、克隆本仓库，然后调用 `bootstrap.py`。`bootstrap.py` 放在 skill 目录而不是根 `scripts/`，因为 Claude Code 安装插件时只把 `plugins/ai-collab` 复制进插件缓存，根目录的文件不在里面。`setup.sh`、`setup.ps1`、`bootstrap.py` 改了，**要在 Mac 和 Windows 上各实际跑一次**（交互终端一次、AI 工具里一次）。发布前先用本地覆盖变量试跑，不用推送：

  ```bash
  # 在一个临时空目录里；GUPO_SKILLS_DIR 指到临时位置，免得动到自己的 ~/.gupo
  GUPO_SKILLS_REPO=<本仓库路径> GUPO_SKILLS_DIR=/tmp/gupo-skills bash <本仓库路径>/setup.sh --dry-run
  # Windows：$env:GUPO_SKILLS_REPO='<本仓库路径>'; $env:GUPO_SKILLS_DIR="$env:TEMP\gupo-skills"; $env:GUPO_SETUP_ARGS='--dry-run'; Get-Content -Raw -Encoding UTF8 <本仓库路径>\setup.ps1 | iex
  ```

  覆盖成本地路径时克隆的是**已提交**的内容，先在 `dev` 分支提交再试；`bash -n setup.sh`、`python3 -m py_compile …/bootstrap.py` 做语法检查，有 `pwsh` 的再 `pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('setup.ps1',[ref]\$null,[ref]\$null)"`。
- `plugins/bmo/skills/bmo-new/scripts/new-project.mjs` 复刻了 `@gupo-admin/cli` 的 `new`：**cli 的建项目逻辑改了，这里要跟着改**。
- 影响使用的改动，在群里通知大家更新（命令见上）。
- 完整说明：使用见 bmo 仓库 `docs/bmo-ai-usage.md`，维护、发布与回退见 `docs/bmo-ai-maintain.md`。

## 目录

```
setup.sh                              一条命令接入（Mac / Linux）：检查 git、Python，克隆本仓库，运行 bootstrap.py
setup.ps1                             一条命令接入（Windows PowerShell），同上
.claude-plugin/marketplace.json       插件市场清单（bmo、ai-collab 两个插件，Claude Code 用）
scripts/install-skills.mjs            其他 AI 工具的安装脚本（install / update / uninstall / status）
plugins/ai-collab/
  .claude-plugin/plugin.json          插件清单
  skills/ai-collab-setup/SKILL.md     接入协作区（运行 bootstrap.py）
  skills/ai-collab-setup/scripts/bootstrap.py  接入的全部流程：找 / clone 协作区、SSH 公钥、预览、确认、调用 setup.py、装 skills
  skills/ai-collab-doctor/SKILL.md    检查协作区接入（bootstrap.py --dry-run，只检查）
plugins/bmo/
  .claude-plugin/plugin.json          插件清单
  skills/bmo-doctor/SKILL.md          检查环境
  skills/bmo-new/SKILL.md             新建项目
  skills/bmo-new/scripts/new-project.mjs  新建项目脚本（复刻 @gupo-admin/cli new 的逻辑，cli 改了这里要跟着改）
```

`new-project.mjs` 也可以单独运行：`node plugins/bmo/skills/bmo-new/scripts/new-project.mjs --name my-project [--ui] [--dir <父目录>] [--skip-install]`。
