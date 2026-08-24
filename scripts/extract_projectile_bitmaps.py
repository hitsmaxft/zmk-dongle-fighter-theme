#!/usr/bin/env python3
"""Extract the low-frame projectile sprites used by fighter playback.

The compressed projectile archive and mapping coordinates come from the
Kak2X/kof96 disassembly.  Unlike character bodies, these graphics are loaded
into a shared VRAM range at round start, so they need a small dedicated
extractor.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


PALETTE = (255, 170, 85, 0)


def s8(value: int) -> int:
    return value - 256 if value >= 128 else value


def decompress_lzss(data: bytes) -> bytes:
    header = data[0] | data[1] << 8
    command_count = (header & 0x3FFF) + 1
    split = 4 - ((header >> 14) & 0x03)
    count_mask = (1 << split) - 1
    source = 2
    output = bytearray()
    for _ in range(command_count):
        command = data[source] if source < len(data) else 0
        source += 1
        for bit in range(7, -1, -1):
            value = data[source] if source < len(data) else 0
            source += 1
            if command & (1 << bit):
                offset = -(value >> split) - 1
                for _ in range((value & count_mask) + 1):
                    output.append(output[offset])
            else:
                output.append(value)
    return bytes(output)


def character_projectile_gfx(
    archive: bytes, ranges: list[tuple[int, int]]
) -> bytes:
    # The game reserves the first two 8x8 tiles as transparent.
    output = bytearray(32)
    for offset, tile_count in ranges:
        output.extend(archive[offset : offset + tile_count * 16])
    return bytes(output)


def decode_8x16(data: bytes, tile_id: int) -> list[list[int]]:
    tile_id &= 0x3E
    raw = data[tile_id * 16 : tile_id * 16 + 32]
    if len(raw) != 32:
        raise ValueError(f"tile {tile_id:02x} exceeds projectile GFX block")
    return [
        [
            (((raw[y * 2 + 1] >> bit) & 1) << 1)
            | ((raw[y * 2] >> bit) & 1)
            for bit in range(7, -1, -1)
        ]
        for y in range(16)
    ]


def render_mapping(
    gfx: bytes,
    objects: list[tuple[int, int, int]],
    x_offset: int,
    y_offset: int,
    header_xflip: bool = False,
) -> tuple[int, int, list[list[int]], int, int]:
    canvas: dict[tuple[int, int], int] = {}
    for raw_y, raw_x, raw_tile in objects:
        tile_xflip = bool(raw_tile & 0x40)
        tile_yflip = bool(raw_tile & 0x80)
        sprite = decode_8x16(gfx, raw_tile)
        if tile_xflip:
            sprite = [row[::-1] for row in sprite]
        if tile_yflip:
            sprite = sprite[::-1]
        object_x = s8(raw_x)
        x = s8(x_offset) + (-object_x - 8 if header_xflip else object_x)
        y = s8(y_offset) + s8(raw_y)
        if header_xflip:
            sprite = [row[::-1] for row in sprite]
        for py, row in enumerate(sprite):
            for px, color in enumerate(row):
                if color:
                    canvas.setdefault((x + px, y + py), color)
    left = min(x for x, _ in canvas)
    top = min(y for _, y in canvas)
    right = max(x for x, _ in canvas)
    bottom = max(y for _, y in canvas)
    pixels = [[0] * (right - left + 1) for _ in range(bottom - top + 1)]
    for (x, y), color in canvas.items():
        pixels[y - top][x - left] = color
    return len(pixels[0]), len(pixels), pixels, left, top


def bmp8(width: int, height: int, pixels: list[list[int]]) -> bytes:
    row_size = (width + 3) & ~3
    image_size = row_size * height
    palette = bytearray()
    for index in range(256):
        shade = PALETTE[index] if index < 4 else 0
        palette += bytes((shade, shade, shade, 0))
    pixel_data = bytearray()
    for row in reversed(pixels):
        pixel_data += bytes(row) + bytes(row_size - width)
    offset = 14 + 40 + len(palette)
    return (
        b"BM"
        + struct.pack("<IHHI", offset + image_size, 0, 0, offset)
        + struct.pack(
            "<IiiHHIIiiII",
            40,
            width,
            height,
            1,
            8,
            0,
            image_size,
            2835,
            2835,
            256,
            4,
        )
        + bytes(palette)
        + bytes(pixel_data)
    )


def main() -> None:
    module_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--disasm", type=Path, required=True)
    parser.add_argument(
        "-o", "--output", type=Path, default=module_root / "assets/projectile_bitmaps"
    )
    args = parser.parse_args()
    archive = decompress_lzss(
        (args.disasm / "data/gfx/play_projectiles.lzc").read_bytes()
    )
    definitions = {
        "athena_shcryst_swirl": {
            "ranges": [(0x02E0, 0x20)],
            "objects": [(0x28, 0xF8, 0x02), (0x28, 0x00, 0x04)],
            "x_offset": 0x00,
            "y_offset": 0x00,
        },
        "athena_shcryst_thrown_0": {
            "ranges": [(0x02E0, 0x20)],
            "objects": [(0x28, 0xF8, 0x02), (0x28, 0x00, 0x04)],
            "x_offset": 0x00,
            "y_offset": 0x0C,
        },
        "athena_shcryst_thrown_1": {
            "ranges": [(0x02E0, 0x20)],
            "objects": [
                (0x20, 0xFC, 0x08), (0x30, 0xFC, 0x88),
                (0x20, 0xF4, 0x0A), (0x20, 0x04, 0x4A),
                (0x30, 0xF4, 0x8A), (0x30, 0x04, 0xCA),
            ],
            "x_offset": 0x00,
            "y_offset": 0x0C,
        },
        "athena_shcryst_thrown_2": {
            "ranges": [(0x02E0, 0x20)],
            "objects": [(0x28, 0xF8, 0x06), (0x28, 0x00, 0x46)],
            "x_offset": 0x00,
            "y_offset": 0x0C,
        },
        "geese_raging_storm_s0": {
            "ranges": [(0x0760, 0x1E)],
            "objects": [
                (0x10, 0xEF, 0x02), (0x06, 0xF4, 0x04),
                (0xF6, 0xF7, 0x06), (0x20, 0xEE, 0x08),
                (0x30, 0xEE, 0x0A), (0x30, 0xF6, 0x0C),
            ],
            "x_offset": 0xF8,
            "y_offset": 0x00,
        },
        "geese_raging_storm_s1": {
            "ranges": [(0x0760, 0x1E)],
            "objects": [
                (0x10, 0xEF, 0x02), (0x06, 0xF4, 0x04),
                (0xF6, 0xF7, 0x06), (0x20, 0xEE, 0x08),
                (0x30, 0xEE, 0x0A), (0x30, 0xF6, 0x0C),
            ],
            "x_offset": 0x08,
            "y_offset": 0x00,
            "header_xflip": True,
        },
        "geese_raging_storm_s2": {
            "ranges": [(0x0760, 0x1E)],
            "objects": [
                (0x10, 0xEF, 0x02), (0x06, 0xF4, 0x04),
                (0xF6, 0xF7, 0x06), (0x20, 0xEE, 0x08),
                (0x30, 0xEE, 0x0A), (0x30, 0xF6, 0x0C),
            ],
            "x_offset": 0x04,
            "y_offset": 0x00,
        },
        "geese_raging_storm_s3": {
            "ranges": [(0x0760, 0x1E)],
            "objects": [
                (0x10, 0xEF, 0x02), (0x06, 0xF4, 0x04),
                (0xF6, 0xF7, 0x06), (0x20, 0xEE, 0x08),
                (0x30, 0xEE, 0x0A), (0x30, 0xF6, 0x0C),
            ],
            "x_offset": 0xFC,
            "y_offset": 0x00,
            "header_xflip": True,
        },
        "iori_fire_a": {
            "ranges": [(0x0B80, 0x18)],
            "objects": [(0x15, 0xE2, 0x12), (0x1B, 0xEA, 0x14),
                        (0x18, 0xF2, 0x16), (0x18, 0xFA, 0x18)],
            "x_offset": 0x0C,
            "y_offset": 0x18,
        },
        "iori_fire_b": {
            "ranges": [(0x0B80, 0x18)],
            "objects": [(0x15, 0xE2, 0x12), (0x1B, 0xEA, 0x14),
                        (0x18, 0xF2, 0x16), (0x18, 0xFA, 0x18)],
            "x_offset": 0xF4,
            "y_offset": 0x18,
            "header_xflip": True,
        },
        "mrkarate_haoh_d": {
            "ranges": [(0x0940, 0x0E), (0x01C0, 0x12)],
            "objects": [
                (0x20, 0xF8, 0x02), (0x20, 0x00, 0x04), (0x20, 0x08, 0x06),
                (0x20, 0x10, 0x08), (0x10, 0xFB, 0x0A), (0x10, 0x03, 0x0C),
                (0x10, 0x0B, 0x0E), (0x30, 0xF8, 0x82), (0x30, 0x00, 0x84),
                (0x30, 0x08, 0x86), (0x30, 0x10, 0x88), (0x40, 0xFB, 0x8A),
                (0x40, 0x03, 0x8C), (0x40, 0x0B, 0x8E),
            ],
            "x_offset": 0,
            "y_offset": 0,
        },
        "mrkarate_haoh_s": {
            "ranges": [(0x0940, 0x0E), (0x01C0, 0x12)],
            "objects": [
                (0x28, 0xF0, 0x10), (0x28, 0xF8, 0x12), (0x28, 0x00, 0x14),
                (0x18, 0xF0, 0x16), (0x18, 0xF8, 0x18), (0x18, 0x00, 0x1A),
                (0x38, 0xF0, 0x96), (0x38, 0xF8, 0x98), (0x38, 0x00, 0x9A),
            ],
            "x_offset": 0x06,
            "y_offset": 0,
        },
        "terry_geyser_main": {
            "ranges": [(0x0000, 0x1C)],
            "objects": [
                (0x20, 0xE0, 0x02), (0x20, 0xE8, 0x04), (0x20, 0xF0, 0x06),
                (0x30, 0xE0, 0x08), (0x30, 0xE8, 0x0A), (0x30, 0xF0, 0x0C),
                (0x30, 0xF8, 0x0E), (0x40, 0xE0, 0x10), (0x40, 0xE8, 0x12),
                (0x40, 0xF0, 0x14), (0x40, 0xF8, 0x16), (0x40, 0x00, 0x18),
                (0x50, 0xE8, 0x1A), (0x50, 0xF0, 0x1C),
                (0x50, 0x00, 0x1A | 0x40), (0x50, 0xF8, 0x1C | 0x40),
            ],
            "x_offset": 0x08,
            "y_offset": 0xE0,
        },
        "terry_geyser_tail": {
            "ranges": [(0x0000, 0x1C)],
            "objects": [
                (0x00, 0xE6, 0x02), (0x00, 0xEE, 0x04), (0x00, 0xF6, 0x06),
                (0x10, 0xE6, 0x08), (0x10, 0xEE, 0x0A), (0x10, 0xF6, 0x0C),
                (0x10, 0xFE, 0x0E),
            ],
            "x_offset": 0x08,
            "y_offset": 0x20,
        },
        "goenitz_tornado_a": {
            "ranges": [(0x0FC0, 0x22)],
            "objects": [
                (0x30, 0xF8, 0x02), (0x20, 0xF8, 0x04),
                (0x20, 0xF0, 0x06), (0x10, 0xF8, 0x08),
                (0x10, 0xF0, 0x0A), (0x00, 0xF8, 0x08),
                (0x00, 0xF0, 0x0A), (0xF0, 0xF8, 0x08),
                (0xF0, 0xF0, 0x0A), (0xE0, 0xF8, 0x08),
                (0xE0, 0xF0, 0x0A), (0xD0, 0xF8, 0x08),
                (0xD0, 0xF0, 0x0A), (0xC0, 0xF8, 0x08),
                (0xC0, 0xF0, 0x0A),
            ],
            "x_offset": 0,
            "y_offset": 0,
        },
        "goenitz_tornado_mid": {
            "ranges": [(0x0FC0, 0x22)],
            "objects": [
                (0x30, 0xFC, 0x0C), (0x20, 0xFC, 0x0E),
                (0x10, 0xFC, 0x0E), (0x00, 0xFC, 0x0E),
                (0xF0, 0xFC, 0x0E), (0xE0, 0xFC, 0x0E),
                (0xD0, 0xFC, 0x0E), (0xC0, 0xFC, 0x0E),
            ],
            "x_offset": 0,
            "y_offset": 0,
        },
        "goenitz_tornado_b": {
            "ranges": [(0x0FC0, 0x22)],
            "objects": [
                (0x30, 0xF8, 0x02), (0x20, 0xF8, 0x04),
                (0x20, 0xF0, 0x06), (0x10, 0xF8, 0x08),
                (0x10, 0xF0, 0x0A), (0x00, 0xF8, 0x08),
                (0x00, 0xF0, 0x0A), (0xF0, 0xF8, 0x08),
                (0xF0, 0xF0, 0x0A), (0xE0, 0xF8, 0x08),
                (0xE0, 0xF0, 0x0A), (0xD0, 0xF8, 0x08),
                (0xD0, 0xF0, 0x0A), (0xC0, 0xF8, 0x08),
                (0xC0, 0xF0, 0x0A),
            ],
            "x_offset": 0,
            "y_offset": 0,
            "header_xflip": True,
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"format": "8-bit indexed BMP", "frames": {}}
    for name, definition in definitions.items():
        gfx = character_projectile_gfx(archive, definition["ranges"])
        width, height, pixels, left, top = render_mapping(
            gfx,
            definition["objects"],
            definition["x_offset"],
            definition["y_offset"],
            bool(definition.get("header_xflip", False)),
        )
        filename = f"{name}.bmp"
        (args.output / filename).write_bytes(bmp8(width, height, pixels))
        manifest["frames"][name] = {
            "file": filename,
            "width": width,
            "height": height,
            "origin_x": left,
            "origin_y": top,
        }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
