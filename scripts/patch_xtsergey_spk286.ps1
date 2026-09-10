<#
Patch the user-supplied Sergey XT BIOS for a SPK286 bring-up run.

The original image is never modified.  The patch changes only the conditional
branch which prints the 8088 segment-register warning; the CPU probe and all
other BIOS code remain byte-for-byte identical.
#>
[CmdletBinding()]
param(
    [string]$InputPath,
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($InputPath)) {
    $InputPath = Join-Path $PSScriptRoot '..\SW\ROMs\test\xtsergey_mod.rom'
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $PSScriptRoot '..\SW\ROMs\test\xtsergey_mod_spk286.rom'
}

$expectedInputSha256 = 'DF25BBC8ABA4E35EB56CA585B2C7054DA1D7435278B2BFE0F0C7FFAE2F85F443'
$offset = 0xD721
$expectedBytes = [byte[]](0x75, 0x06) # JNZ +6: print warning when AX == 0001h
$replacementBytes = [byte[]](0xEB, 0x06) # JMP +6: skip only the warning print

$inputFullPath = [IO.Path]::GetFullPath($InputPath)
$outputFullPath = [IO.Path]::GetFullPath($OutputPath)
if (-not [IO.File]::Exists($inputFullPath)) {
    throw "Input ROM not found: $inputFullPath"
}

$inputHash = (Get-FileHash -LiteralPath $inputFullPath -Algorithm SHA256).Hash.ToUpperInvariant()
if ($inputHash -ne $expectedInputSha256) {
    throw "Unexpected input ROM SHA-256 ($inputHash). Refusing to patch a different image."
}

$bytes = [IO.File]::ReadAllBytes($inputFullPath)
if ($bytes.Length -ne 65536) {
    throw "Unexpected input ROM size: $($bytes.Length) bytes (expected 65536)."
}
for ($i = 0; $i -lt $expectedBytes.Length; $i++) {
    if ($bytes[$offset + $i] -ne $expectedBytes[$i]) {
        throw ('Unexpected bytes at ROM offset 0x{0:X4}: got {1:X2} {2:X2}, expected 75 06.' -f $offset, $bytes[$offset], $bytes[$offset + 1])
    }
}

for ($i = 0; $i -lt $replacementBytes.Length; $i++) {
    $bytes[$offset + $i] = $replacementBytes[$i]
}

$outputDirectory = Split-Path -Parent $outputFullPath
if (-not [IO.Directory]::Exists($outputDirectory)) {
    [IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
}
if ([IO.File]::Exists($outputFullPath)) {
    $existingHash = (Get-FileHash -LiteralPath $outputFullPath -Algorithm SHA256).Hash.ToUpperInvariant()
    $newHash = ([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes)
    $newHashText = ([BitConverter]::ToString($newHash) -replace '-', '').ToUpperInvariant()
    if ($existingHash -ne $newHashText) {
        throw "Refusing to overwrite an existing different output ROM: $outputFullPath"
    }
    Write-Output "Already present: $outputFullPath"
    Write-Output "SHA-256: $existingHash"
    exit 0
}

[IO.File]::WriteAllBytes($outputFullPath, $bytes)
$outputHash = (Get-FileHash -LiteralPath $outputFullPath -Algorithm SHA256).Hash.ToUpperInvariant()
Write-Output "Created: $outputFullPath"
Write-Output "Patched ROM offset: 0x$('{0:X4}' -f $offset) (75 06 -> EB 06)"
Write-Output "SHA-256: $outputHash"
