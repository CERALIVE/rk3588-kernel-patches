# HDMI-RX audio v4 — code validation, 2026-09-05

Implementation commit: `36056886e84cb9a91a6e63075fc802246cf47d2c`.
Behavior decisions: [UPSTREAM-STATUS.md](UPSTREAM-STATUS.md#hdmi-rx-audio-v4-reconciliation--2026-09-05).

| Gate | Observed result |
|---|---|
| Full stdlib unit suite | **70 tests passed** |
| `scripts/check-series-ledger.py` | **31 members, 31 status rows**, consistent |
| Candidate matrix | **28 rows × 13 fields**, complete |
| `scripts/build-series.py --check` | **32 files in sync**: 31 patches plus `series` |
| Payload parity | **All 31 patches** match their source-lane payload |
| Island provenance | **Nine members** match the published v2026.9.2 asset |
| `scripts/apply.sh --keep <clean-tree>` | **All 31 members git-am applied**; every post-apply assertion passed |
| Applied-tree audio checks | **Seven tests passed**, including six compiled helper scenarios and mailbox parsing; lifecycle call sites and both boards' DT status also asserted |
| Checkpatch on `ceralive/0046`–`0049` | **Zero errors, zero warnings**, using `--no-tree --no-signoff` |
| Shellcheck | **Warning severity clean**; default severity still reports existing informational SC1091/SC2016 findings |
| LSP error diagnostics | **Clean** for the generator, audio test, and apply script |
| Retirement byte preservation | Git records all three source moves as **100% identical** |

The gate verified both pinned coordinates, not just a same-named branch:

- kernel tag: `v7.2`;
- tag object: `237a1c39e8dfd3e1c6f1f023eea37a48ec04cc63`;
- peeled commit: `8d3ae59288f1e7d58d76558a6ee96d533bc5019f`.

The existing cached Linux tree contained pre-existing local changes. The gate
correctly refused to reset it; those changes were left untouched. A fresh
repo-local clone supplied the successful gate tree. The first full application
also caught the canonical trailing-context count issue documented in
[REBASE-v7.2.md](REBASE-v7.2.md); its repair changes generated hunk counts only,
not imported source bytes. Existing island EOF-blank warnings remain unchanged.

## Reproduce

Host requirements: Python 3 (stdlib only), Git, and a C compiler named `cc`.
The compiler runs small extracted-helper tests, **not a kernel build**.

```sh
python3 -m unittest discover -s tests
python3 scripts/check-series-ledger.py
KEEP_TREE=1 scripts/apply.sh
```

The helper tests cover clock refusal without false state publication, successful
fs×128 programming, invalid/768 kHz rejection before clock access, independent
44.1/48 kHz ACR vectors, disarm-before-drain, and multichannel-to-stereo routing.
They do not simulate real workqueue scheduling, physical FIFO drift, or sound
quality. The applied-tree checks cover the actual integration call sites.

## Explicit limits

No kernel compilation, image build, board connection, 30-minute audio drill,
suspend drill, or multichannel hardware qualification was performed. v4's known
second-suspend-cycle silence remains unfixed. ALSA jack notifications and idle
pre-lock polling are intentionally retired, not claimed as upstream-equivalent.
The required engine card-name string is **`RK3588 HDMI-IN`**; cerastream was not
changed. The EDID-guard and colorimetry commits were not rewritten; only their
generated mailbox slot totals changed from 41 to 49.
