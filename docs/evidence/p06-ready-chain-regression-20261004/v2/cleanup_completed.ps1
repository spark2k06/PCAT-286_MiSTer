$ErrorActionPreference = 'Stop'
$taskBuild = [IO.Path]::GetFullPath('D:\GitHub\PCAT-286_MiSTer\build\p06-ready-chain-regression-20261004-v2')
$taskVerilator = [IO.Path]::GetFullPath((Join-Path $taskBuild 'work\verilator'))
$taskLog = Join-Path $taskBuild 'regression.log'
$taskText = Get-Content -LiteralPath $taskLog -Raw
$taskIcarus = @([regex]::Matches($taskText, 'sim/unit/(spk286_[a-z0-9_]+_tb)\.sv:\d+: \$finish called') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$taskVerilated = @([regex]::Matches($taskText, 'sim/unit/(spk286_[a-z0-9_]+_tb)\.sv:\d+: Verilog \$finish') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$taskLatest = Get-ChildItem -LiteralPath $taskVerilator -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$taskCompleted = @($taskIcarus | Where-Object { $taskVerilated -contains $_ -and $_ -ne $taskLatest.Name })
$taskExtensions = @('.o', '.a', '.cpp', '.h', '.d', '.mk', '.gch')
$taskEntries = @()
$taskRemovedBytes = [long]0
$taskRemovedFiles = 0
foreach ($taskName in $taskCompleted) {
    $taskDirectory = [IO.Path]::GetFullPath((Join-Path $taskVerilator $taskName))
    if (-not $taskDirectory.StartsWith($taskVerilator + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Directory outside exact Verilator build' }
    if (-not (Test-Path -LiteralPath $taskDirectory -PathType Container)) { continue }
    $taskResolvedDirectory = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $taskDirectory).Path)
    if ($taskResolvedDirectory -ne $taskDirectory) { throw 'Unexpected resolved directory' }
    $taskBinary = Join-Path $taskDirectory $taskName
    $taskBuildLog = Join-Path $taskDirectory 'build.log'
    if (-not (Test-Path -LiteralPath $taskBinary -PathType Leaf) -or -not (Test-Path -LiteralPath $taskBuildLog -PathType Leaf)) { throw 'Missing completed binary or build log' }
    $taskBefore = (Get-FileHash -LiteralPath $taskBinary -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskLogBefore = (Get-FileHash -LiteralPath $taskBuildLog -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskFiles = @(Get-ChildItem -LiteralPath $taskDirectory -File | Where-Object { $taskExtensions -contains $_.Extension })
    $taskUnitBytes = [long]0
    foreach ($taskFile in $taskFiles) {
        $taskAbsolute = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $taskFile.FullName).Path)
        if (-not $taskAbsolute.StartsWith($taskDirectory + '\', [StringComparison]::OrdinalIgnoreCase) -or -not $taskAbsolute.StartsWith($taskVerilator + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'File outside authorized exact build' }
        $taskUnitBytes += $taskFile.Length
        Remove-Item -LiteralPath $taskAbsolute
    }
    $taskAfter = (Get-FileHash -LiteralPath $taskBinary -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskLogAfter = (Get-FileHash -LiteralPath $taskBuildLog -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($taskBefore -ne $taskAfter -or $taskLogBefore -ne $taskLogAfter) { throw 'Retained binary/build log changed' }
    if ($taskFiles.Count -gt 0) {
        $taskEntries += [pscustomobject]@{ unit = $taskName; removed_files = $taskFiles.Count; removed_bytes = $taskUnitBytes; binary_sha256_before = $taskBefore; binary_sha256_after = $taskAfter; build_log_sha256_before = $taskLogBefore; build_log_sha256_after = $taskLogAfter; directory = $taskDirectory }
        $taskRemovedBytes += $taskUnitBytes
        $taskRemovedFiles += $taskFiles.Count
    }
}
$taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$taskReceipt = [pscustomobject]@{ status = 'COMPLETED_UNIT_INTERMEDIATE_CLEANUP'; timestamp = (Get-Date).ToString('o'); exact_authorized_root = $taskVerilator; excluded_latest_directory = $taskLatest.FullName; removed_extensions = $taskExtensions; removed_files = $taskRemovedFiles; removed_bytes = $taskRemovedBytes; units = $taskEntries; kept = 'Completed executables, build logs, regression log, Icarus outputs, vectors, source snapshot and all other builds retained.' }
$taskReceipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskBuild ('cleanup-' + $taskStamp + '.json')) -Encoding utf8
[pscustomobject]@{ completed_units_cleaned = $taskEntries.Count; removed_files = $taskRemovedFiles; removed_bytes = $taskRemovedBytes; removed_gib = [math]::Round($taskRemovedBytes / 1GB, 3); drive_d_free_gib = [math]::Round((Get-PSDrive D).Free / 1GB, 3) } | ConvertTo-Json
