<!-- Moved verbatim from AGENTS.md on 2026-10-05 by lean-rules-docs-landing-latam -->

## PR TARGETING — READ THIS FIRST

**This repository is a GitHub fork, so `gh pr create` defaults its base to
`rcawston/rockchip-rk3588-mainline-patches`.** That is the exact failure mode the
root `AGENTS.md` records as having already sent a `srtla-send-rs` PR to
`irlserver/srtla_send`. Always be explicit:

```bash
gh pr create --repo CERALIVE/rk3588-kernel-patches --base main
gh pr view <n> --json url -q .url   # MUST be https://github.com/CERALIVE/...
```

Keep **only** `origin` (CERALIVE) attached at rest. If an upstream-sync ever needs
the parent, add it transiently as `rcawston` (**never** as `upstream`), fetch with
an explicit refspec, pin-verify the SHA, and remove it before any push or PR.

An upstream-sync PR that carries a real `git merge` commit must be **merge-commit
merged, never squashed** — squashing discards the second parent, so `git merge-base`
never advances and every later sync replays as phantom conflicts.

