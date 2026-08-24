#!/usr/bin/env python3
"""Extract every playable-character animation frame from Nettou KOF '96 (GB).

The pixels are read from the supplied ROM.  The matching Kak2X/kof96
disassembly supplies labels, animation grouping, and sprite/OAM coordinates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path


EXPECTED_JP_SHA1 = "63f25bff422a591907b83ab9f14709e938172839"
UPSTREAM = "https://github.com/Kak2X/kof96"
PALETTE = (255, 170, 85, 0)
CHARACTER_DIR = {
    "Kyo": "Kyo",
    "Daimon": "Daimon",
    "Terry": "Terry",
    "Andy": "Andy",
    "Ryo": "Ryo",
    "Robert": "Robert",
    "Athena": "Athena",
    "Mai": "Mai",
    "Leona": "Leona",
    "OLeona": "Orochi_Leona",
    "Geese": "Geese",
    "Krauser": "Krauser",
    "MrBig": "Mr_Big",
    "Iori": "Iori",
    "Mature": "Mature",
    "Chizuru": "Chizuru",
    "Kagura": "Boss_Kagura",
    "Goenitz": "Goenitz",
    "MrKarate": "Mr_Karate",
    "OIori": "Orochi_Iori",
}


@dataclass(frozen=True)
class Gfx:
    label: str
    path: Path
    rom_offset: int
    size: int


@dataclass
class Header:
    label: str
    part: str
    flags: int
    gfx_label: str
    map_ref: str
    x_offset: int
    y_offset: int
    objects: list[tuple[int, int, int]] | None


@dataclass(frozen=True)
class Move:
    logical_name: str
    table: str
    unused: bool


def s8(value: int) -> int:
    return value - 256 if value >= 128 else value


def parse_num(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value, 0)


def parse_flags(value: str) -> int:
    constants = {"OLF_XFLIP": 0x20, "OLF_YFLIP": 0x40, "$00": 0}
    return sum(constants[token.strip()] for token in value.split("|"))


def active_jp_lines(text: str) -> list[str]:
    """Apply the few build conditionals used by the Japanese revision."""
    values = {"REV_VER_2": False, "FIX_BUGS": False, "REV_LANG_EN": False}
    result: list[str] = []
    stack: list[tuple[bool, bool]] = []
    active = True
    for line in text.splitlines():
        stripped = line.strip()
        match = re.fullmatch(r"IF\s+(!?)(REV_VER_2|FIX_BUGS|REV_LANG_EN)", stripped)
        if match:
            condition = values[match.group(2)]
            if match.group(1):
                condition = not condition
            stack.append((active, condition))
            active = active and condition
            continue
        if stripped == "ELSE" and stack:
            parent, condition = stack[-1]
            active = parent and not condition
            stack[-1] = (parent, not condition)
            continue
        if stripped == "ENDC" and stack:
            parent, _ = stack.pop()
            active = parent
            continue
        if active:
            result.append(line)
    return result


def build_gfx_index(disasm: Path, rom: bytes) -> dict[str, Gfx]:
    index: dict[str, Gfx] = {}
    pattern = re.compile(r'^(GFX_Char_\w+):\s+INCBIN\s+"([^"]+)"')
    # Most bodies occupy one bank each (0B-1B); four overflow blocks are at
    # the start of 1C.
    for bank in range(0x0B, 0x1D):
        source = disasm / "src" / f"bank{bank:02X}.asm"
        offset = bank * 0x4000
        found = 0
        for line in active_jp_lines(source.read_text(encoding="utf-8")):
            match = pattern.match(line.strip())
            if not match:
                continue
            label, relative = match.groups()
            asset = disasm / relative
            expected = asset.read_bytes()
            actual = rom[offset : offset + len(expected)]
            if actual != expected:
                raise ValueError(
                    f"ROM mismatch at 0x{offset:05X} for {label} ({relative})"
                )
            index[label] = Gfx(label, asset, offset, len(expected))
            offset += len(expected)
            found += 1
        if not found:
            raise ValueError(f"no character graphics found in {source}")
    return index


def parse_obj_sources(disasm: Path) -> tuple[
    dict[str, list[tuple[str, str | None]]], dict[str, Header]
]:
    tables: dict[str, list[tuple[str, str | None]]] = {}
    headers: dict[str, Header] = {}
    object_maps: dict[str, list[tuple[int, int, int]]] = {}
    for source in sorted((disasm / "data" / "objlst" / "char").glob("*.asm")):
        lines = active_jp_lines(source.read_text(encoding="utf-8"))

        # Pointer tables are a linear stream.  Some labels intentionally point
        # into the middle of another table, so resolve each label up to the next
        # $FFFF terminator rather than stopping at the next label.
        stream: list[tuple[str, str | None] | None] = []
        starts: dict[str, int] = {}
        in_pointer_area = True
        for line in lines:
            stripped = line.strip()
            match = re.match(r"^(OBJLstPtrTable_\w+):", stripped)
            if match and in_pointer_area:
                starts[match.group(1)] = len(stream)
                continue
            if stripped.startswith("OBJLstHdr"):
                in_pointer_area = False
            if not in_pointer_area or not stripped.startswith("dw "):
                continue
            values = [v.strip() for v in stripped[3:].split(";")[0].split(",")]
            if values == ["OBJLSTPTR_NONE"]:
                stream.append(None)
            elif values and values[0].startswith("OBJLstHdrA_"):
                second = None if len(values) < 2 or values[1] == "OBJLSTPTR_NONE" else values[1]
                stream.append((values[0], second))
        for label, start in starts.items():
            entries: list[tuple[str, str | None]] = []
            for entry in stream[start:]:
                if entry is None:
                    break
                entries.append(entry)
            if not entries:
                raise ValueError(f"empty pointer table: {label}")
            tables[label] = entries

        header_positions = []
        for i, line in enumerate(lines):
            match = re.match(r"^(OBJLstHdr[AB]_\w+):", line.strip())
            if match:
                header_positions.append((i, match.group(1)))
        for position_index, (start, label) in enumerate(header_positions):
            end = (
                header_positions[position_index + 1][0]
                if position_index + 1 < len(header_positions)
                else len(lines)
            )
            block = lines[start + 1 : end]
            bin_at = next(
                (i for i, line in enumerate(block) if line.strip().startswith(".bin:")), None
            )
            metadata_lines = block if bin_at is None else block[:bin_at]
            directives = [
                line.split(";", 1)[0].strip()
                for line in metadata_lines
                if line.strip().startswith(("db ", "dw ", "dpr "))
            ]
            objects = None
            if bin_at is not None:
                data_directives = [
                    line.split(";", 1)[0].strip()[3:]
                    for line in block[bin_at + 1 :]
                    if line.strip().startswith("db ")
                ]
                count = parse_num(data_directives[0])
                objects = []
                for values in data_directives[1 : 1 + count]:
                    y, x, tile = (parse_num(v) for v in values.split(","))
                    objects.append((y, x, tile))
                if len(objects) != count:
                    raise ValueError(f"truncated object list: {label}")
                object_maps[label] = objects

            # The Japanese build has one mapping-only label whose actual header
            # was added in revision 2.  It remains a valid .bin target.
            if not directives:
                continue
            part = "A" if label.startswith("OBJLstHdrA_") else "B"
            if part == "A":
                flags = parse_flags(directives[0][3:])
                gfx_label = directives[3][4:].strip()
                map_ref = directives[4][3:].strip()
                x_offset = parse_num(directives[5][3:])
                y_offset = parse_num(directives[6][3:])
            else:
                flags = parse_flags(directives[0][3:])
                gfx_label = directives[1][4:].strip()
                map_ref = directives[2][3:].strip()
                x_offset = parse_num(directives[3][3:])
                y_offset = parse_num(directives[4][3:])

            headers[label] = Header(
                label,
                part,
                flags,
                gfx_label,
                map_ref,
                x_offset,
                y_offset,
                objects,
            )

    for header in headers.values():
        if header.objects is not None:
            continue
        if header.map_ref == ".bin":
            target = header.label
        else:
            target = header.map_ref.removesuffix(".bin")
        if target not in object_maps:
            raise ValueError(f"unresolved object-list reference: {header.label} -> {target}")
        header.objects = object_maps[target]
    return tables, headers


def parse_moves(disasm: Path) -> dict[str, list[Move]]:
    lines = active_jp_lines((disasm / "src" / "bank03.asm").read_text(encoding="utf-8"))
    moves: dict[str, list[Move]] = {}
    character: str | None = None
    for line in lines:
        stripped = line.strip()
        table_match = re.fullmatch(r"MoveAnimTbl_(\w+):", stripped)
        if table_match:
            character = table_match.group(1)
            if character in CHARACTER_DIR:
                moves[character] = []
            else:
                character = None
            continue
        if character is None or not stripped.startswith("mMvAnDef "):
            continue
        ptr_match = re.match(r"mMvAnDef\s+(OBJLstPtrTable_\w+)", stripped)
        name_match = re.search(r";\s*(MOVE_[A-Z0-9_]+)\s*$", stripped)
        if not ptr_match or not name_match:
            raise ValueError(f"cannot parse move: {line}")
        moves[character].append(
            Move(name_match.group(1), ptr_match.group(1), ";X" in stripped)
        )
    missing = set(CHARACTER_DIR) - set(moves)
    if missing:
        raise ValueError(f"missing move tables: {sorted(missing)}")
    return moves


def decode_8x16(data: bytes, tile_id: int) -> list[list[int]]:
    tile_id &= 0xFE
    start = tile_id * 16
    raw = data[start : start + 32]
    if len(raw) != 32:
        raise ValueError(f"tile {tile_id:02X} exceeds a {len(data)}-byte GFX block")
    pixels: list[list[int]] = []
    for y in range(16):
        lo, hi = raw[y * 2 : y * 2 + 2]
        pixels.append(
            [(((hi >> bit) & 1) << 1) | ((lo >> bit) & 1) for bit in range(7, -1, -1)]
        )
    return pixels


def place_header(
    canvas: dict[tuple[int, int], int], header: Header, gfx: Gfx, rom: bytes
) -> None:
    assert header.objects is not None
    data = rom[gfx.rom_offset : gfx.rom_offset + gfx.size]
    flip_x = bool(header.flags & 0x20)
    flip_y = bool(header.flags & 0x40)
    for raw_y, raw_x, tile_id in header.objects:
        x = s8(header.x_offset) + (-s8(raw_x) - 8 if flip_x else s8(raw_x))
        y = s8(header.y_offset) + (80 - s8(raw_y) if flip_y else s8(raw_y))
        sprite = decode_8x16(data, tile_id)
        if flip_x:
            sprite = [row[::-1] for row in sprite]
        if flip_y:
            sprite = sprite[::-1]
        for py, row in enumerate(sprite):
            for px, color in enumerate(row):
                if color:
                    # Set A is earlier in OAM and therefore wins overlaps.
                    canvas.setdefault((x + px, y + py), color)


def bmp8(width: int, height: int, pixels: list[list[int]]) -> bytes:
    row_size = (width + 3) & ~3
    image_size = row_size * height
    palette = bytearray()
    for index in range(256):
        shade = PALETTE[index] if index < 4 else 0
        palette += bytes((shade, shade, shade, 0))
    pixel_data = bytearray()
    for row in reversed(pixels):
        pixel_data += bytes(row)
        pixel_data += bytes(row_size - width)
    offset = 14 + 40 + len(palette)
    file_header = b"BM" + struct.pack("<IHHI", offset + image_size, 0, 0, offset)
    dib = struct.pack(
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
    return file_header + dib + bytes(palette) + bytes(pixel_data)


def animation_name(character: str, logical_name: str) -> str:
    name = logical_name.removeprefix("MOVE_")
    if name.startswith("SHARED_"):
        name = name.removeprefix("SHARED_")
    else:
        normalized = character.upper()
        aliases = {
            "MRKARATE": "MRKARATE",
            "MRBIG": "MRBIG",
            "OLEONA": "OLEONA",
            "OIORI": "OIORI",
        }
        prefix = aliases.get(normalized, normalized)
        if name.startswith(prefix + "_"):
            name = name[len(prefix) + 1 :]
    return name.lower()


def main() -> None:
    module_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--disasm", type=Path, required=True)
    parser.add_argument(
        "-o", "--output", type=Path, default=module_root / "assets/character_bitmaps"
    )
    args = parser.parse_args()

    rom = args.rom.read_bytes()
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if sha1 != EXPECTED_JP_SHA1:
        raise SystemExit(f"unsupported ROM SHA-1: {sha1}; expected {EXPECTED_JP_SHA1}")

    gfx_index = build_gfx_index(args.disasm, rom)
    pointer_tables, headers = parse_obj_sources(args.disasm)
    moves = parse_moves(args.disasm)
    args.output.mkdir(parents=True, exist_ok=True)

    revision = None
    try:
        revision = subprocess.run(
            ["git", "-C", str(args.disasm), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass

    manifest: dict[str, object] = {
        "rom": str(args.rom),
        "rom_sha1": sha1,
        "rom_sha256": sha256,
        "metadata_source": UPSTREAM,
        "metadata_revision": revision,
        "verified_gfx_blocks": len(gfx_index),
        "format": "8-bit indexed BMP; palette 0 is transparent in Game Boy OBJ rendering and is emitted as white",
        "scope": "playable-character body OBJ frames; spawned projectiles and global effects are separate game objects",
        "characters": {},
    }
    total_frames = 0
    for character, character_moves in moves.items():
        directory_name = CHARACTER_DIR[character]
        character_root = args.output / directory_name
        character_info: dict[str, object] = {"animations": {}}
        used_names: dict[str, int] = {}
        for move in character_moves:
            base_name = animation_name(character, move.logical_name)
            occurrence = used_names.get(base_name, 0)
            used_names[base_name] = occurrence + 1
            name = base_name if occurrence == 0 else f"{base_name}_{occurrence + 1}"
            animation_root = character_root / name
            animation_root.mkdir(parents=True, exist_ok=True)
            if move.table not in pointer_tables:
                raise ValueError(f"unknown pointer table: {move.table}")
            frames_info = []
            for frame_number, (header_a_label, header_b_label) in enumerate(
                pointer_tables[move.table]
            ):
                labels = [header_a_label] + ([header_b_label] if header_b_label else [])
                canvas: dict[tuple[int, int], int] = {}
                sources = []
                for header_label in labels:
                    header = headers[header_label]
                    gfx = gfx_index[header.gfx_label]
                    place_header(canvas, header, gfx, rom)
                    sources.append(
                        {
                            "header": header_label,
                            "gfx": header.gfx_label,
                            "rom_offset": gfx.rom_offset,
                            "rom_size": gfx.size,
                        }
                    )
                if canvas:
                    left = min(x for x, _ in canvas)
                    top = min(y for _, y in canvas)
                    right = max(x for x, _ in canvas)
                    bottom = max(y for _, y in canvas)
                    width, height = right - left + 1, bottom - top + 1
                    pixels = [[0] * width for _ in range(height)]
                    for (x, y), color in canvas.items():
                        pixels[y - top][x - left] = color
                else:
                    left = top = 0
                    width = height = 1
                    pixels = [[0]]
                filename = f"{frame_number:03d}.bmp"
                (animation_root / filename).write_bytes(bmp8(width, height, pixels))
                frames_info.append(
                    {
                        "file": filename,
                        "width": width,
                        "height": height,
                        "origin_x": left,
                        "origin_y": top,
                        "sources": sources,
                    }
                )
                total_frames += 1
            character_info["animations"][name] = {
                "logical_move": move.logical_name,
                "pointer_table": move.table,
                "unused_or_placeholder": move.unused,
                "frames": frames_info,
            }
        character_info["animation_count"] = len(character_moves)
        character_info["frame_count"] = sum(
            len(value["frames"]) for value in character_info["animations"].values()
        )
        manifest["characters"][directory_name] = character_info
    manifest["character_count"] = len(moves)
    manifest["frame_count"] = total_frames
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"extracted {total_frames} frames for {len(moves)} characters to {args.output}")


if __name__ == "__main__":
    main()
