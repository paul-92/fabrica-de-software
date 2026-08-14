param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet('start','stop','status','restart')]
    [string]$Command
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
$releaseId = (Get-Content -Raw -LiteralPath $pointer | ConvertFrom-Json).release_id
if ($releaseId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') {
    throw 'ASEP active release id is invalid.'
}
$release = [IO.Path]::GetFullPath((Join-Path (Join-Path $betaRoot 'releases') $releaseId))
$releases = [IO.Path]::GetFullPath((Join-Path $betaRoot 'releases'))
if ([IO.Directory]::GetParent($release).FullName -ne $releases) {
    throw 'ASEP active release escaped releases root.'
}
$python = Join-Path $release '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'ASEP release Python executable is missing.'
}
& $python -m deployment.windows_runtime $Command --root $betaRoot
exit $LASTEXITCODE
