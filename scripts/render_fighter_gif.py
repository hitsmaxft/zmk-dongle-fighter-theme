#!/usr/bin/env python3
"""Render a firmware-equivalent fighter action as a dependency-free GIF."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

import generate_cornix_fighter_assets as fighter


SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64


def frame_x(
    origin_x: int,
    target_x: int,
    frame_count: int,
    frame_index: int,
    movement_steps: list[int] | None = None,
    return_step: int | None = None,
) -> int:
    if frame_count <= 1 or frame_index == 0 or origin_x <= target_x:
        return origin_x
    if return_step is not None:
        frame_index = min(frame_index, frame_count - 1)
        distance = origin_x - target_x
        if frame_index < return_step:
            movement_count = sum(movement_steps[1:return_step])
            movement_index = sum(movement_steps[1 : frame_index + 1])
            if movement_count == 0:
                return origin_x
            return origin_x - (
                (distance * movement_index + movement_count // 2) // movement_count
            )
        movement_count = sum(movement_steps[return_step:])
        movement_index = sum(movement_steps[return_step : frame_index + 1])
        if movement_count == 0:
            return target_x
        return target_x + (
            (distance * movement_index + movement_count // 2) // movement_count
        )
    if movement_steps is None:
        movement_count = frame_count - 1
        movement_index = min(frame_index, movement_count)
    else:
        movement_count = sum(movement_steps[1:])
        movement_index = sum(movement_steps[1 : min(frame_index, frame_count - 1) + 1])
    if movement_count == 0:
        return origin_x
    if movement_index >= movement_count:
        return target_x
    distance = origin_x - target_x
    return origin_x - (
        (distance * movement_index + movement_count // 2) // movement_count
    )


def parse_order(value: str) -> list[int]:
    try:
        order = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "order must be comma-separated source-frame indices"
        ) from error
    if not order or len(order) > 127:
        raise argparse.ArgumentTypeError("order must contain 1..127 source-frame indices")
    if any(index < 0 for index in order):
        raise argparse.ArgumentTypeError("order indices must be non-negative")
    return order


def parse_movement(value: str) -> list[int]:
    modes = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not modes or len(modes) > 127:
        raise argparse.ArgumentTypeError("movement must contain 1..127 fixed/move modes")
    invalid = next((mode for mode in modes if mode not in ("fixed", "move")), None)
    if invalid is not None:
        raise argparse.ArgumentTypeError(
            f"invalid movement mode {invalid!r}; expected fixed or move"
        )
    return [int(mode == "move") for mode in modes]


def draw_hud(pixels: list[list[int]], left_level: int, right_level: int) -> None:
    digits = (
        (0x7, 0x5, 0x5, 0x5, 0x7),
        (0x2, 0x6, 0x2, 0x2, 0x7),
        (0x7, 0x1, 0x7, 0x4, 0x7),
        (0x7, 0x1, 0x7, 0x1, 0x7),
        (0x5, 0x5, 0x7, 0x1, 0x1),
        (0x7, 0x4, 0x7, 0x1, 0x7),
        (0x7, 0x4, 0x7, 0x5, 0x7),
        (0x7, 0x1, 0x2, 0x2, 0x2),
        (0x7, 0x5, 0x7, 0x5, 0x7),
        (0x7, 0x5, 0x7, 0x1, 0x7),
    )

    def horizontal_line(x: int, y: int, width: int) -> None:
        for px in range(x, x + width):
            if 0 <= px < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                pixels[y][px] = 1

    def number(level: int, x: int) -> None:
        text = str(max(0, min(100, level)))
        width = len(text) * 3 + len(text) - 1
        origin_x = x + (11 - width) // 2
        for digit_index, value in enumerate(text):
            for y, row in enumerate(digits[int(value)]):
                for bit in range(3):
                    if row & (1 << (2 - bit)):
                        pixels[7 + y][origin_x + digit_index * 4 + bit] = 1
        horizontal_line(x, 13, 11)

    def bar(level: int, x: int, fill_from_left: bool) -> None:
        horizontal_line(x, 1, 58)
        horizontal_line(x, 5, 58)
        fill_width = max(0, min(100, level)) * 58 // 100
        fill_x = x if fill_from_left else x + 58 - fill_width
        for y in range(2, 5):
            for px in range(fill_x, fill_x + fill_width):
                if ((px - fill_x) + (y - 2)) % 2 == 0:
                    pixels[y][px] = 1

    bar(left_level, 1, False)
    bar(right_level, 69, True)
    number(left_level, 1)
    number(right_level, 116)


def gif_lzw(indices: bytes) -> bytes:
    # A clear code before every two literals keeps the code width fixed at three
    # bits. The stream is intentionally simple; 128x64 previews remain compact.
    clear_code = 4
    end_code = 5
    codes: list[int] = []
    for start in range(0, len(indices), 2):
        codes.append(clear_code)
        codes.extend(indices[start : start + 2])
    codes.append(end_code)

    packed = bytearray()
    accumulator = 0
    bit_count = 0
    for code in codes:
        accumulator |= int(code) << bit_count
        bit_count += 3
        while bit_count >= 8:
            packed.append(accumulator & 0xFF)
            accumulator >>= 8
            bit_count -= 8
    if bit_count:
        packed.append(accumulator & 0xFF)
    return bytes(packed)


def gif_sub_blocks(data: bytes) -> bytes:
    output = bytearray()
    for start in range(0, len(data), 255):
        block = data[start : start + 255]
        output.append(len(block))
        output.extend(block)
    output.append(0)
    return bytes(output)


def write_gif(
    path: Path,
    frames: list[bytes],
    width: int,
    height: int,
    delays_cs: list[int],
    loop_count: int,
) -> None:
    if not frames or len(frames) != len(delays_cs):
        raise ValueError("GIF frames and delays must be nonempty and have equal length")
    if width <= 0 or height <= 0 or width > 65535 or height > 65535:
        raise ValueError("GIF dimensions must be in 1..65535")
    if any(len(frame) != width * height for frame in frames):
        raise ValueError("GIF frame size does not match its dimensions")

    output = bytearray(b"GIF89a")
    output.extend(struct.pack("<HHBBB", width, height, 0xF0, 0, 0))
    output.extend(b"\x00\x00\x00\xff\xff\xff")
    output.extend(b"\x21\xff\x0bNETSCAPE2.0\x03\x01")
    output.extend(struct.pack("<H", loop_count))
    output.append(0)
    for frame, delay_cs in zip(frames, delays_cs, strict=True):
        output.extend(b"\x21\xf9\x04\x00")
        output.extend(struct.pack("<H", max(1, min(65535, delay_cs))))
        output.extend(b"\x00\x00")
        output.append(0x2C)
        output.extend(struct.pack("<HHHHB", 0, 0, width, height, 0))
        output.append(2)
        output.extend(gif_sub_blocks(gif_lzw(frame)))
    output.append(0x3B)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)


def scale_pixels(pixels: list[list[int]], factor: int) -> bytes:
    output = bytearray()
    for row in pixels:
        expanded = bytes(pixel for pixel in row for _ in range(factor))
        for _ in range(factor):
            output.extend(expanded)
    return bytes(output)


def render_action(
    bitmaps: Path,
    playback_plan_path: Path | None,
    character_name: str,
    sequence: str,
    animation_override: str | None,
    order_override: list[int] | None,
    movement_override: list[int] | None,
    return_step_override: int | None,
    frame_limit: int | None,
    scale: int,
    show_hud: bool,
    left_battery: int,
    right_battery: int,
    source_ticks_per_display_frame: int = fighter.DEFAULT_SOURCE_TICKS_PER_DISPLAY_FRAME,
) -> tuple[list[bytes], list[int], dict[str, object]]:
    manifest = json.loads((bitmaps / "manifest.json").read_text(encoding="utf-8"))
    available = manifest["characters"]
    if character_name not in available:
        raise ValueError(f"unknown character {character_name!r}")
    character = available[character_name]
    animations = fighter.select_animations(character_name, character)
    playback_plan = fighter.load_playback_plan(
        playback_plan_path,
        available,
        source_ticks_per_display_frame,
    )
    playback_entry = playback_plan.get((character_name, sequence))
    animation = animation_override or (
        str(playback_entry["animation"]) if playback_entry is not None else animations[sequence]
    )
    if animation not in character["animations"]:
        raise ValueError(f"{character_name} has no animation named {animation!r}")
    all_frames = character["animations"][animation]["frames"]

    if order_override is not None:
        playback_order = order_override
    elif playback_entry is not None:
        if playback_entry["animation"] != animation:
            raise ValueError(
                f"playback plan {character_name}/{sequence} targets "
                f"{playback_entry['animation']!r}, not selected animation {animation!r}"
            )
        playback_order = list(playback_entry["order"])
    else:
        limit = frame_limit or fighter.CHARACTER_SEQUENCE_FRAME_LIMIT.get(
            character_name, {}
        ).get(sequence, fighter.SEQUENCE_FRAME_LIMIT[sequence])
        playback_order = fighter.sample_frame_indices(len(all_frames), limit)

    if movement_override is not None:
        movement_steps = movement_override
    elif order_override is None and playback_entry is not None:
        movement_steps = playback_entry.get("movement_steps")
    else:
        movement_steps = None
    if return_step_override is not None:
        return_step = return_step_override
    elif order_override is None and playback_entry is not None:
        return_step = playback_entry.get("return_step")
    else:
        return_step = None
    x_offsets = (
        playback_entry.get("x_offsets")
        if order_override is None and playback_entry is not None
        else None
    )
    y_offsets = (
        playback_entry.get("y_offsets")
        if order_override is None and playback_entry is not None
        else None
    )
    frame_durations_ms = (
        playback_entry.get("durations_ms")
        if order_override is None and playback_entry is not None
        else None
    )

    if len(playback_order) > 127:
        raise ValueError(f"playback order has {len(playback_order)} steps; valid bound is 1..127")
    for position, source_index in enumerate(playback_order):
        if not 0 <= source_index < len(all_frames):
            raise ValueError(
                f"order[{position}]={source_index} is outside valid source-frame bound "
                f"0..{len(all_frames) - 1} for {character_name}/{animation}"
            )
    if movement_steps is not None:
        if len(movement_steps) != len(playback_order):
            raise ValueError(
                f"movement has {len(movement_steps)} steps but order has "
                f"{len(playback_order)}"
            )
        if movement_steps[0] != 0:
            raise ValueError("movement step zero must be fixed")
        if sequence not in ("mid", "fast"):
            raise ValueError("idle and slow actions cannot define movement")
        if not any(movement_steps[1:]):
            raise ValueError("a moving action must contain at least one moving step")
    if return_step is not None:
        if movement_steps is None:
            raise ValueError("return step requires a movement table")
        if not 1 <= return_step < len(playback_order):
            raise ValueError(
                f"return step must be inside 1..{len(playback_order) - 1}"
            )
        if not any(movement_steps[1:return_step]):
            raise ValueError("action must move before its return step")
        if not any(movement_steps[return_step:]):
            raise ValueError("action must move at or after its return step")
    if x_offsets is not None:
        if len(x_offsets) != len(playback_order):
            raise ValueError("x offset table must match the playback order")
        if movement_steps is not None or return_step is not None:
            raise ValueError("x offsets cannot be mixed with computed movement")
    if y_offsets is not None:
        if len(y_offsets) != len(playback_order):
            raise ValueError("y offset table must match the playback order")
        if any(offset not in (0, -10) for offset in y_offsets):
            raise ValueError("y offsets must contain only grounded 0 or airborne -10")

    selected_source_indices = list(dict.fromkeys(playback_order))
    selected_frames = [all_frames[index] for index in selected_source_indices]
    source_left = min(int(frame["origin_x"]) for frame in selected_frames)
    source_top = min(int(frame["origin_y"]) for frame in selected_frames)
    source_right = max(
        int(frame["origin_x"]) + int(frame["width"]) for frame in selected_frames
    )
    source_bottom = max(
        int(frame["origin_y"]) + int(frame["height"]) for frame in selected_frames
    )
    source_bounds = (source_left, source_top, source_right, source_bottom)
    scale_num, scale_den = fighter.SEQUENCE_SCALES[sequence]
    source_height = source_bottom - source_top
    if sequence in ("mid", "fast") and source_height * scale_num > fighter.CANVAS_H * scale_den:
        divisor = math.gcd(fighter.CANVAS_H, source_height)
        scale_num = fighter.CANVAS_H // divisor
        scale_den = source_height // divisor
    scaled_width = math.ceil((source_right - source_left) * scale_num / scale_den)
    canvas_width = (
        max(fighter.CANVAS_W, scaled_width)
        if sequence in ("mid", "fast")
        else fighter.CANVAS_W
    )

    rendered_by_source: dict[int, list[list[int]]] = {}
    for source_index, frame in zip(selected_source_indices, selected_frames, strict=True):
        rendered_by_source[source_index] = fighter.render_frame(
            bitmaps / character_name / animation / frame["file"],
            frame,
            source_bounds,
            scale_num,
            scale_den,
            canvas_width,
            fighter.CANVAS_H,
        )

    origin_x = max(0, SCREEN_WIDTH - canvas_width)
    if sequence == "mid":
        target_x = max(0, origin_x - (SCREEN_WIDTH + 1) // 3)
    elif sequence == "fast":
        target_x = 0
    else:
        target_x = origin_x
    origin_y = SCREEN_HEIGHT - fighter.CANVAS_H if sequence in ("mid", "fast") else 0

    output_frames: list[bytes] = []
    for step_index, source_index in enumerate(playback_order):
        screen = [[0] * SCREEN_WIDTH for _ in range(SCREEN_HEIGHT)]
        image = rendered_by_source[source_index]
        x0 = (
            origin_x + x_offsets[step_index]
            if x_offsets is not None
            else frame_x(
                origin_x,
                target_x,
                len(playback_order),
                step_index,
                movement_steps,
                return_step,
            )
        )
        y0 = origin_y + (y_offsets[step_index] if y_offsets is not None else 0)
        for y, row in enumerate(image):
            target_y = y0 + y
            if not 0 <= target_y < SCREEN_HEIGHT:
                continue
            for x, pixel in enumerate(row):
                target_x_pixel = x0 + x
                if pixel and 0 <= target_x_pixel < SCREEN_WIDTH:
                    screen[target_y][target_x_pixel] = 1
        if show_hud:
            draw_hud(screen, left_battery, right_battery)
        output_frames.append(scale_pixels(screen, scale))

    if frame_durations_ms is not None:
        delays_ms = list(frame_durations_ms)
    elif sequence in ("mid", "fast"):
        delays_ms = [
            fighter.FIGHTER_ENDPOINT_HOLD_MS
            if index in (0, len(playback_order) - 1)
            else fighter.SEQUENCE_FRAME_MS[sequence]
            for index in range(len(playback_order))
        ]
    else:
        delays_ms = [fighter.SEQUENCE_FRAME_MS[sequence]] * len(playback_order)
    details = {
        "character": character_name,
        "sequence": sequence,
        "animation": animation,
        "source_frame_count": len(all_frames),
        "selected_frame_count": len(selected_source_indices),
        "playback_step_count": len(playback_order),
        "playback_order": playback_order,
        "movement": (
            ["move" if step else "fixed" for step in movement_steps]
            if movement_steps is not None
            else None
        ),
        "movement_step_count": (
            sum(movement_steps)
            if movement_steps is not None
            else sum(left != right for left, right in zip(x_offsets[:-1], x_offsets[1:], strict=True))
            if x_offsets is not None
            else len(playback_order) - 1
        ),
        "return_step": return_step,
        "x_offsets": x_offsets,
        "y_offsets": y_offsets,
        "durations_ms": frame_durations_ms,
        "timing": playback_entry.get("timing") if playback_entry is not None else None,
        "timing_report": (
            playback_entry.get("timing_report") if playback_entry is not None else None
        ),
        "duration_ms": sum(delays_ms),
        "canvas_width": canvas_width,
        "screen": [SCREEN_WIDTH * scale, SCREEN_HEIGHT * scale],
    }
    gif_delays: list[int] = []
    elapsed_ms = 0
    emitted_centiseconds = 0
    for delay in delays_ms:
        elapsed_ms += delay
        target_centiseconds = max(emitted_centiseconds + 1, (elapsed_ms + 5) // 10)
        gif_delays.append(target_centiseconds - emitted_centiseconds)
        emitted_centiseconds = target_centiseconds
    return output_frames, gif_delays, details


def main() -> None:
    module_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", default="Kyo")
    parser.add_argument(
        "--sequence", choices=tuple(fighter.SEQUENCE_FRAME_LIMIT), default="fast"
    )
    parser.add_argument("--animation")
    parser.add_argument("--order", type=parse_order)
    parser.add_argument("--movement", type=parse_movement)
    parser.add_argument("--return-step", type=int)
    parser.add_argument("--frame-limit", type=int)
    parser.add_argument(
        "--source-ticks-per-display-frame",
        type=int,
        default=fighter.DEFAULT_SOURCE_TICKS_PER_DISPLAY_FRAME,
        metavar="COUNT",
    )
    parser.add_argument(
        "--bitmaps", type=Path, default=module_root / "assets/character_bitmaps"
    )
    playback_group = parser.add_mutually_exclusive_group()
    playback_group.add_argument(
        "--playback-plan", type=Path, default=module_root / "data/fighter_playback.json"
    )
    playback_group.add_argument(
        "--no-playback-plan", dest="playback_plan", action="store_const", const=None
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--details-json", type=Path)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--loop-count", type=int, default=0)
    parser.add_argument("--left-battery", type=int, default=87)
    parser.add_argument("--right-battery", type=int, default=62)
    parser.add_argument("--no-hud", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.scale <= 8:
        parser.error("--scale must be in 1..8")
    if not 0 <= args.loop_count <= 65535:
        parser.error("--loop-count must be in 0..65535")
    if args.frame_limit is not None and not 1 <= args.frame_limit <= 127:
        parser.error("--frame-limit must be in 1..127")
    if not 1 <= args.source_ticks_per_display_frame <= 16:
        parser.error("--source-ticks-per-display-frame must be in 1..16")

    try:
        frames, delays_cs, details = render_action(
            args.bitmaps,
            args.playback_plan,
            args.character,
            args.sequence,
            args.animation,
            args.order,
            args.movement,
            args.return_step,
            args.frame_limit,
            args.scale,
            not args.no_hud and args.sequence in ("mid", "fast"),
            args.left_battery,
            args.right_battery,
            args.source_ticks_per_display_frame,
        )
        write_gif(
            args.output,
            frames,
            SCREEN_WIDTH * args.scale,
            SCREEN_HEIGHT * args.scale,
            delays_cs,
            args.loop_count,
        )
        if args.details_json is not None:
            args.details_json.parent.mkdir(parents=True, exist_ok=True)
            args.details_json.write_text(
                json.dumps(details, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(
        f"rendered {details['character']}/{details['sequence']} "
        f"({details['animation']}): {details['selected_frame_count']} selected frames -> "
        f"{details['playback_step_count']} steps/{details['duration_ms']}ms, "
        f"{details['movement_step_count']} moving, "
        f"{details['screen'][0]}x{details['screen'][1]} GIF at {args.output}"
    )


if __name__ == "__main__":
    main()
