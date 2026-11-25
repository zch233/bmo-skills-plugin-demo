#!/usr/bin/env node
/**
 * 把本仓库 plugins/<插件>/skills/<skill> 平铺安装给 Claude Code 以外的 AI 工具（Codex、Cursor、Grok、WorkBuddy/CodeBuddy、Qoder）。
 * Claude Code 不用这个脚本，继续走插件市场（README「安装」）。只用 Node 标准库。
 *
 *   node scripts/install-skills.mjs install [--tools auto|codex,cursor,grok,qoder,codebuddy] [--copy] [--dry-run]
 *   node scripts/install-skills.mjs update [--dry-run]      git pull --ff-only 后重新链接：增补新 skill、清理已删 skill
 *   node scripts/install-skills.mjs uninstall [--dry-run]   只删本脚本建的（按记录文件）
 *   node scripts/install-skills.mjs status
 *
 * 装到哪里：
 *   ~/.agents/skills/<skill>     总是写：Codex、Cursor、Grok、Qoder 桌面版读这里；链接指向本仓库的 skill 目录
 *   ~/.codebuddy/skills/<skill>  检测到 WorkBuddy / CodeBuddy（或 --tools 含 codebuddy）才写，指向 ~/.agents/skills/<skill>
 *   ~/.qoder/skills/<skill>      检测到 Qoder（或 --tools 含 qoder）才写，指向 ~/.agents/skills/<skill>
 *   绝不写 ~/.claude/skills：Claude Code 用插件，再写一份会重复。
 * Mac / Linux 用软链，Windows 用目录联接（junction，不需要管理员）；--copy 改成复制（工具不认链接时用，之后要 update 才能拿到新版）。
 * 同名目录已存在且不是本脚本建的：跳过并提示，不覆盖。装了哪些记在 ~/.agents/skills/.gupo-skills.json（按仓库名分段，~/.gupo/skills/ 下的多个 skill 仓库互不影响），卸载只按记录删。
 */
import { execFileSync, spawnSync } from 'node:child_process'
import { cpSync, existsSync, lstatSync, mkdirSync, readdirSync, readFileSync, readlinkSync, rmdirSync, rmSync, symlinkSync, unlinkSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'

const SCRIPT = fileURLToPath(import.meta.url)
const REPO = resolve(dirname(SCRIPT), '..')
const HOME = homedir()
const IS_WIN = process.platform === 'win32'
const AGENTS_DIR = join(HOME, '.agents', 'skills')
const MANIFEST = join(AGENTS_DIR, '.gupo-skills.json')
const CLAUDE_DIR = join(HOME, '.claude')
// 记录文件按仓库名分段：以后 ~/.gupo/skills/<别的仓库> 也用同一个脚本时互不影响；同名仓库换了位置（比如从别处的克隆换到 ~/.gupo/skills）算同一个
const REPO_KEY = basename(REPO)

// 额外目录：工具名 → 它读的 skills 目录。codex / cursor / grok 只读 ~/.agents/skills，没有额外目录
const EXTRA_TARGETS = {
  codebuddy: join(HOME, '.codebuddy', 'skills'),
  qoder: join(HOME, '.qoder', 'skills'),
}
const KNOWN_TOOLS = ['codex', 'cursor', 'grok', 'qoder', 'codebuddy']
const TOOL_ALIASES = { workbuddy: 'codebuddy' }

const USAGE = `用法：
  node scripts/install-skills.mjs install [--tools auto|${KNOWN_TOOLS.join(',')}] [--copy] [--dry-run]
  node scripts/install-skills.mjs update [--dry-run]
  node scripts/install-skills.mjs uninstall [--dry-run]
  node scripts/install-skills.mjs status`

const { values: opts, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    'tools': { type: 'string', default: 'auto' },
    'copy': { type: 'boolean', default: false },
    'dry-run': { type: 'boolean', default: false },
    'help': { type: 'boolean', short: 'h', default: false },
  },
})
const DRY = opts['dry-run']
const command = positionals[0]

// ---------- 工具函数 ----------

const say = message => console.log(message)
const act = message => say(DRY ? `  [dry-run] ${message}` : `  ${message}`)
const warn = message => say(`  ⚠️ ${message}`)
const tilde = p => (p === HOME || p.startsWith(HOME + sep)) ? `~${p.slice(HOME.length)}` : p

function norm(p) {
  let s = p.startsWith('\\\\?\\') ? p.slice(4) : p
  s = resolve(s)
  return IS_WIN ? s.toLowerCase() : s
}
const samePath = (a, b) => norm(a) === norm(b)
const isInside = (child, parent) => {
  const rel = relative(norm(parent), norm(child))
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

/** 任何写操作前调用：绝不碰 ~/.claude */
function guard(p) {
  if (isInside(p, CLAUDE_DIR))
    throw new Error(`拒绝写入 ${p}：Claude Code 用插件安装，本脚本不碰 ~/.claude`)
}

function lstat(p) {
  try {
    return lstatSync(p)
  }
  catch {
    return null
  }
}

function linkTarget(p) {
  try {
    return resolve(dirname(p), readlinkSync(p).replace(/^\\\\\?\\/, ''))
  }
  catch {
    return null
  }
}

function removeEntry(p, type) {
  guard(p)
  if (DRY)
    return
  if (type === 'copy') {
    rmSync(p, { recursive: true, force: true })
    return
  }
  try {
    unlinkSync(p)
  }
  catch (error) {
    // Windows 的目录联接有时要用 rmdir 删（只删联接本身，不动目标内容）
    if (IS_WIN)
      rmdirSync(p)
    else
      throw error
  }
}

function createEntry(p, target, type) {
  guard(p)
  if (DRY)
    return
  mkdirSync(dirname(p), { recursive: true })
  if (type === 'copy')
    cpSync(target, p, { recursive: true, dereference: true })
  else
    symlinkSync(target, p, IS_WIN ? 'junction' : 'dir')
}

function readManifestFile() {
  try {
    const data = JSON.parse(readFileSync(MANIFEST, 'utf8'))
    return data && typeof data.repos === 'object' ? data : { repos: {} }
  }
  catch {
    return { repos: {} }
  }
}

/** 本仓库那一段记录；没有返回 null */
function readManifest() {
  const data = readManifestFile().repos[REPO_KEY]
  return data ? { ...data, entries: Array.isArray(data.entries) ? data.entries : [] } : null
}

/** 写本仓库那一段；传 null 删掉这一段，全空了删文件 */
function writeManifest(section) {
  guard(MANIFEST)
  if (DRY)
    return
  const data = readManifestFile()
  if (section)
    data.repos[REPO_KEY] = section
  else
    delete data.repos[REPO_KEY]
  if (!Object.keys(data.repos).length) {
    rmSync(MANIFEST, { force: true })
    return
  }
  mkdirSync(AGENTS_DIR, { recursive: true })
  writeFileSync(MANIFEST, `${JSON.stringify(data, null, 2)}\n`)
}

/** 本仓库 plugins/*\/skills/* 里带 SKILL.md 的目录 */
function discoverSkills() {
  const skills = []
  const pluginsDir = join(REPO, 'plugins')
  for (const plugin of readdirSync(pluginsDir, { withFileTypes: true })) {
    if (!plugin.isDirectory())
      continue
    const skillsDir = join(pluginsDir, plugin.name, 'skills')
    if (!existsSync(skillsDir))
      continue
    for (const skill of readdirSync(skillsDir, { withFileTypes: true })) {
      if (skill.isDirectory() && existsSync(join(skillsDir, skill.name, 'SKILL.md')))
        skills.push({ name: skill.name, plugin: plugin.name, src: join(skillsDir, skill.name) })
    }
  }
  const seen = new Map()
  for (const s of skills) {
    if (seen.has(s.name))
      throw new Error(`skill 重名：${seen.get(s.name)}/${s.name} 和 ${s.plugin}/${s.name}，平铺安装会冲突，先改名`)
    seen.set(s.name, s.plugin)
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name))
}

function onPath(cmd) {
  const r = spawnSync(IS_WIN ? 'where' : 'which', [cmd], { stdio: 'ignore' })
  return r.status === 0
}

function detectTools() {
  const local = process.env.LOCALAPPDATA || join(HOME, 'AppData', 'Local')
  const appDirs = process.platform === 'darwin'
    ? ['/Applications', join(HOME, 'Applications')]
    : IS_WIN ? [join(local, 'Programs')] : []
  const apps = appDirs.flatMap((d) => {
    try {
      return readdirSync(d).map(n => n.toLowerCase())
    }
    catch {
      return []
    }
  })
  // 应用名可能带后缀，如「WorkBuddy AI.app」，按前缀匹配
  const app = name => apps.some(n => n.startsWith(name.toLowerCase()))
  return {
    codex: existsSync(join(HOME, '.codex')) || onPath('codex'),
    cursor: existsSync(join(HOME, '.cursor')) || app('Cursor') || onPath('cursor'),
    grok: existsSync(join(HOME, '.grok')) || onPath('grok'),
    codebuddy: existsSync(join(HOME, '.codebuddy')) || existsSync(join(HOME, '.workbuddy'))
      || app('WorkBuddy') || app('CodeBuddy') || onPath('codebuddy'),
    qoder: existsSync(join(HOME, '.qoder')) || app('Qoder') || onPath('qoder') || onPath('qodercli'),
  }
}

/** --tools 解析成要写的额外目录（codebuddy / qoder）；auto 按检测结果 */
function resolveTools(spec) {
  if (!spec || spec === 'auto') {
    const found = detectTools()
    return { requested: 'auto', tools: KNOWN_TOOLS.filter(t => found[t]) }
  }
  const tools = [...new Set(spec.split(',').map(t => t.trim().toLowerCase()).filter(Boolean).map(t => TOOL_ALIASES[t] || t))]
  const unknown = tools.filter(t => !KNOWN_TOOLS.includes(t))
  if (unknown.length)
    throw new Error(`不认识的工具：${unknown.join(', ')}（可选 auto 或 ${KNOWN_TOOLS.join(',')}）`)
  return { requested: tools.join(','), tools }
}

/** 想要的全部条目：~/.agents/skills 指向仓库，额外目录指向 ~/.agents/skills 里的同名目录（复制模式都从仓库复制） */
function desiredEntries(skills, tools, type) {
  const entries = []
  for (const s of skills) {
    const main = join(AGENTS_DIR, s.name)
    entries.push({ skill: s.name, path: main, target: s.src, type, primary: true })
    for (const tool of tools) {
      if (EXTRA_TARGETS[tool])
        entries.push({ skill: s.name, path: join(EXTRA_TARGETS[tool], s.name), target: type === 'copy' ? s.src : main, type, primary: false, dependsOn: main })
    }
  }
  return entries
}

/**
 * 路径现在的状态：
 *   missing  不存在
 *   ours     本脚本建的（记录里有且类型对得上；或者是指向本仓库 / ~/.agents/skills 里我方条目的链接）
 *   foreign  别人的，不碰
 */
function ownership(p, manifestEntries, expectedTarget) {
  const st = lstat(p)
  if (!st)
    return { state: 'missing' }
  const recorded = manifestEntries.find(e => samePath(e.path, p))
  if (st.isSymbolicLink()) {
    const target = linkTarget(p)
    if (target && ((recorded && recorded.type !== 'copy' && samePath(target, recorded.target))
      || samePath(target, expectedTarget) || isInside(target, join(REPO, 'plugins'))))
      return { state: 'ours', type: 'link', target }
    return { state: 'foreign', why: `是指向 ${tilde(target || '?')} 的链接` }
  }
  if (recorded && recorded.type === 'copy' && st.isDirectory())
    return { state: 'ours', type: 'copy' }
  return { state: 'foreign', why: st.isDirectory() ? '是已有的目录' : '是已有的文件' }
}

// ---------- 子命令 ----------

function install() {
  const skills = discoverSkills()
  const { requested, tools } = resolveTools(opts.tools)
  const type = opts.copy ? 'copy' : 'link'
  const manifest = readManifest()
  const old = manifest?.entries || []

  say(`仓库：${tilde(REPO)}`)
  say(`skill：${skills.map(s => s.name).join('、')}`)
  say(`工具：${tools.length ? tools.join('、') : '（没检测到，只写 ~/.agents/skills）'}${requested === 'auto' ? '（自动检测）' : ''}`)
  say(`方式：${type === 'copy' ? '复制' : IS_WIN ? '目录联接' : '软链'}`)
  const dirs = [AGENTS_DIR, ...tools.filter(t => EXTRA_TARGETS[t]).map(t => EXTRA_TARGETS[t])]
  say(`写入：${dirs.map(tilde).join('、')}`)
  say('')

  const desired = desiredEntries(skills, tools, type)
  const installed = []
  const skippedPrimary = new Set()
  let changed = 0

  for (const e of desired) {
    if (!e.primary && skippedPrimary.has(e.dependsOn)) {
      warn(`跳过 ${tilde(e.path)}：${tilde(e.dependsOn)} 不是本脚本装的`)
      continue
    }
    const own = ownership(e.path, old, e.target)
    if (own.state === 'foreign') {
      warn(`跳过 ${tilde(e.path)}：${own.why}，不是本脚本建的。要用本仓库的版本，先自己移走它再重跑`)
      if (e.primary)
        skippedPrimary.add(e.path)
      continue
    }
    if (own.state === 'ours') {
      if (own.type === 'link' && e.type === 'link' && own.target && samePath(own.target, e.target)) {
        installed.push(e)
        continue
      }
      removeEntry(e.path, own.type)
      createEntry(e.path, e.target, e.type)
      act(`${e.type === 'copy' ? '刷新' : '重建'} ${tilde(e.path)} → ${tilde(e.target)}`)
    }
    else {
      createEntry(e.path, e.target, e.type)
      act(`${e.type === 'copy' ? '复制' : '链接'} ${tilde(e.path)} → ${tilde(e.target)}`)
    }
    changed++
    installed.push(e)
  }

  // 清理：记录里有、这次不需要的（skill 已删、工具不再选），还是我方的才删；先删额外目录再删主目录
  const keep = new Set(desired.map(e => norm(e.path)))
  const stale = old.filter(e => !keep.has(norm(e.path))).sort((a, b) => Number(a.primary) - Number(b.primary))
  for (const e of stale) {
    const own = ownership(e.path, old, e.target)
    if (own.state === 'ours') {
      removeEntry(e.path, own.type)
      act(`删除 ${tilde(e.path)}（${skills.some(s => s.name === e.skill) ? '这次没选这个工具' : `仓库里已没有 ${e.skill}`}）`)
      changed++
    }
  }

  writeManifest({
    repo: REPO,
    mode: type,
    tools: requested,
    updatedAt: new Date().toISOString(),
    entries: installed.map(({ skill, path, target, type, primary }) => ({ skill, path, target, type, primary })),
  })

  say('')
  say(changed ? `${DRY ? '预计改动' : '完成'}：${changed} 项${DRY ? '（dry-run，没有写入）' : ''}` : '已是最新，没有改动')
  if (!DRY)
    say('接下来：新开一个 AI 工具会话，说「帮我检查环境」（bmo-doctor）或「接入协作区」（ai-collab-setup）。')
}

function update() {
  const manifest = readManifest()
  if (DRY) {
    say(`[dry-run] 会运行：git -C ${tilde(REPO)} pull --ff-only`)
  }
  else {
    say(`拉取最新：git -C ${tilde(REPO)} pull --ff-only`)
    try {
      execFileSync('git', ['-C', REPO, 'pull', '--ff-only'], { stdio: 'inherit' })
    }
    catch {
      warn('拉取失败（没网、有本地改动或分叉），按当前版本重新链接')
    }
  }
  if (manifest?.repo && !samePath(manifest.repo, REPO))
    warn(`上次是从 ${tilde(manifest.repo)} 装的，这次改为指向 ${tilde(REPO)}`)
  // 用拉取后的新脚本重新安装，沿用上次的工具和方式
  const args = [SCRIPT, 'install', '--tools', manifest?.tools || 'auto']
  if (manifest?.mode === 'copy')
    args.push('--copy')
  if (DRY)
    args.push('--dry-run')
  say('')
  const r = spawnSync(process.execPath, args, { stdio: 'inherit' })
  process.exit(r.status ?? 1)
}

function uninstall() {
  const manifest = readManifest()
  if (!manifest) {
    say(`记录文件 ${tilde(MANIFEST)} 里没有 ${REPO_KEY} 的记录，没有可卸载的（本脚本只删自己记录过的）`)
    return
  }
  const entries = [...manifest.entries].sort((a, b) => Number(a.primary) - Number(b.primary))
  let removed = 0
  for (const e of entries) {
    const own = ownership(e.path, manifest.entries, e.target)
    if (own.state === 'ours') {
      removeEntry(e.path, own.type)
      act(`删除 ${tilde(e.path)}`)
      removed++
    }
    else if (own.state === 'foreign') {
      warn(`保留 ${tilde(e.path)}：${own.why}，已不是本脚本建的`)
    }
  }
  writeManifest(null)
  act(`删除记录文件里 ${REPO_KEY} 这一段（别的仓库的记录保留）`)
  say(`\n${DRY ? '预计删除' : '已删除'} ${removed} 项。Claude Code 的插件不受影响（要卸载用 claude plugin uninstall）。`)
}

function status() {
  const skills = discoverSkills()
  const manifest = readManifest()
  const found = detectTools()
  say(`仓库：${tilde(REPO)}`)
  try {
    const head = execFileSync('git', ['-C', REPO, 'log', '-1', '--format=%h %cd', '--date=short'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim()
    say(`版本：${head}`)
  }
  catch {}
  say(`检测到的工具：${KNOWN_TOOLS.filter(t => found[t]).join('、') || '无'}`)
  if (!manifest) {
    say(`记录：${tilde(MANIFEST)} 里没有 ${REPO_KEY}，还没用本脚本安装过`)
  }
  else {
    say(`记录：${tilde(MANIFEST)} → ${REPO_KEY}（${manifest.mode === 'copy' ? '复制' : '链接'}，工具 ${manifest.tools}，${manifest.updatedAt}）`)
    if (manifest.repo && !samePath(manifest.repo, REPO))
      warn(`记录里的仓库是 ${tilde(manifest.repo)}，和当前仓库不同；在当前仓库运行 install 会改为指向这里`)
  }
  const tools = manifest ? resolveTools(manifest.tools).tools : []
  const desired = desiredEntries(skills, tools, manifest?.mode || 'link')
  const old = manifest?.entries || []
  say('')
  for (const e of desired) {
    const own = ownership(e.path, old, e.target)
    let state
    if (own.state === 'missing')
      state = '❌ 未安装'
    else if (own.state === 'foreign')
      state = `⚠️ 被占用（${own.why}）`
    else if (own.type === 'copy')
      state = '✅ 已安装（复制）'
    else if (!existsSync(e.path))
      state = `❌ 链接断了（→ ${tilde(own.target || '?')}）`
    else if (own.target && samePath(own.target, e.target))
      state = '✅ 已安装'
    else
      state = `⚠️ 指向旧位置 ${tilde(own.target || '?')}，运行 install 修正`
    say(`  ${state.padEnd(10)} ${tilde(e.path)}`)
  }
  const keep = new Set(desired.map(e => norm(e.path)))
  for (const e of old.filter(e => !keep.has(norm(e.path))))
    say(`  ⚠️ 多余     ${tilde(e.path)}（仓库里已没有 ${e.skill}，运行 update 清理）`)
}

// ---------- 入口 ----------

try {
  if (opts.help || !command) {
    say(USAGE)
    process.exit(command || opts.help ? 0 : 1)
  }
  const commands = { install, update, uninstall, status }
  if (!commands[command]) {
    say(`不认识的子命令：${command}\n\n${USAGE}`)
    process.exit(1)
  }
  commands[command]()
}
catch (error) {
  console.error(`✖ ${error.message}`)
  process.exit(1)
}
