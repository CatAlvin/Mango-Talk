param(
    [string]$SshHost,
    [string]$RemoteProject,
    [string]$PublicUrl
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$LocalConfigPath = Join-Path $ProjectRoot '.deploy\local-config.json'
if (Test-Path -LiteralPath $LocalConfigPath) {
    $LocalConfig = Get-Content -LiteralPath $LocalConfigPath -Raw | ConvertFrom-Json
    if (-not $SshHost) { $SshHost = $LocalConfig.sshHost }
    if (-not $RemoteProject) { $RemoteProject = $LocalConfig.remoteProject }
    if (-not $PublicUrl) { $PublicUrl = $LocalConfig.publicUrl }
}
if (-not $PublicUrl) { throw 'Provide the public HTTPS origin, without a path.' }
$PublicUrl = $PublicUrl.TrimEnd('/')
if ($SshHost -notmatch '^[A-Za-z0-9][A-Za-z0-9@._-]*$') { throw 'Provide a valid SSH host or alias.' }
if ($RemoteProject -notmatch '^/[A-Za-z0-9._/-]+/mango-talk$' -or $RemoteProject.Contains('..')) { throw 'Provide an absolute project path ending in /mango-talk.' }
if ($PublicUrl -notmatch '^https://[A-Za-z0-9][A-Za-z0-9.-]*$') { throw 'Provide the public HTTPS origin, without a path.' }

function Invoke-CheckedNative {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE"
    }
}

Push-Location -LiteralPath $ProjectRoot
$StagingDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('mango-talk-' + [guid]::NewGuid().ToString('N'))
try {
    $Revision = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $Revision -notmatch '^[0-9a-f]{40}$') { throw 'Cannot determine Git revision.' }
    $Branch = (& git branch --show-current).Trim()
    if ($Branch -ne 'main') { throw 'Deploy the reviewed main branch.' }
    $GitStatus = & git status --porcelain
    if ($LASTEXITCODE -ne 0 -or $GitStatus) { throw 'Commit all project changes before deployment.' }
    $RemoteMain = & git ls-remote origin refs/heads/main
    if ($LASTEXITCODE -ne 0 -or -not $RemoteMain.StartsWith($Revision)) { throw 'Push the reviewed commit to GitHub main before deployment.' }

    $NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    $PnpmCommand = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if (-not $NpmCommand -and -not $PnpmCommand) { throw 'npm.cmd or pnpm.cmd is required to build the frontend.' }
    Push-Location -LiteralPath (Join-Path $ProjectRoot 'frontend')
    try {
        if ($NpmCommand) {
            Invoke-CheckedNative $NpmCommand.Source @('ci')
            Invoke-CheckedNative $NpmCommand.Source @('run', 'build')
        }
        else {
            Invoke-CheckedNative $PnpmCommand.Source @('--package=npm@11.6.2', 'dlx', 'npm', 'ci')
            Invoke-CheckedNative $PnpmCommand.Source @('--package=npm@11.6.2', 'dlx', 'npm', 'run', 'build')
        }
    }
    finally { Pop-Location }
    $FrontendDist = Join-Path $ProjectRoot 'frontend\dist'
    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDist 'index.html'))) { throw 'The production frontend build is missing.' }
    $Manifest = @{ commit = $Revision; builtAt = [DateTime]::UtcNow.ToString('o') } | ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText((Join-Path $FrontendDist 'release.json'), $Manifest, [System.Text.UTF8Encoding]::new($false))

    New-Item -ItemType Directory -Path $StagingDirectory | Out-Null
    $FrontendArchive = Join-Path $StagingDirectory 'frontend.tar.gz'
    $DeploymentArchive = Join-Path $StagingDirectory 'deploy.tar'
    Invoke-CheckedNative 'tar.exe' @('-C', $FrontendDist, '-czf', $FrontendArchive, '.')
    Invoke-CheckedNative 'git' @('archive', '--format=tar', "--output=$DeploymentArchive", $Revision, 'deploy')
    $RemoteDirectory = '/tmp/mango-talk-' + [guid]::NewGuid().ToString('N')
    Invoke-CheckedNative 'ssh' @('-o', 'BatchMode=yes', $SshHost, "mkdir -m 700 '$RemoteDirectory'")
    Invoke-CheckedNative 'scp' @('-o', 'BatchMode=yes', $FrontendArchive, $DeploymentArchive, "${SshHost}:$RemoteDirectory/")
    Invoke-CheckedNative 'ssh' @('-o', 'BatchMode=yes', $SshHost, "tar -xf '$RemoteDirectory/deploy.tar' -C '$RemoteDirectory' && bash '$RemoteDirectory/deploy/server.sh' '$Revision' '$RemoteDirectory/frontend.tar.gz' '$RemoteProject' '$PublicUrl'")
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $StagingDirectory) {
        $ResolvedStaging = (Resolve-Path -LiteralPath $StagingDirectory).Path
        $ExpectedTempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        if (-not $ResolvedStaging.StartsWith($ExpectedTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'Refusing cleanup outside the temporary directory.'
        }
        Remove-Item -LiteralPath $ResolvedStaging -Recurse -Force
    }
}
