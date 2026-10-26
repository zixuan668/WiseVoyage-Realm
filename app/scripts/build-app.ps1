param(
    [string]$HBuilderX = 'D:\HBuilderX\HBuilderX',
    [string]$ServerOrigin = ''
)
$ErrorActionPreference = 'Stop'
$taskAppRoot = Split-Path $PSScriptRoot -Parent
$taskCompiler = Join-Path $HBuilderX 'plugins\uniapp-cli-vite'
$taskNode = Join-Path $HBuilderX 'plugins\node\node.exe'
if (-not (Test-Path -LiteralPath $taskNode)) { throw 'HBuilderX Node runtime not found. Pass -HBuilderX with your installation directory.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskCompiler 'vite.config.js'))) { throw 'Install the HBuilderX uni-app compiler plugin first.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskAppRoot 'manifest.json'))) {
    throw 'App manifest.json is missing. Restore the tracked app/manifest.json before building.'
}
if ($ServerOrigin) {
    $taskUri = $null
    if (-not [Uri]::TryCreate($ServerOrigin, [UriKind]::Absolute, [ref]$taskUri) -or $taskUri.Scheme -notin @('http','https')) { throw 'ServerOrigin must be an absolute http(s) origin.' }
    $env:VITE_APP_SERVER_ORIGIN = $ServerOrigin.TrimEnd('/')
}
$env:UNI_INPUT_DIR = $taskAppRoot
$env:UNI_OUTPUT_DIR = Join-Path $taskAppRoot 'unpackage\dist\build\app-plus'
$env:UNI_CLI_CONTEXT = $taskCompiler
$env:UNI_HBUILDERX_PLUGINS = Join-Path $HBuilderX 'plugins'
$env:NODE_ENV = 'production'
$env:UNI_PLATFORM = 'app'
Push-Location -LiteralPath $taskCompiler
try {
    & $taskNode 'node_modules/@dcloudio/vite-plugin-uni/bin/uni.js' build --platform app --config vite.config.js
    if ($LASTEXITCODE -ne 0) { throw "App compilation failed (exit $LASTEXITCODE)." }
} finally { Pop-Location }
if (-not (Test-Path -LiteralPath (Join-Path $env:UNI_OUTPUT_DIR 'app-service.js'))) { throw 'Native compiler did not produce app-service.js.' }
Write-Host "Native App resources built: $env:UNI_OUTPUT_DIR"
Write-Host 'These are compiled resources. Build/sign an APK in HBuilderX separately.'
