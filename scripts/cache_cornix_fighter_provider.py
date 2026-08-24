#!/usr/bin/env python3
"""Generate the KOF96 provider into a persistent content-addressed build cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def update_file_hash(digest: hashlib._Hash, root: Path, path: Path) -> None:
    digest.update(path.relative_to(root).as_posix().encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")


def input_digest(
    module_root: Path,
    bitmaps_dir: Path,
    playback_plan: Path,
    profile: str,
    source_ticks_per_display_frame: int,
    allow_source_frame_drop: bool,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"kof96-provider-cache-v4\0")
    digest.update(profile.encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(source_ticks_per_display_frame).encode("ascii"))
    digest.update(b"\0")
    digest.update(str(int(allow_source_frame_drop)).encode("ascii"))
    digest.update(b"\0")
    update_file_hash(
        digest, module_root, module_root / "scripts/generate_cornix_fighter_assets.py"
    )
    update_file_hash(digest, module_root, Path(__file__).resolve())
    update_file_hash(digest, module_root, playback_plan)
    update_file_hash(digest, module_root, bitmaps_dir / "manifest.json")
    for bitmap in sorted(bitmaps_dir.rglob("*.bmp")):
        update_file_hash(digest, module_root, bitmap)
    return digest.hexdigest()


def profile_arguments(profile: str) -> list[str]:
    if profile == "default":
        return []
    if profile == "twenty":
        return ["--enabled-character", "all"]
    if profile == "eighteen":
        excluded = {
            "Leona",
            "Iori",
            "Chizuru",
            "Boss_Kagura",
            "Mature",
            "Mr_Big",
        }
        manifest = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "assets/character_bitmaps/manifest.json"
            ).read_text(
                encoding="utf-8"
            )
        )
        return [
            option
            for name in manifest["characters"]
            if name not in excluded
            for option in ("--enabled-character", name)
        ]
    if profile.startswith("frames-"):
        try:
            frame_count = int(profile.removeprefix("frames-"))
        except ValueError as error:
            raise SystemExit(f"invalid frame profile {profile!r}") from error
        if not 1 <= frame_count <= 127:
            raise SystemExit("frame profile must be in frames-1 through frames-127")
        return [
            "--enabled-character", "all",
            "--frame-limit", f"idle={frame_count}",
            "--frame-limit", f"slow={frame_count}",
            "--frame-limit", f"mid={frame_count}",
            "--frame-limit", f"fast={frame_count}",
        ]
    raise SystemExit(f"unknown KOF96 provider profile {profile!r}")


def atomic_write(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--source-ticks-per-display-frame", type=int, default=2)
    parser.add_argument("--allow-source-frame-drop", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.source_ticks_per_display_frame <= 16:
        parser.error("--source-ticks-per-display-frame must be in 1..16")

    module_root = Path(__file__).resolve().parents[1]
    bitmaps_dir = module_root / "assets/character_bitmaps"
    generator = module_root / "scripts/generate_cornix_fighter_assets.py"
    playback_plan = module_root / "data/fighter_playback.json"
    output = args.output.resolve()
    cache_dir = output.parent
    key_file = cache_dir / "provider.sha256"
    manifest_output = cache_dir / "manifest.json"
    cache_dir.mkdir(parents=True, exist_ok=True)

    generator_args = profile_arguments(args.profile)
    key = input_digest(
        module_root,
        bitmaps_dir,
        playback_plan,
        args.profile,
        args.source_ticks_per_display_frame,
        args.allow_source_frame_drop,
    )
    if output.exists() and key_file.exists() and key_file.read_text(encoding="utf-8").strip() == key:
        print(f"KOF96 provider cache hit: {key[:12]}")
        return

    temporary_dir = cache_dir / f".generate-{os.getpid()}"
    temporary_dir.mkdir(parents=True, exist_ok=False)
    try:
        temporary_header = temporary_dir / output.name
        subprocess.run(
            [
                sys.executable,
                str(generator),
                "--bitmaps",
                str(bitmaps_dir),
                "--character",
                "all",
                "--output-dir",
                str(temporary_dir),
                "--provider-header",
                str(temporary_header),
                "--profile-label",
                args.profile,
                "--playback-plan",
                str(playback_plan),
                "--source-ticks-per-display-frame",
                str(args.source_ticks_per_display_frame),
                *(["--allow-source-frame-drop"] if args.allow_source_frame_drop else []),
                *generator_args,
                "--no-previews",
            ],
            check=True,
        )
        os.replace(temporary_header, output)
        os.replace(temporary_dir / "manifest.json", manifest_output)
        atomic_write(key_file, key + "\n")
    finally:
        shutil.rmtree(temporary_dir, ignore_errors=True)

    print(f"KOF96 provider cache miss: generated {key[:12]}")


if __name__ == "__main__":
    main()
