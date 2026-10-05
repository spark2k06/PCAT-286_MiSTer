param(
    [switch]$Apply,
    [string]$BeforeDate = '2026-10-05',
    [string]$Receipt = 'docs/evidence/temporary-storage-cleanup-20261005.json'
)

# Only discard regenerable Verilator precompiled headers. Keep the source
# headers, executables, traces, reports, bitstreams and today's active builds.
$ErrorActionPreference = 'Stop'
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskBuildRoot = (Resolve-Path -LiteralPath (Join-Path $taskWorkspace 'build')).Path
$taskPrefix = $taskBuildRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
$taskCutoff = [datetime]::ParseExact($BeforeDate, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
$taskReceiptPath = [IO.Path]::GetFullPath((Join-Path $taskWorkspace $Receipt))
if (-not $taskReceiptPath.StartsWith($taskWorkspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Receipt must remain inside this workspace'
}
if ((Get-Item -LiteralPath $taskBuildRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Build root is a reparse point'
}
$taskFiles = @(Get-ChildItem -LiteralPath $taskBuildRoot -Recurse -File -Filter '*.gch' -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^V.+__pch\.h\.(fast|slow)\.gch$' -and $_.LastWriteTime -lt $taskCutoff })
$taskCheckedParents = @{}
$taskPlan = @()
foreach ($taskFile in $taskFiles) {
    $taskPath = [IO.Path]::GetFullPath($taskFile.FullName)
    if (-not $taskPath.StartsWith($taskPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Outside build: $taskPath" }
    if ($taskFile.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked file: $taskPath" }
    $taskParent = $taskFile.Directory
    while ($taskParent.FullName -ne $taskBuildRoot) {
        if (-not $taskParent.FullName.StartsWith($taskPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Parent escaped build' }
        if (-not $taskCheckedParents.ContainsKey($taskParent.FullName)) {
            if ($taskParent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked parent: $($taskParent.FullName)" }
            $taskCheckedParents[$taskParent.FullName] = $true
        }
        $taskParent = $taskParent.Parent
    }
    $taskHeader = $taskPath -replace '\.(fast|slow)\.gch$', ''
    $taskHeaderInfo = Get-Item -LiteralPath $taskHeader
    if ($taskHeaderInfo.PSIsContainer -or ($taskHeaderInfo.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Missing regular source header: $taskHeader"
    }
    $taskPlan += [PSCustomObject]@{
        path = $taskPath.Substring($taskWorkspace.Length + 1).Replace('\', '/')
        bytes = $taskFile.Length
        source_header = $taskHeader.Substring($taskWorkspace.Length + 1).Replace('\', '/')
        header_sha256 = (Get-FileHash -LiteralPath $taskHeader -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
$taskTracked = @(git -C $taskWorkspace ls-files -- build)
if ($LASTEXITCODE -ne 0 -or $taskTracked.Count -ne 0) { throw 'Cannot discard tracked build files' }
$taskFreeBefore = @(Get-PSDrive -Name C,D | Select-Object Name,Free)
$taskRecord = [ordered]@{
    status = 'VALIDATED_PLAN_ONLY'
    cutoff_local = $taskCutoff.ToString('yyyy-MM-dd')
    resolved_root = $taskBuildRoot
    candidate_count = $taskPlan.Count
    candidate_logical_bytes = [long](($taskPlan | Measure-Object bytes -Sum).Sum)
    files = $taskPlan
    free_before = $taskFreeBefore
    preserved = 'Every corresponding source header, all non-PCH artifacts and all files modified on/after cutoff'
}
if ($Apply) {
    # All targets were validated before the first mutation. Recheck each file
    # for replacement or concurrent writes immediately before deleting it.
    $taskDeletedBytes = [long]0
    foreach ($taskEntry in $taskPlan) {
        $taskDeletePath = Join-Path $taskWorkspace $taskEntry.path
        $taskNow = Get-Item -LiteralPath $taskDeletePath
        if ($taskNow.Length -ne $taskEntry.bytes -or $taskNow.LastWriteTime -ge $taskCutoff -or
            ($taskNow.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Target changed: $taskDeletePath" }
        Remove-Item -LiteralPath $taskDeletePath
        $taskDeletedBytes += $taskEntry.bytes
    }
    foreach ($taskEntry in $taskPlan) {
        if (Test-Path -LiteralPath (Join-Path $taskWorkspace $taskEntry.path)) { throw 'A deleted target remains' }
        if ((Get-FileHash -LiteralPath (Join-Path $taskWorkspace $taskEntry.source_header) -Algorithm SHA256).Hash.ToLowerInvariant() -ne
            $taskEntry.header_sha256) { throw 'A preserved header changed' }
    }
    $taskRecord.status = 'GENERATED_VERILATOR_PCH_CLEANUP_COMPLETE'
    $taskRecord.deleted_logical_bytes = $taskDeletedBytes
    $taskRecord.free_after = @(Get-PSDrive -Name C,D | Select-Object Name,Free)
}
$taskRecord | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
[PSCustomObject]@{status=$taskRecord.status; count=$taskPlan.Count; logical_bytes=$taskRecord.candidate_logical_bytes;
    receipt=$taskReceiptPath; free=@(Get-PSDrive -Name C,D | Select-Object Name,Free)} | ConvertTo-Json -Depth 4
