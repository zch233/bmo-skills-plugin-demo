#!/usr/bin/env node
import { execFileSync } from 'node:child_process'
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import process from 'node:process'
import { parseArgs } from 'node:util'

/**
 * 新建一个接入 bmo 的项目，等价于：
 *   npx @gupo-admin/cli@latest new（项目名 + master 分支）
 *   git remote add bmo ... && git fetch bmo && git cherry-pick <docs 初始提交>..bmo/docs
 *   补齐 bmo:* 命令 → pnpm bmo:init（拉子模块后 bmo:update 到最新 master，并同步 bmo 的 skill）→ 设置默认病种
 *   pnpm install
 * bmo 每天在更新，模板分支里的 bmo 版本可能滞后，统一靠 bmo:update 拿最新。
 *
 * cli 的 new 是交互式的，AI 跑不了，所以这里照着 cli（@gupo-admin/cli 0.3.0 的 createProject）复刻了一份；
 * cli 的建项目逻辑改了，这里要跟着改。
 *
 * node new-project.mjs --name my-project [--title "系统中文名"] [--ui] [--dir <父目录>] [--disease "糖尿病 DM SLOW_DM"] [--skip-install]
 *   --resume   接入 bmo 时有冲突停下来了：解决冲突、git add 后，用同样的参数加 --resume 再跑一次，接着做完剩下的步骤
 *   --title    系统中文名，写进 env/.env 的 VITE_APP_NAME（浏览器标签标题、页头 / 侧边栏的系统名）；不传保留模板的 Gupo-Admin
 *   --ui       用新 UI 模板（bmo 的 docs-ui 分支），默认 docs 分支
 *   --disease  默认病种，交给 bmo 的 bmo-disease 脚本：“场景名称 基线编号 场景编码”（必须和智元矩阵病种场景表一致），
 *              清单里只有一条的也可以只写场景名称；不传就是糖尿病 DM SLOW_DM
 */

const TEMPLATE_REPO = 'git@codeup.aliyun.com:gupo/rd-frontend/dev/dev-business-kits-docs.git'
// BMO_REPO 环境变量可指向别的仓库，用来在推送前验证模板分支
const BMO_REPO = process.env.BMO_REPO || 'git@codeup.aliyun.com:gupo/rd-frontend/bmo/bmo-business-pc.git'

const { values } = parseArgs({
  options: {
    'name': { type: 'string' },
    'title': { type: 'string' },
    'ui': { type: 'boolean', default: false },
    'dir': { type: 'string', default: process.cwd() },
    'disease': { type: 'string', default: '糖尿病 DM SLOW_DM' },
    'skip-install': { type: 'boolean', default: false },
    'resume': { type: 'boolean', default: false },
  },
})

// 宿主要有的 bmo 命令；模板分支可能还没加齐或是旧写法，建项目时补上 / 改成这样
const BMO_SCRIPTS = {
  'bmo:init': 'git submodule update --init && pnpm bmo:update',
  'bmo:update': 'git submodule update --remote --recursive && pnpm bmo:skills',
  'bmo:add': 'node packages/bmo-business-pc/scripts/bmo-add.mjs',
  'bmo:skills': 'node packages/bmo-business-pc/scripts/bmo-skills.mjs',
  'bmo:disease': 'node packages/bmo-business-pc/scripts/bmo-disease.mjs',
  'bmo:login': 'node packages/bmo-business-pc/scripts/bmo-login.mjs',
  'bmo:release': 'node packages/bmo-business-pc/scripts/bmo-release.mjs',
}

let step = 0
const TOTAL = values['skip-install'] ? 4 : 5
const log = message => console.log(`\n[${++step}/${TOTAL}] ${message}`)
const run = (cmd, args, cwd) => execFileSync(cmd, args, { cwd, stdio: 'inherit', shell: process.platform === 'win32' })
const output = (cmd, args, cwd) => execFileSync(cmd, args, { cwd, encoding: 'utf8', shell: process.platform === 'win32' }).trim()

function fail(message) {
  console.error(`\n✖ ${message}`)
  process.exit(1)
}

/** 只解析 pnpm-workspace.yaml 里的 catalog 段（key: version），不引第三方 yaml 库 */
function parseCatalog(text) {
  const catalog = {}
  let inCatalog = false
  for (const line of text.split(/\r?\n/)) {
    if (/^\S/.test(line))
      inCatalog = line.trim() === 'catalog:'
    else if (inCatalog && line.trim()) {
      const match = line.trim().match(/^['"]?([^'":]+)['"]?\s*:\s*['"]?([^'"]+)['"]?$/)
      if (match)
        catalog[match[1]] = match[2]
    }
  }
  return catalog
}

function createFromTemplate(name, projectPath) {
  const temp = mkdtempSync(join(tmpdir(), 'bmo-new-'))
  try {
    run('git', ['clone', '--depth', '1', '--branch', 'master', TEMPLATE_REPO, temp])
    cpSync(join(temp, 'app'), projectPath, { recursive: true })

    const readJson = file => JSON.parse(readFileSync(file, 'utf8'))
    const compVersion = readJson(join(temp, 'components/package.json')).version
    const cliVersion = readJson(join(temp, 'packages/cli/package.json')).version
    const catalog = parseCatalog(readFileSync(join(temp, 'pnpm-workspace.yaml'), 'utf8'))

    const pkgPath = join(projectPath, 'package.json')
    const pkg = readJson(pkgPath)
    pkg.name = name
    pkg.version = '0.1.0'
    pkg.dependencies['@gupo-admin/components'] = compVersion
    pkg.devDependencies['@gupo-admin/cli'] = cliVersion
    pkg.devDependencies['@gupo-admin/skills'] = compVersion
    pkg.scripts ??= {}
    if (!pkg.scripts.postinstall)
      pkg.scripts.postinstall = 'gupo-admin skills sync --silent || true'
    else if (!pkg.scripts.postinstall.includes('skills sync'))
      pkg.scripts.postinstall = `${pkg.scripts.postinstall} && gupo-admin skills sync --silent || true`
    for (const key in catalog) {
      if (pkg.dependencies[key])
        pkg.dependencies[key] = catalog[key]
      else if (pkg.devDependencies[key])
        pkg.devDependencies[key] = catalog[key]
    }
    writeFileSync(pkgPath, JSON.stringify(pkg, null, 2))

    const envPath = join(projectPath, 'env/.env')
    writeFileSync(envPath, readFileSync(envPath, 'utf8').replace(/VITE_APP_STORAGE_KEY=(.*)/, `VITE_APP_STORAGE_KEY=${name}`))
    cpSync(join(temp, 'packages/cli/templates/ai-starter'), projectPath, { recursive: true })
  }
  finally {
    rmSync(temp, { recursive: true, force: true })
  }
}

/** 两边都有的字段以模板（ours）为准，只把 bmo 分支（theirs）新增的字段补进来 */
function mergePackageJson(ours, theirs) {
  const merged = structuredClone(ours)
  for (const [key, value] of Object.entries(theirs)) {
    if (!(key in merged))
      merged[key] = value
    else if (value && typeof value === 'object' && !Array.isArray(value) && typeof merged[key] === 'object')
      merged[key] = mergePackageJson(merged[key], value)
  }
  return merged
}

/**
 * bmo 模板分支是在旧模板上做的，模板迭代后可能冲突。bmo 分支已经把 bmo:* 命令放在 scripts 中间（放末尾会和 cli 追加的
 * postinstall 撞同一行），一般不会冲突；万一 package.json 冲突就按 JSON 合并兜底，其他文件冲突停下来交给人/AI。
 */
function cherryPick(args, cwd) {
  // 摘到一半（有 sequencer 或 CHERRY_PICK_HEAD）就一直处理到摘完：package.json 冲突自动合并，
  // 解决后变成空提交的跳过，其他冲突停下来交给人 / AI，之后 --resume 从这里接着来
  const inProgress = () => existsSync(join(cwd, '.git/sequencer')) || existsSync(join(cwd, '.git/CHERRY_PICK_HEAD'))
  const CONTINUE = ['-c', 'core.editor=true', 'cherry-pick', '--continue']
  let next = args
  for (let round = 0; round < 500; round++) {
    try {
      run('git', next, cwd)
    }
    catch {}
    if (!inProgress())
      return
    const conflicts = output('git', ['diff', '--name-only', '--diff-filter=U'], cwd).split('\n').filter(Boolean)
    if (conflicts.some(file => file !== 'package.json')) {
      fail([
        `接入 bmo 时有冲突：${conflicts.join('、')}（项目在 ${cwd}）。`,
        '解决：两边改动都保留，同一处以模板（HEAD）为准、补上 bmo 新增的内容；解决完 git add 这些文件，',
        '然后用同样的参数加 --resume 再运行本脚本，会接着做完剩下的步骤（不要手动 git cherry-pick --continue）。',
        '这说明 bmo 的模板分支和最新模板有冲突，请转告 bmo 维护者更新 docs / docs-ui 分支。',
      ].join('\n'))
    }
    if (conflicts.length) {
      const ours = JSON.parse(output('git', ['show', ':2:package.json'], cwd))
      const theirs = JSON.parse(output('git', ['show', ':3:package.json'], cwd))
      writeFileSync(join(cwd, 'package.json'), `${JSON.stringify(mergePackageJson(ours, theirs), null, 2)}\n`)
      run('git', ['add', 'package.json'], cwd)
      console.log('package.json 冲突已按 JSON 合并（模板字段优先，补上 bmo 新增的命令和依赖）')
    }
    let staged = true
    try {
      run('git', ['diff', '--cached', '--quiet'], cwd)
      staged = false
    }
    catch {}
    // 冲突按模板解决后这个提交可能已经没有改动了，跳过它接着摘下一个
    next = !staged && existsSync(join(cwd, '.git/CHERRY_PICK_HEAD')) ? ['cherry-pick', '--skip'] : CONTINUE
  }
  fail(`接入 bmo 的 cherry-pick 一直没完成，项目在 ${cwd}，请检查 git status`)
}

/** 已有的 bmo:* 命令原位改成 BMO_SCRIPTS 的写法，缺的补在已有 bmo:* 后面（不放 scripts 末尾） */
function ensureBmoScripts(pkgPath) {
  const text = readFileSync(pkgPath, 'utf8')
  const pkg = JSON.parse(text)
  const entries = Object.entries(pkg.scripts ?? {}).map(([key, value]) => [key, BMO_SCRIPTS[key] ?? value])
  const missing = Object.entries(BMO_SCRIPTS).filter(([key]) => !(key in (pkg.scripts ?? {})))
  const anchor = entries.findLastIndex(([key]) => key.startsWith('bmo:'))
  entries.splice(anchor >= 0 ? anchor + 1 : entries.findIndex(([key]) => key === 'dev') + 1, 0, ...missing)
  pkg.scripts = Object.fromEntries(entries)
  writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + (text.endsWith('\n') ? '\n' : ''))
}

function main() {
  const name = values.name
  if (!name || !/^[\w.-]+$/.test(name))
    fail('请用 --name 指定项目名称（字母、数字、- _ .）')
  const projectPath = resolve(values.dir, name)
  if (!output('git', ['config', 'user.name']) || !output('git', ['config', 'user.email']))
    fail('git 还没配置 user.name / user.email，先运行 /bmo:doctor')
  const branch = values.ui ? 'docs-ui' : 'docs'

  if (values.resume) {
    if (!existsSync(join(projectPath, '.git')))
      fail(`--resume 要接着已经开始的项目，但 ${projectPath} 不是 git 项目`)
    const unresolved = output('git', ['diff', '--name-only', '--diff-filter=U'], projectPath)
    if (unresolved)
      fail(`还有没解决的冲突：${unresolved.split('\n').join('、')}，解决后 git add 再 --resume`)
    step = 1
    log(`接着接入 bmo（${branch} 分支）`)
    // 摘到一半就继续；已经摘完时 --continue 会报“没有进行中的 cherry-pick”，进冲突检查后直接返回
    cherryPick(['-c', 'core.editor=true', 'cherry-pick', '--continue'], projectPath)
  }
  else {
    if (existsSync(projectPath))
      fail(`目录已存在：${projectPath}（接入 bmo 冲突后继续，加 --resume）`)
    log(`从模板创建项目 ${name}`)
    mkdirSync(projectPath, { recursive: true })
    createFromTemplate(name, projectPath)
    run('git', ['init', '--initial-branch=master'], projectPath)
    run('git', ['add', '.'], projectPath)
    run('git', ['commit', '-q', '-m', 'chore: init'], projectPath)

    log(`接入 bmo（${branch} 分支）`)
    run('git', ['remote', 'add', 'bmo', BMO_REPO], projectPath)
    run('git', ['fetch', 'bmo', branch], projectPath)
    // 摘 bmo 模板分支在它自己 init 之后的全部提交；只摘 bmo/docs 会漏掉前面的提交
    const root = output('git', ['rev-list', '--max-parents=0', `bmo/${branch}`], projectPath).split('\n')[0]
    cherryPick(['cherry-pick', `${root}..bmo/${branch}`], projectPath)
  }

  log('拉取 bmo 并更新到最新（pnpm bmo:init）')
  ensureBmoScripts(join(projectPath, 'package.json'))
  run('pnpm', ['bmo:init'], projectPath)

  log('设置默认病种和系统名称')
  if (existsSync(join(projectPath, 'packages/bmo-business-pc/scripts/bmo-disease.mjs'))) {
    try {
      run('node', ['packages/bmo-business-pc/scripts/bmo-disease.mjs', ...values.disease.trim().split(/\s+/)], projectPath)
    }
    catch {
      console.log('病种没设置成功（见上面的提示，三项要和智元矩阵病种场景表一致），项目照常创建，之后用 bmo-disease 再设置')
    }
  }
  else {
    console.log('当前 bmo 版本还没有 bmo-disease 脚本，跳过')
  }
  if (values.title) {
    const envPath = join(projectPath, 'env/.env')
    const env = readFileSync(envPath, 'utf8')
    const title = values.title.replace(/[\r\n]/g, ' ').trim()
    writeFileSync(envPath, /^VITE_APP_NAME=.*$/m.test(env) ? env.replace(/^VITE_APP_NAME=.*$/m, `VITE_APP_NAME=${title}`) : `${env.trimEnd()}\nVITE_APP_NAME=${title}\n`)
    console.log(`系统名称已设为：${title}（env/.env 的 VITE_APP_NAME）`)
  }
  run('git', ['add', 'packages/bmo-business-pc', 'package.json', 'src/router/index.ts', 'env/.env'], projectPath)
  try {
    run('git', ['diff', '--cached', '--quiet'], projectPath)
  }
  catch {
    run('git', ['commit', '-q', '-m', 'chore: 更新 bmo 到最新，补齐 bmo 命令，设置默认病种和系统名称'], projectPath)
  }

  if (!values['skip-install']) {
    log('安装依赖（pnpm install）')
    run('pnpm', ['install'], projectPath)
  }

  const pkg = JSON.parse(readFileSync(join(projectPath, 'package.json'), 'utf8'))

  console.log(`\n✔ 项目已创建：${projectPath}`)
  console.log(`  启动：cd ${name} && pnpm dev${pkg.scripts?.dev ? `（${pkg.scripts.dev}）` : ''}`)
}

main()
