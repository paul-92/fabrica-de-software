param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet('plan','deploy','rollback')]
    [string]$Command,
    [Parameter(Position=1, Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')]
    [string]$ReleaseId
)

$ErrorActionPreference = 'Stop'
$betaRoot = $env:ASEP_WINDOWS_ROOT
if ([string]::IsNullOrWhiteSpace($betaRoot)) {
    $betaRoot = Join-Path $env:USERPROFILE 'ASEP-Beta'
}
$pointer = Join-Path $betaRoot 'current\active-release.json'
if (-not (Test-Path -LiteralPath $pointer -PathType Leaf)) {
    throw 'ASEP active release pointer is missing.'
}
$activeId = (Get-Content -Raw -LiteralPath $pointer | ConvertFrom-Json).release_id
if ($activeId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') {
    throw 'ASEP active release id is invalid.'
}
$python = Join-Path (Join-Path (Join-Path $betaRoot 'releases') $activeId) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'ASEP active release Python executable is missing.'
}

$arguments = @(
    '-m', 'deployment.deploy',
    $(if ($Command -eq 'plan') {'deploy'} else {$Command}),
    $ReleaseId,
    '--windows',
    '--releases-root', (Join-Path $betaRoot 'releases'),
    '--current-link', $pointer,
    '--database', (Join-Path $betaRoot 'data\asep.db'),
    '--hosted-root', (Join-Path $betaRoot 'workspaces'),
    '--backup-root', (Join-Path $betaRoot 'backups'),
    '--maintenance-root', (Join-Path $betaRoot 'temp\maintenance'),
    '--operations-root', (Join-Path $betaRoot 'temp\deployment')
)
if ($Command -eq 'plan') { $arguments += '--dry-run' }
& $python @arguments
exit $LASTEXITCODE
