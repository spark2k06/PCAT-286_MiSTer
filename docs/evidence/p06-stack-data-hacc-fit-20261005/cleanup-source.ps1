$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath 'D:\GitHub\PCAT-286_MiSTer').Path
$taskFitRoot = (Resolve-Path -LiteralPath (Join-Path $taskRoot 'build\p06-stack-data-hacc-allfeatures-20261005-v1')).Path
$taskWorkRoot = (Resolve-Path -LiteralPath (Join-Path $taskFitRoot 'work')).Path
$taskEvidenceRoot = (Resolve-Path -LiteralPath (Join-Path $taskRoot 'docs\evidence\p06-stack-data-hacc-fit-20261005')).Path
$taskOriginalRoot = (Resolve-Path -LiteralPath (Join-Path $taskRoot 'build\p06-stack-data-hacc-original-sdc-sta-20261005-v1')).Path
foreach ($taskOwnedRoot in @($taskRoot,$taskFitRoot,$taskWorkRoot,$taskEvidenceRoot,$taskOriginalRoot)) {
    if ((Get-Item -LiteralPath $taskOwnedRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Owned roots must not be reparse points.' }
}
$taskManifest = Get-Content -LiteralPath (Join-Path $taskEvidenceRoot 'manifest.json') -Raw | ConvertFrom-Json
$taskResult = Get-Content -LiteralPath (Join-Path $taskEvidenceRoot 'result.json') -Raw | ConvertFrom-Json
$taskReview = Get-Content -LiteralPath (Join-Path $taskEvidenceRoot 'independent-review.json') -Raw | ConvertFrom-Json
$taskOriginal = Get-Content -LiteralPath (Join-Path $taskOriginalRoot 'manifest.json') -Raw | ConvertFrom-Json
if ($taskResult.status -ne 'TIMING_OPEN_CHECK_REPORTED_MARGINS' -or $taskReview.status -ne 'INDEPENDENT_ACTUAL_FIT_REVIEW_PASS_TIMING_STILL_OPEN') { throw 'Completed independent review is required.' }
if ($taskResult.full_regression -ne 'USER_PAUSE_AFTER_CURRENT_FIT_NOT_RUN') { throw 'Latest pause instruction is absent.' }
foreach ($taskRun in @($taskFitRoot,$taskOriginalRoot)) {
    if (!(Test-Path -LiteralPath (Join-Path $taskRun 'completed.txt'))) { throw 'Fit/STA still active.' }
}
$taskArchive = Join-Path $taskEvidenceRoot $taskManifest.archive
if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskManifest.sha256 -or $taskManifest.sha256 -ne $taskReview.archive_sha256) { throw 'Verified source/report archive changed.' }
if ($taskManifest.verification -ne 'Every archived member read back equal before cleanup' -or $taskManifest.fitted_source_count -ne 2073) { throw 'Source readback/count differs.' }
foreach ($taskFile in $taskManifest.independent_review.files.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $taskEvidenceRoot $taskFile.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskFile.Value.sha256) { throw 'Independent review identity differs.' }
}
foreach ($taskArtifact in $taskOriginal.preserved_fitted_artifacts_sha256.PSObject.Properties) {
    $taskArtifactPath = Join-Path $taskWorkRoot ($taskArtifact.Name -replace '/', '\')
    if ((Get-FileHash -LiteralPath $taskArtifactPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskArtifact.Value) { throw 'Fitted DB/RBF/SOF identity differs.' }
}
$taskTrackedArchive = & git -C $taskRoot ls-files --error-unmatch -- ('docs/evidence/p06-stack-data-hacc-fit-20261005/' + $taskManifest.archive)
if ($LASTEXITCODE -ne 0 -or !$taskTrackedArchive) { throw 'The source/report archive must be committed before cleanup.' }
$taskSealHead = (& git -C $taskRoot rev-parse HEAD).Trim()
$taskCommitArchive = & git -C $taskRoot ls-tree HEAD -- ('docs/evidence/p06-stack-data-hacc-fit-20261005/' + $taskManifest.archive)
if ($LASTEXITCODE -ne 0 -or !$taskCommitArchive) { throw 'Sealed archive is absent from HEAD.' }
$taskRbf = Join-Path $taskRoot ($taskResult.rbf.path -replace '/', '\')
$taskTargets = @(Get-ChildItem -LiteralPath $taskWorkRoot -Force | Where-Object { $_.Name -ne 'output_files' })
$taskInventory = @()
foreach ($taskTarget in $taskTargets) {
    $taskResolved = (Resolve-Path -LiteralPath $taskTarget.FullName).Path
    if (!$taskResolved.StartsWith($taskWorkRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or $taskResolved -eq $taskWorkRoot) { throw 'Target outside exact owned work directory.' }
    $taskEntries = @($taskTarget)
    if ($taskTarget.PSIsContainer) { $taskEntries += @(Get-ChildItem -LiteralPath $taskResolved -Recurse -Force) }
    if (@($taskEntries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'Cleanup must not traverse reparse points.' }
    $taskFiles = @($taskEntries | Where-Object { !$_.PSIsContainer })
    $taskInventory += [pscustomobject]@{ path=$taskResolved; files=$taskFiles.Count; bytes=[long](($taskFiles | Measure-Object -Property Length -Sum).Sum) }
}
$taskDiskBefore = @{}
foreach ($taskDisk in Get-PSDrive C,D) { $taskDiskBefore[$taskDisk.Name] = $taskDisk.Free }
foreach ($taskTarget in $taskTargets) { Remove-Item -LiteralPath $taskTarget.FullName -Recurse -Force }
if (@(Get-ChildItem -LiteralPath $taskWorkRoot -Force | Where-Object { $_.Name -ne 'output_files' }).Count) { throw 'Owned cleanup incomplete.' }
if ((Get-FileHash -LiteralPath $taskRbf -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskResult.rbf.sha256) { throw 'Preserved RBF changed.' }
$taskDiskAfter = @{}
foreach ($taskDisk in Get-PSDrive C,D) { $taskDiskAfter[$taskDisk.Name] = $taskDisk.Free }
$taskReceipt = [ordered]@{
    status='OWNED_FIT_BULK_CLEANED_AFTER_COMMITTED_INDEPENDENT_READBACK'
    archive_sha256=$taskManifest.sha256
    rbf_sha256=$taskResult.rbf.sha256
    sealed_commit=$taskSealHead
    source_files_archived=2073
    deleted_targets=$taskInventory
    deleted_bytes=[long](($taskInventory | Measure-Object -Property bytes -Sum).Sum)
    retained='RBF/SOF and complete output_files; metadata, original/global four-corner reports, all 2073 effective sources and proof/source/ROM/resource identities in the committed readback-verified archive.'
    full_regression='USER_PAUSE_AFTER_CURRENT_FIT_NOT_RUN; frozen effective sources remain recoverable for future regression.'
    containers='Fit and original-SDC --rm containers completed; docker ps independently observed empty before cleanup.'
    free_before_bytes=$taskDiskBefore
    free_after_bytes=$taskDiskAfter
    scope='Only non-output_files entries of this exact completed owned fit work directory; no original user/repository files, other builds or global caches.'
}
$taskJson = $taskReceipt | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $taskEvidenceRoot 'cleanup.json'), ($taskJson -replace "\r\n", "`n") + "`n", [Text.UTF8Encoding]::new($false))
Write-Output ('STACK_DATA_HACC_OWNED_FIT_CLEANED {0} bytes; best RBF retained' -f $taskReceipt.deleted_bytes)
