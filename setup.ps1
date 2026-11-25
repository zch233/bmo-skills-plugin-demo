# 古珀协作区一条命令接入（Windows PowerShell 5.1 / PowerShell 7；Mac / Linux 用 setup.sh）。在项目目录执行：
#   irm https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.ps1 | iex
# 要带参数时（irm | iex 传不了参数），二选一：
#   & ([scriptblock]::Create((irm https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.ps1))) --type tester
#   $env:GUPO_SETUP_ARGS = '--type tester'; irm https://gitee.com/z-null/bmo-skills-plugin-demo/raw/main/setup.ps1 | iex
#
# 本文件是薄壳，只做三件事，其余逻辑都在 bootstrap.py：
#   1. 检查 git、Python 3.8+，缺了用 winget 装（Git.Git / Python.Python.3.12），装不了就说明去哪下载
#   2. 把插件仓库 https 克隆到 ~\.gupo\skills\bmo-skills-plugin-demo，已有就 git pull --ff-only
#   3. 运行仓库里的 plugins\ai-collab\skills\ai-collab-setup\scripts\bootstrap.py，参数原样透传
#
# 本地试跑可覆盖：$env:GUPO_SKILLS_REPO（插件仓库地址，可以是本地路径）、$env:GUPO_SKILLS_DIR（克隆位置）。
# 本地文件试跑用 pwsh，或 Get-Content -Raw -Encoding UTF8 .\setup.ps1 | iex（PowerShell 5.1 直接运行无 BOM 的文件会按 GBK 读）。
# iex 在用户当前的 PowerShell 会话里执行：不能用 exit（会关掉窗口），出错一律 return，退出码放在 $LASTEXITCODE。

$GupoSetupArgs = @($args)

function Invoke-GupoSetup {
    param([string[]]$PassArgs)

    $ErrorActionPreference = 'Continue'
    # Python 子进程输出 UTF-8；用完恢复，iex 跑在用户自己的会话里，不留副作用
    $oldEncoding = $null
    try { $oldEncoding = [Console]::OutputEncoding; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
    try {
        Invoke-GupoSetupSteps -PassArgs $PassArgs
    } finally {
        if ($oldEncoding) { try { [Console]::OutputEncoding = $oldEncoding } catch {} }
    }
}

function Invoke-GupoSetupSteps {
    param([string[]]$PassArgs)

    $repo = if ($env:GUPO_SKILLS_REPO) { $env:GUPO_SKILLS_REPO } else { 'https://gitee.com/z-null/bmo-skills-plugin-demo.git' }
    $dir = if ($env:GUPO_SKILLS_DIR) { $env:GUPO_SKILLS_DIR } else { Join-Path $HOME '.gupo\skills\bmo-skills-plugin-demo' }
    $rel = 'plugins\ai-collab\skills\ai-collab-setup\scripts\bootstrap.py'
    $hasWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)

    function Update-SessionPath {
        # winget 装完只改了注册表，把新的 PATH 读进当前会话，省得重开窗口
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    }

    function Test-Git {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) { return $false }
        $null = & git --version 2>$null
        return ($LASTEXITCODE -eq 0)
    }

    function Find-Python {
        # 逐个试 py -3 / python / python3，真跑一次取版本号：Microsoft Store 的 python 占位程序跑不出版本号，会被排除
        foreach ($cand in @(@('py', '-3'), @('python'), @('python3'))) {
            if (-not (Get-Command $cand[0] -ErrorAction SilentlyContinue)) { continue }
            $pre = @($cand | Select-Object -Skip 1)
            try {
                $ver = & $cand[0] @pre -c 'import sys; print(sys.version_info[0] * 100 + sys.version_info[1])' 2>$null
            } catch { continue }
            $ver = "$($ver | Select-Object -Last 1)".Trim()
            if ($LASTEXITCODE -eq 0 -and $ver -match '^\d+$' -and [int]$ver -ge 308) { return , $cand }
        }
        return $null
    }

    Write-Host '== 准备：git、Python、插件仓库 =='

    # 1. git
    if (-not (Test-Git)) {
        if ($hasWinget) {
            Write-Host '[INFO] 没有 git，用 winget 安装 Git.Git ...'
            & winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
            Update-SessionPath
        }
        if (-not (Test-Git)) {
            Write-Host '[FAIL] 没有 git。到 https://git-scm.com/download/win 下载安装（刚用 winget 装过的，新开一个 PowerShell 窗口），然后重新运行这条命令'
            $global:LASTEXITCODE = 1
            return
        }
    }
    Write-Host "[OK]   $(& git --version)"

    # 2. Python 3.8+
    $py = Find-Python
    if (-not $py -and $hasWinget) {
        Write-Host '[INFO] 没有 Python 3.8+，用 winget 安装 Python.Python.3.12 ...'
        & winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
        Update-SessionPath
        $py = Find-Python
    }
    if (-not $py) {
        Write-Host '[FAIL] 没有 Python 3.8+。到 https://www.python.org/downloads/ 下载安装（勾选 Add python.exe to PATH；刚用 winget 装过的，新开一个 PowerShell 窗口），然后重新运行这条命令'
        $global:LASTEXITCODE = 1
        return
    }
    $pyExe = $py[0]
    $pyPre = @($py | Select-Object -Skip 1)
    Write-Host "[OK]   $(& $pyExe @pyPre --version 2>&1)"

    # 3. 插件仓库：公开仓库，https 克隆，不需要 SSH；更新失败不阻断
    $env:GIT_TERMINAL_PROMPT = '0'
    if (Test-Path (Join-Path $dir '.git')) {
        & git -C $dir pull --ff-only -q
        if ($LASTEXITCODE -eq 0) { Write-Host "[OK]   插件仓库已是最新：$dir" }
        else { Write-Host "[WARN] 插件仓库没更新成（没网、有本地改动或分叉），用现有版本继续：$dir" }
    } elseif ((Test-Path $dir) -and (Get-ChildItem -Force $dir | Select-Object -First 1)) {
        Write-Host "[WARN] $dir 已存在但不是 git 仓库，直接用里面的文件"
    } else {
        Write-Host "[INFO] 下载插件仓库到 $dir"
        New-Item -ItemType Directory -Force -Path (Split-Path $dir) | Out-Null
        & git clone -q $repo $dir
        if ($LASTEXITCODE -ne 0) {
            Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue
            Write-Host "[FAIL] 下载失败：检查网络后重跑（地址 $repo）"
            $global:LASTEXITCODE = 1
            return
        }
    }
    Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue
    $bootstrap = Join-Path $dir $rel
    if (-not (Test-Path $bootstrap)) {
        Write-Host "[FAIL] 找不到 ${bootstrap}：插件仓库版本不对，删掉 $dir 后重跑"
        $global:LASTEXITCODE = 1
        return
    }

    # 4. 交给 bootstrap.py（在 PowerShell 窗口里运行时 stdin 就是控制台，脚本可以直接提问）
    $env:GUPO_SETUP_ENTRY = 'ps1'
    try {
        & $pyExe @pyPre $bootstrap @PassArgs
        $code = $LASTEXITCODE
    } finally {
        Remove-Item Env:GUPO_SETUP_ENTRY -ErrorAction SilentlyContinue
    }
    $global:LASTEXITCODE = $code
}

if ($GupoSetupArgs.Count -eq 0 -and $env:GUPO_SETUP_ARGS) {
    $GupoSetupArgs = @($env:GUPO_SETUP_ARGS -split '\s+' | Where-Object { $_ })
}
Invoke-GupoSetup -PassArgs $GupoSetupArgs
