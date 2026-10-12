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
 *   pnpm install && pnpm bmo:init
 *
 * cli 的 new 是交互式的，AI 跑不了，所以这里照着 cli（@gupo-admin/cli 0.3.0 的 createProject）复刻了一份；
 * cli 的建项目逻辑改了，这里要跟着改。
 *
 * node new-project.mjs --name my-project [--ui] [--dir <父目录>] [--skip-install]
 *   --ui  用新 UI 模板（bmo 的 docs-ui 分支），默认 docs 分支
 */

const TEMPLATE_REPO = 'git@codeup.aliyun.com:gupo/rd-frontend/dev/dev-business-kits-docs.git'
const BMO_REPO = 'git@codeup.aliyun.com:gupo/rd-frontend/bmo/bmo-business-pc.git'

const { values } = parseArgs({
  options: {
    'name': { type: 'string' },
    'ui': { type: 'boolean', default: false },
    'dir': { type: 'string', default: process.cwd() },
    'skip-install': { type: 'boolean', default: false },
  },
})

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
 * 模板一直在迭代，bmo 分支是在旧模板上做的，package.json 几乎每次都冲突（模板加了 postinstall、bmo 加了 bmo:* 命令），
 * 这种按 JSON 合并自动解决；其他文件冲突就停下来交给人/AI。
 */
function cherryPick(args, cwd) {
  try {
    run('git', args, cwd)
    return
  }
  catch {}
  while (true) {
    const conflicts = output('git', ['diff', '--name-only', '--diff-filter=U'], cwd).split('\n').filter(Boolean)
    if (!conflicts.length)
      return
    if (conflicts.some(file => file !== 'package.json'))
      fail(`cherry-pick 有冲突：${conflicts.join('、')}。项目在 ${cwd}，解决后 git add 并 git cherry-pick --continue，再执行 git submodule update --init 和 pnpm install`)
    const ours = JSON.parse(output('git', ['show', ':2:package.json'], cwd))
    const theirs = JSON.parse(output('git', ['show', ':3:package.json'], cwd))
    writeFileSync(join(cwd, 'package.json'), `${JSON.stringify(mergePackageJson(ours, theirs), null, 2)}\n`)
    run('git', ['add', 'package.json'], cwd)
    console.log('package.json 冲突已按 JSON 合并（模板字段优先，补上 bmo 新增的命令和依赖）')
    try {
      run('git', ['-c', 'core.editor=true', 'cherry-pick', '--continue'], cwd)
      return
    }
    catch {}
  }
}

function main() {
  const name = values.name
  if (!name || !/^[\w.-]+$/.test(name))
    fail('请用 --name 指定项目名称（字母、数字、- _ .）')
  const projectPath = resolve(values.dir, name)
  if (existsSync(projectPath))
    fail(`目录已存在：${projectPath}`)
  if (!output('git', ['config', 'user.name']) || !output('git', ['config', 'user.email']))
    fail('git 还没配置 user.name / user.email，先运行 /bmo:doctor')

  log(`从模板创建项目 ${name}`)
  mkdirSync(projectPath, { recursive: true })
  createFromTemplate(name, projectPath)
  run('git', ['init', '--initial-branch=master'], projectPath)
  run('git', ['add', '.'], projectPath)
  run('git', ['commit', '-q', '-m', 'chore: init'], projectPath)

  const branch = values.ui ? 'docs-ui' : 'docs'
  log(`接入 bmo（${branch} 分支）`)
  run('git', ['remote', 'add', 'bmo', BMO_REPO], projectPath)
  run('git', ['fetch', 'bmo', branch], projectPath)
  // 摘 bmo 模板分支在它自己 init 之后的全部提交；只摘 bmo/docs 会漏掉前面的提交
  const root = output('git', ['rev-list', '--max-parents=0', `bmo/${branch}`], projectPath).split('\n')[0]
  cherryPick(['cherry-pick', `${root}..bmo/${branch}`], projectPath)

  log('拉取 bmo 子模块')
  run('git', ['submodule', 'update', '--init'], projectPath)

  if (!values['skip-install']) {
    log('安装依赖（pnpm install）')
    run('pnpm', ['install'], projectPath)
  }

  log('同步 bmo 的 AI skill')
  const pkg = JSON.parse(readFileSync(join(projectPath, 'package.json'), 'utf8'))
  if (existsSync(join(projectPath, 'packages/bmo-business-pc/scripts/bmo-skills.mjs')))
    run('node', ['packages/bmo-business-pc/scripts/bmo-skills.mjs'], projectPath)
  else
    console.log('当前 bmo 版本还没有 bmo-skills 脚本，跳过')

  console.log(`\n✔ 项目已创建：${projectPath}`)
  console.log(`  启动：cd ${name} && pnpm dev${pkg.scripts?.dev ? `（${pkg.scripts.dev}）` : ''}`)
}

main()
