# Historical timing audit evidence, 2026-10-05

The compressed packet retains the complete passive traces, generated bench,
builder, logs, selected Intel scan pages and original seal manifest. It is
4,971,549 bytes with SHA-256
`a23ad15aa3d15ebbe7452402979f735e0a38347ae51519b51483f61964d42876`.
Its 631 regular-file members all stay under the named private build directory.
Compiler objects and duplicate uncompressed traces are disposable.

`manifest.json` is the original byte-exact seal manifest. Production source
hashes bind the packet to the repository state recorded there; the builder and
bench are included in the packet. `verification.json` records a separate
review of all member hashes, source hashes, paired traces and run clock counts.

Validate the packet from any working directory without extraction or simulation:

```sh
python3 docs/evidence/p06-historical-timing-audit-20261005/verify_archive.py
```

Run the command from the repository root. Rebuilding requires Icarus and
Verilator under WSL and the bound source state. To restore the disposable
fixture from the repository root:

```sh
tar -xzf docs/evidence/p06-historical-timing-audit-20261005/p06-historical-timing-audit-20261005.tar.gz
python3 build/p06-timing-audit-20261005/branch_probe.py
```

The archive preserves the original failed fixture/comparison experiments as
well as the accepted diagnosis. These are not a full architectural regression,
fitted timing result or acceptance of a timing correction.
