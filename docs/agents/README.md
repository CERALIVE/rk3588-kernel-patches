# Agent contract index

Read the relevant full contract before changing its subsystem. Sections are preserved from origin/main.

| Original heading | Contract | Governed paths / scope |
|---|---|---|
| Overview | [overview.md](overview.md) | Overview |
| ROLE IN THE GROUP | [role-in-the-group.md](role-in-the-group.md) | `image-building-pipeline/`, `rk3588-media-island/`, `island/`, `rcawston/rockchip-rk3588-mainline-patches` |
| STRUCTURE | [structure.md](structure.md) | STRUCTURE |
| WHERE TO LOOK | [where-to-look.md](where-to-look.md) | `rebase/<tag>.rules`, `docs/REBASE-<tag>.md`, `ceralive/<NNNN>-*.patch`, `scripts/build-series.py`, `backports/<NNNN>-*.patch`, `backports/README.md`, `scripts/import-lore-series.py`, `island/` |
| KEY FACTS | [key-facts.md](key-facts.md) | `tests/test_island_lane.py`, `docs/EDID-STREAMING-GUARD.md`, `tests/test_hdmirx_avi_colorimetry.py`, `drivers/soc/rockchip/pm_domains.c`, `drivers/pmdomain/rockchip/pm-domains.c`, `patches/`, `scripts/build-series.py --check`, `upstream/` |
| PR TARGETING — READ THIS FIRST | [pr-targeting-read-this-first.md](pr-targeting-read-this-first.md) | `rcawston/rockchip-rk3588-mainline-patches`, `irlserver/srtla_send` |
| CI | [ci.md](ci.md) | `patches/`, `scripts/apply.sh`, `.github/` |
| ANTI-PATTERNS | [anti-patterns.md](anti-patterns.md) | `patches/`, `upstream/`, `ceralive/`, `backports/`, `island/`, `rebase/`, `retired/`, `docs/UPSTREAM-STATUS.md` |
