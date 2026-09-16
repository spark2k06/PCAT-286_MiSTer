# AT hardware boot checkpoint — 2026-09-12

The user reports that the previous independent boot corrections now boot on
MiSTer. Supersoft Landmark reaches its DMA page-register diagnostic and displays
CPU/register and timer-channel-0 passes. Full POST is not yet passing.

This checkpoint preserves all source, profile, test and documentation changes
that were present for that build, including the pre-existing AT integration.
No new peripheral fixes are part of this checkpoint.

Latest local build archived without modification:
`releases/PCAT-286_20260912_boot_checkpoint_AT_FAST.rbf`
SHA-256: `0D4BD1B4C9F6B1590362F95ACF09A5D38FCC836FEA5A43998764620D34FA4E2C`.
Source: `output_files_pcat286_at_fast/PCAT-286_AT_FAST.rbf`, last written
2026-09-12 11:47:05 local time. This is the latest local synthesis associated
with the user's report; the flashed file hash was not supplied independently.

The audited RTL source manifest from the preceding review is unchanged. Previous
simulation and regression results were used only to validate this checkpoint.

External diagnostic ROM images, disk images, unrelated analysis executables,
old failed bitstreams, and transient Quartus output directories remain local.
The ROM patch scripts and their source hashes are preserved for reproduction.
The next investigation uses the existing user-selected Landmark SKIP_PM image:
SHA-256 `E9A3F0605996FF6802F44AD1744675C01DF9B5832273BB7472C878A6AAD03EC6`.

Current timing summary is not a timing sign-off: worst setup -21.537 ns;
worst hold +0.054 ns. SDRAM_CLK is now constrained and reports positive setup
and hold. Internal-domain/CDC setup still needs assessment from the new fit.
