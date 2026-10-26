param([string]$ServerAddress)
$ErrorActionPreference = 'Stop'
if (-not $ServerAddress) {
    $adapter = Get-NetAdapter -Physical | Where-Object Status -eq 'Up' | Select-Object -First 1
    if (-not $adapter) { throw 'No active physical network adapter. Specify -ServerAddress.' }
    $address = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 | Where-Object IPAddress -NotLike '169.254.*' | Select-Object -First 1
    if (-not $address) { throw 'No IPv4 address. Specify -ServerAddress.' }
    $ServerAddress = 'http://' + $address.IPAddress + ':18000'
}
$uri = [uri]$ServerAddress
if (-not $uri.IsAbsoluteUri -or $uri.Scheme -notin @('http','https') -or $uri.AbsolutePath -ne '/' -or $uri.Query -or $uri.Fragment -or $uri.UserInfo) {
    throw 'Use an HTTP/HTTPS origin without a path, credentials, query or fragment.'
}
$configPath = Join-Path $PSScriptRoot '../app/common/config.js'
$source = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
$source = $source -replace "export const LAN_SERVER_ORIGIN = '[^']*'", ("export const LAN_SERVER_ORIGIN = '" + $uri.GetLeftPart([System.UriPartial]::Authority) + "'")
Set-Content -LiteralPath $configPath -Value $source -Encoding utf8
Write-Output ('App backend: ' + $ServerAddress)
