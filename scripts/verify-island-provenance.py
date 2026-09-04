#!/usr/bin/env python3
"""Verify island/ byte-for-byte against its immutable release asset."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent.parent
ISLAND_DIR: Final = ROOT / "island"
REPOSITORY: Final = "CERALIVE/rk3588-media-island"
TAG: Final = "v2026.9.2"
COMMIT: Final = "1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5"
ASSET: Final = f"rk3588-media-island-{TAG}.mbox.tar"
ASSET_SHA256: Final = (
    "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
)
ASSET_URL: Final = (
    f"https://github.com/{REPOSITORY}/releases/download/{TAG}/{ASSET}"
)
MEMBERS: Final = (
    ("0001-rk3588-media-island-drivers.patch", "0031-rk3588-media-island-drivers.patch"),
    ("0002-video-rockchip-kconfig-makefile-hooks.patch", "0032-video-rockchip-kconfig-makefile-hooks.patch"),
    ("0003-iommu-rockchip-export-for-mpp.patch", "0033-iommu-rockchip-export-for-mpp.patch"),
    ("0004-iommu-dma-expose-iova-domain.patch", "0034-iommu-dma-expose-iova-domain.patch"),
    ("0005-arm64-dts-rk3588-mpp-encoder-nodes.patch", "0035-arm64-dts-rk3588-mpp-encoder-nodes.patch"),
    ("0006-arm64-dts-rk3588-mpp-decoder-nodes.patch", "0036-arm64-dts-rk3588-mpp-decoder-nodes.patch"),
    ("0007-arm64-dts-rk3588-mpp-jpegd-node.patch", "0037-arm64-dts-rk3588-mpp-jpegd-node.patch"),
    ("0008-arm64-dts-rk3588-rga3-vendor-compat.patch", "0038-arm64-dts-rk3588-rga3-vendor-compat.patch"),
    ("0009-arm64-dts-rk3588-rga2-vendor-compat.patch", "0039-arm64-dts-rk3588-rga2-vendor-compat.patch"),
)


def verify(asset_path: Path, lane_dir: Path) -> list[str]:
    problems: list[str] = []
    asset_bytes = asset_path.read_bytes()
    actual_sha256 = hashlib.sha256(asset_bytes).hexdigest()
    if actual_sha256 != ASSET_SHA256:
        return [
            f"{asset_path.name}: sha256 {actual_sha256}, expected {ASSET_SHA256}"
        ]

    with tarfile.open(asset_path, mode="r:") as archive:
        entries: dict[str, tarfile.TarInfo] = {}
        for info in archive.getmembers():
            name = info.name.removeprefix("./")
            if name in entries:
                problems.append(f"{ASSET}: duplicate member {name}")
            entries[name] = info

        for asset_member, lane_member in MEMBERS:
            info = entries.get(asset_member)
            if info is None:
                problems.append(f"{ASSET}: missing member {asset_member}")
                continue
            if not info.isfile():
                problems.append(f"{ASSET}: {asset_member} is not a regular file")
                continue
            extracted = archive.extractfile(info)
            if extracted is None:
                problems.append(f"{ASSET}: cannot read member {asset_member}")
                continue
            expected = extracted.read()
            lane_path = lane_dir / lane_member
            if not lane_path.is_file():
                problems.append(f"{lane_member}: missing from island/")
                continue
            if lane_path.read_bytes() != expected:
                problems.append(
                    f"{lane_member}: differs from release member {asset_member}"
                )

    lane_names = {path.name for path in lane_dir.glob("*.patch")}
    expected_names = {lane_member for _, lane_member in MEMBERS}
    for unexpected in sorted(lane_names - expected_names):
        problems.append(f"{unexpected}: unexpected island/ member")
    return problems


def run(asset_path: Path, lane_dir: Path) -> int:
    try:
        problems = verify(asset_path, lane_dir)
    except (OSError, tarfile.TarError) as exc:
        print(f"FAIL {asset_path}: {exc}", file=sys.stderr)
        return 1
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print(
        f"OK   {len(MEMBERS)} island members match {REPOSITORY} {TAG} "
        f"({COMMIT}), asset sha256 {ASSET_SHA256}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset",
        type=Path,
        help=f"read a cached {ASSET} instead of downloading it",
    )
    parser.add_argument("--lane-dir", type=Path, default=ISLAND_DIR)
    args = parser.parse_args()

    if args.asset is not None:
        return run(args.asset, args.lane_dir)

    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / ASSET
        try:
            with urllib.request.urlopen(ASSET_URL, timeout=60) as response:
                destination.write_bytes(response.read())
        except (OSError, urllib.error.URLError) as exc:
            print(f"FAIL download {ASSET_URL}: {exc}", file=sys.stderr)
            return 1
        return run(destination, args.lane_dir)


if __name__ == "__main__":
    sys.exit(main())
