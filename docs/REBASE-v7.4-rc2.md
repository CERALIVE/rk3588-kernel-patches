# Rebase ledger: v7.4-rc2

## HDMI-RX context revisions, 2026-11-11

The candidate is `v7.4-rc2`, tag object
`fd9230005e85472b81c1c7c16afe93dd878996b1`, commit
`7475ea8b58616b33c04afb976cf0fbaad9dd63fb`.

Upstream `e8554ac860356f1f4cd9bce454271dce1ed35fc1` removed
`u32 color_depth;` from `struct snps_hdmirx_dev`. The two first-party
members below used that field only as patch context. Remove that context
line and reduce each side's hunk count by one; retain every added and
removed payload line byte-for-byte. All other hunks remain unchanged.

| Member and hunk | Old header | New header | Intent preserved |
|---|---|---|---|
| `0026`, hunk 1, `struct snps_hdmirx_dev` | `@@ -205,7 +206,19 @@` | `@@ -205,6 +206,18 @@` | The raw register lock, four raw IRQ-save guards and raw lock initializer are unchanged. |
| `0041`, hunk 2, `struct snps_hdmirx_dev` | `@@ -214,6 +225,7 @@` | `@@ -214,5 +225,6 @@` | The colorimetry field, pure mapping functions, format reporting and source-change event behavior are unchanged. |

Both hunks previously had this leading context:

```c
	u32 edid_blocks_written;
	u32 cur_fmt_fourcc;
	u32 color_depth;
```

Both now have:

```c
	u32 edid_blocks_written;
	u32 cur_fmt_fourcc;
```

In `0026`, the next removed payload line is
`spinlock_t rst_lock; /* to lock register access */`; its replacement
comment and `raw_spinlock_t` remain identical. In `0041`, the next added
payload line remains `struct hdmirx_colorimetry colorimetry;`, followed by
the unchanged raw-lock comment supplied by `0026`.

The old source patches reject these struct hunks on the candidate.
The revised members apply with plain sequential `git am`.
This section records only the context revisions; the complete base-bump
disposition ledger and cutover runbook are still pending.
No kernel build or board validation is claimed here.
