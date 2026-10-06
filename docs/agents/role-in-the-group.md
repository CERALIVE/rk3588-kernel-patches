<!-- Moved verbatim from AGENTS.md on 2026-10-05 by lean-rules-docs-landing-latam -->

## ROLE IN THE GROUP

Holds the **mainline-track RK3588 kernel patch series** for CeraLive: the
`rk3588-media-island` release series, HDMI-RX fixes, a `system-uncached` dma-heap,
seven backported **unmerged lore postings**, and board Type-C policy patches —
assembled as one `git am` mailbox series pinned to an exact kernel tag.

The base is **`v7.2`**. **32 members are active across
50 slots** — `0004` was never published, and seventeen retired ordinals stay
burned. Board evidence quoted anywhere in this repo was measured at the previous
`v7.1.7` base and is historical here.

Produces **patch text only** — no `.deb`, no kernel, no image artifact. It is
therefore **NOT in the device image `REPOS` array** and has **no `versions.yaml`
pin**, for the same reason `ceralive-infra` has none: there is nothing for the
image pipeline to fetch.

Relates to:
- `image-building-pipeline/` — the production downstream consumer. Its immutable
  `patches_commit` selects this series for the shipped mainline 7.2 kernel.
- `rk3588-media-island/` — the source repository that publishes the nine mailbox
  members consumed byte-preserved through `island/`.

Upstream: GitHub fork of
[`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches),
imported at `e13a311` (2026-07-01).

