param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet('start','stop','status')]
    [string]$Command
)

$ErrorActionPreference = 'Stop'
$betaRoot = $env:ASEP_WINDOWS_ROOT
if ([string]::IsNullOrWhiteSpace($betaRoot)) {
    $betaRoot = Join-Path $env:USERPROFILE 'ASEP-Beta'
}

# Provider-specific code and credentials stay outside immutable releases. The
# adapter implements the same start/stop/status contract and must redact output.
$adapter = Join-Path $betaRoot 'config\tunnel\connector.ps1'
if (-not (Test-Path -LiteralPath $adapter -PathType Leaf)) {
    throw 'Tunnel connector adapter is not configured.'
}

& $adapter $Command
exit $LASTEXITCODE
