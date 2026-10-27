param([switch]$SkipVoice)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE). Fix the error above and rerun install.bat." }
}

function Refresh-ToolPath {
    $env:Path = $env:Path + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + (Join-Path $env:USERPROFILE '.local\bin')
}

function Install-Tool {
    param([string]$Command, [string]$Package)
    if (Get-Command $Command -ErrorAction SilentlyContinue) { return }
    if (!(Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'Install App Installer from the Microsoft Store to enable winget, then rerun install.bat.'
    }
    Write-Host "Installing $Package..."
    Invoke-Checked 'winget.exe' @('install', '--id', $Package, '--exact', '--source', 'winget', '--accept-package-agreements', '--accept-source-agreements')
    Refresh-ToolPath
    if (!(Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$Package was installed, but is not on PATH yet. Close this window and rerun install.bat."
    }
}

try {
    if (!(Test-Path -LiteralPath 'apps\web\package-lock.json') -or !(Test-Path -LiteralPath 'apps\api\uv.lock')) {
        throw 'Extract or clone the whole Fieldnote repository before running install.bat.'
    }
    Write-Host 'Fieldnote setup: Windows web app and Python API'
    Write-Host 'Internet access is required. Voice setup downloads several GB and needs NVIDIA WSL CUDA support.'
    Install-Tool 'node.exe' 'OpenJS.NodeJS.LTS'
    Install-Tool 'uv.exe' 'astral-sh.uv'
    $nodeVersion = & node.exe -p process.versions.node
    if ($LASTEXITCODE -ne 0 -or [version]$nodeVersion -lt [version]'22.12.0') {
        throw 'Node.js 22.12 or newer is required. Update Node.js and rerun setup.'
    }
    if (!(Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'npm is missing. Repair your Node.js installation and rerun setup.' }
    Invoke-Checked 'npm.cmd' @('ci', '--prefix', (Join-Path $projectRoot 'apps\web'))
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $projectRoot 'apps\api\.venv'
    Invoke-Checked 'uv.exe' @('sync', '--project', 'apps/api', '--locked', '--group', 'dev', '--python', '3.12')
    if (!(Test-Path -LiteralPath '.env')) {
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
        Write-Host 'Created .env. Existing settings are never overwritten.'
    }
    Invoke-Checked 'npm.cmd' @('run', 'build', '--prefix', (Join-Path $projectRoot 'apps\web'))

    if (!$SkipVoice) {
        if (!(Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
            throw 'WSL is missing. Run wsl --install -d Ubuntu in an Administrator terminal, restart Windows, then rerun install.bat.'
        }
        $distros = (& wsl.exe --list --quiet 2>$null | Out-String) -replace "`0", ''
        $listResult = $LASTEXITCODE
        if ($listResult -ne 0 -or !($distros -split "`r?`n" | Where-Object { $_.Trim() -eq 'Ubuntu' })) {
            Write-Host 'Installing Ubuntu WSL. Windows may request administrator permission or a restart.'
            Invoke-Checked 'wsl.exe' @('--install', '-d', 'Ubuntu', '--no-launch')
            Write-Host 'Open Ubuntu from Start and finish creating your Linux username/password. Restart Windows if requested, then rerun install.bat.'
            exit 2
        }
        $linuxUser = & wsl.exe -d Ubuntu -- id -u
        if ($LASTEXITCODE -ne 0 -or $linuxUser.Trim() -eq '0') {
            throw 'Open Ubuntu and create/select a regular Linux user before setup.'
        }
        # Pass the Windows path as an argument, never interpolate it into shell code.
        $linuxRoot = & wsl.exe -d Ubuntu -- wslpath -a -u $projectRoot
        if ($LASTEXITCODE -ne 0 -or !$linuxRoot) { throw 'Could not map the project folder into Ubuntu.' }
        Invoke-Checked 'wsl.exe' @('-d', 'Ubuntu', '--cd', $linuxRoot.Trim(), '--', 'bash', 'scripts/install-local-speech.sh')
    }
    Write-Host ''
    Write-Host 'Setup complete. Add your provider key to .env. Optional OpenAI connection setup is documented in README.md.'
    if ($SkipVoice) {
        Write-Host 'Voice was skipped. Follow the Windows API startup steps in README.md for typed interviews.'
    } else {
        Write-Host 'Run start.bat to launch Fieldnote. Speech models warm automatically when the API starts.'
    }
    Write-Host 'The separate code-execution runner is not installed on this computer.'
} catch {
    Write-Host "Setup stopped: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
