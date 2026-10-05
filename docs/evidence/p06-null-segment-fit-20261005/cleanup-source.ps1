$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath 'D:\GitHub\PCAT-286_MiSTer').Path
$fitRoot = (Resolve-Path -LiteralPath (Join-Path $taskRoot 'build\p06-null-segment-allfeatures-20261005-v1')).Path
$workRoot = (Resolve-Path -LiteralPath (Join-Path $fitRoot 'work')).Path
$evidenceRoot = (Resolve-Path -LiteralPath (Join-Path $taskRoot 'docs\evidence\p06-null-segment-fit-20261005')).Path
$manifest = Get-Content -LiteralPath (Join-Path $evidenceRoot 'manifest.json') -Raw | ConvertFrom-Json
$result = Get-Content -LiteralPath (Join-Path $evidenceRoot 'result.json') -Raw | ConvertFrom-Json
$review = Get-Content -LiteralPath (Join-Path $evidenceRoot 'independent-review.json') -Raw | ConvertFrom-Json
if ($result.status -ne 'TIMING_OPEN_CHECK_REPORTED_MARGINS' -or $review.status -ne 'INDEPENDENT_ACTUAL_FIT_REVIEW_PASS_TIMING_STILL_OPEN') { throw 'Only the completed, independently reviewed non-closing fit can be cleaned.' }
if (!(Test-Path -LiteralPath (Join-Path $fitRoot 'completed.txt'))) { throw 'Fit/STA still active.' }
$archivePath = Join-Path $evidenceRoot $manifest.archive
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256 -or $manifest.sha256 -ne $review.archive_sha256) { throw 'Verified source/report archive changed.' }
if ($manifest.verification -ne 'Every archived member read back equal before cleanup') { throw 'Source archive readback absent.' }
$rbfPath = Join-Path $taskRoot ($result.rbf.path -replace '/', '\')
if ((Get-FileHash -LiteralPath $rbfPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $result.rbf.sha256) { throw 'RBF identity differs.' }
$targets = @(Get-ChildItem -LiteralPath $workRoot -Force | Where-Object { $_.Name -ne 'output_files' })
$inventory = @()
foreach ($target in $targets) {
    $resolvedTarget = (Resolve-Path -LiteralPath $target.FullName).Path
    if (!$resolvedTarget.StartsWith($workRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or $resolvedTarget -eq $workRoot) { throw 'Cleanup target outside the exact owned frozen work directory.' }
    $entries = @($target)
    if ($target.PSIsContainer) { $entries += @(Get-ChildItem -LiteralPath $resolvedTarget -Recurse -Force) }
    if (@($entries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count -ne 0) { throw 'Cleanup must not traverse a reparse point.' }
    $files = @($entries | Where-Object { !$_.PSIsContainer })
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    $inventory += [pscustomobject]@{ path = $resolvedTarget; files = $files.Count; bytes = [long]$bytes }
}
$diskBefore = @{}
foreach ($disk in Get-PSDrive C,D) { $diskBefore[$disk.Name] = $disk.Free }
foreach ($target in $targets) { Remove-Item -LiteralPath $target.FullName -Recurse -Force }
if (@(Get-ChildItem -LiteralPath $workRoot -Force | Where-Object { $_.Name -ne 'output_files' }).Count -ne 0) { throw 'Owned compiler/source cleanup incomplete.' }
if ((Get-FileHash -LiteralPath $rbfPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $result.rbf.sha256) { throw 'Preserved RBF identity changed.' }
$diskAfter = @{}
foreach ($disk in Get-PSDrive C,D) { $diskAfter[$disk.Name] = $disk.Free }
$receipt = [ordered]@{
    status = 'NEGATIVE_FIT_OWNED_BULK_CLEANED_AFTER_SEALED_SOURCE_READBACK'
    archive_sha256 = $manifest.sha256
    rbf_sha256 = $result.rbf.sha256
    source_files_archived = $manifest.fitted_source_count
    deleted_targets = $inventory
    deleted_bytes = [long](($inventory | Measure-Object -Property bytes -Sum).Sum)
    retained = 'RBF/SOF and complete output_files; manifests, logs, production/original four-corner reports and all 2062 effective source bytes in the readback-verified committed archive.'
    full_regression = 'AUTHORIZED_AFTER_TIMING_CLOSURE_NOT_RUN; this negative fit cannot enter the regression. Freeze the later positive candidate separately.'
    containers = 'Fit and original-SDC --rm containers completed and independently observed absent before cleanup.'
    free_before_bytes = $diskBefore
    free_after_bytes = $diskAfter
    scope = 'Only non-output_files entries of this exact completed owned frozen work directory; no original repository/user files, other builds or global caches.'
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'cleanup.json') -Encoding utf8
Write-Output ('NULL_NEGATIVE_FIT_CLEANED {0} bytes; RBF retained' -f $receipt.deleted_bytes)
