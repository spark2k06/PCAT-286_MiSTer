# User-reported 4 KiB candidate performance on MiSTer

Date: 2026-10-02. Original screenshots are retained in `checkit.png` and
`checknum.png`. Their hashes and transcription are in `observation.json`.

| Measurement | P10 | 4 KiB candidate | Gain |
| --- | ---: | ---: | ---: |
| CheckIT and CHECKNUM Dhrystones | 4361 | 4911 | 12.612% |
| CheckIT K Whetstones | 84.1 | 95.1 | 13.080% |
| CHECKNUM K Whetstones | 83.7 | 94.4 | 12.784% |

CheckIT estimates 35.03 MHz, with PC-XT ratings 14.28 / 14.40 and no NPU.
That calibration estimate is separate from the configured 50 MHz FPGA clock.
The programs' software math scores remain separate observations.

The conversation associates these results with the user's compilation of
RTL `0399806`. The local associated RBF is 4,162,364 bytes, SHA256
`1a0b8c1c5de65f9b5e21eb087d45805aaee65922df5aab6205bfbee6c7ebd98b`.
The loaded MiSTer hash and OSD setting were not independently read. No repeat
distribution or guest configuration dump was supplied. This accepts the
reported benchmark improvement; general software, regression and timing
acceptance remain separate.
