# tests/ — the on-board QA harnesses

These scripts run on a **real board** booted into the non-shipping `edge-test`
kernel, and their transcripts are quoted as the evidence that the Wave-6 driver
fixes work. Everything here therefore has two jobs: exercise the driver, and be
impossible to pass vacuously.

## The debugfs fault controls — the driver's own names

The `edge-test` kernel exposes eight one-shot fault controls. **The two drivers
do not use the same counter-naming rule**, and assuming they do cost a board
session (see the 2026-08-10 entry in the effort's `learnings.md`):

| Directory | Knob | Consumed counter | Injected errno |
|---|---|---|---|
| `/sys/kernel/debug/rkvenc-test/` | `delay_task_completion_ms` | `delay_consumed` | — (delay, not a failure) |
| | `fail_service_attach_once` | `fail_service_attach_once_consumed` | `ENOMEM` |
| | `fail_ccu_attach_once` | `fail_ccu_attach_once_consumed` | `ENODEV` |
| | `fail_irq_request_once` | `fail_irq_request_once_consumed` | `EBUSY` |
| | `fail_clock_enable_once` | `fail_clock_enable_once_consumed` | `EIO` |
| | `fail_session_alloc_once` | `fail_session_alloc_once_consumed` | `ENOMEM` |
| `/sys/kernel/debug/hdmirx-audio-test/` | `delay_worker_ms` | `delay_worker_consumed` | — |
| | `fail_clk_set_rate_once` | `fail_clk_set_rate_consumed` | `EIO` |

rkvenc registers its knobs through a helper that appends `_consumed` to the
**full** knob name, so a knob ending in `_once` yields `…_once_consumed`
(`patches/0013`). HDMI-RX registers its two counters by hand, without the
`_once` (`patches/0017`). The delay knobs are the third shape again.

No harness spells a counter name. `qa_arm <knob> <value>` resolves it from the
table in `lib/qa-common.sh`, and `qa_verify_controls_against_patches` re-derives
that table from the driver sources in `patches/` — so the harness and the kernel
cannot drift apart without a self-test going red on the workstation.

## Asserting an errno

A failed write reaches the shell as a **strerror sentence**
(`printf: write error: Cannot allocate memory`), never as the symbol the driver
returned. Assertions therefore go through `qa_write_expect_errno` /
`qa_errno_matches`, which accept the raw syscall errno (preferred), the C-locale
strerror string, or the bare symbol. `qa-write-errno` supplies the raw errno and
is built beside the ioctl harness; without it the shell's own text is parsed
under `LC_ALL=C`.

## Running the self-tests — no hardware, no root

Every harness has a `--self-test` that runs entirely on a workstation, against a
synthetic debugfs built by `lib/qa-fixture.sh` from the same driver-verified
table the real run uses:

```sh
tests/rkvenc-fault-qa.sh      --self-test
tests/hdmirx-audio-fault-qa.sh --self-test
tests/rkvenc-unbind.sh        --self-test
tests/build-rkvenc-harness.sh --self-test
```

Run these **before** every board session. They assert the harness's own
bookkeeping — right node names, right errno matching, no unset-variable abort
under `set -u`, and that an ignored or twice-consumed knob is a FAILURE.

The fixture simulates the driver's one-shot bookkeeping and **nothing else**. It
is not a fake driver, and a claim about driver behaviour still needs a board.

## Copying to a board

`lib/` is **required**, not optional — the harnesses die immediately without it:

```
tests/rkvenc-fault-qa.sh
tests/hdmirx-audio-fault-qa.sh
tests/rkvenc-unbind.sh
tests/lib/qa-common.sh
tests/lib/qa-fixture.sh
<out>/rkvenc-invalid-ioctl      # built by build-rkvenc-harness.sh
<out>/qa-write-errno            # built by build-rkvenc-harness.sh
<out>/expected-errno.tsv
```

`--debugfs <dir>` points a harness at a different controls directory, which is
what the fixture legs use and what makes a dry run possible off-board.
