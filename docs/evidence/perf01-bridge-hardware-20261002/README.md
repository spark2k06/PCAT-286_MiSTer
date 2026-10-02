# PERF01 bridge response: user-reported MiSTer measurements

Date: 2026-10-02. The user supplied these screenshots after receiving the
50 MHz bridge-response candidate and reported a notable improvement.
The original screenshot bytes are retained without editing.

| Measurement | Previous timing-closed RBF | Bridge candidate | Gain |
| --- | ---: | ---: | ---: |
| CheckIT Dhrystones | 3946 | 4361 | 10.517% |
| CHECKNUM Dhrystones | 3946 | 4361 | 10.517% |
| CheckIT Whetstones | 76.7K | 84.1K | 9.648% |
| CHECKNUM Whetstones | 76.7K | 83.7K | 9.126% |

The current CheckIT screenshot estimates 35.04 MHz (previous 35.02 MHz),
with ratings 12.68 times PC-XT for CPU and 12.74 for math, no NPU.
These frequency estimates are not the configured FPGA CPU clock, which
remains 50 MHz. CheckIT and CHECKNUM are recorded separately; their Whetstone
values differ and are not averaged or substituted for one another.

Delivered candidate: `build/perf01-bridge-candidate-20261002/PCAT-286.rbf`,
4,097,400 bytes, SHA-256
`3cbcbaaba667c48c4ef28c45f484c61563cee660e9fd21e8267a77cd013a3b7e`.
Its association with this hardware observation follows the conversation;
the screenshots do not independently attest the hash loaded into MiSTer.
No repeat-run distribution or separate current guest configuration dump
was provided. The preceding baseline's identity and maximum-speed setting
were explicitly confirmed by the user; see
[the prior record](../../optimization/P08_HARDWARE_CHECKIT_20261002.md).

These measurements agree in magnitude with the separately directed 9–10%
throughput gains, and support the practical benefit of the bridge change.
They do not establish FPGA timing closure or acceptance of all software.
The candidate's measured setup violations are recorded separately in
[P10](../../optimization/P10_BRIDGE_RESPONSE_20261002.md). No full CPU
regression or additional automated guest run was performed for this report.

Screenshot SHA-256 identities are in `files.sha256`. The user message was
"La mejora ha sido notable"; the numeric transcription above comes from
the two attached screenshots.
