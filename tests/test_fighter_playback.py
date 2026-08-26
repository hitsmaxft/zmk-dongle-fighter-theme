import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
sys.path.insert(0, str(SCRIPTS))

from generate_cornix_fighter_assets import (
    gb_logic_durations,
    load_playback_plan,
    sample_frame_indices,
)
from cache_cornix_fighter_provider import profile_arguments


BITMAPS = ASSETS / "character_bitmaps"
PLAYBACK_PLAN = DATA / "fighter_playback.json"
GENERATOR = SCRIPTS / "generate_cornix_fighter_assets.py"


def write_plan(
    path: Path,
    character: str,
    animation: str,
    order: list[int],
    movement: list[str] | None = None,
    return_step: int | None = None,
    x_offsets: list[int] | None = None,
    y_offsets: list[int] | None = None,
    durations_ms: list[int] | None = None,
    timing: dict[str, object] | None = None,
) -> None:
    entry = {"animation": animation, "order": order}
    if movement is not None:
        entry["movement"] = movement
    if return_step is not None:
        entry["return_step"] = return_step
    if x_offsets is not None:
        entry["x_offsets"] = x_offsets
    if y_offsets is not None:
        entry["y_offsets"] = y_offsets
    if durations_ms is not None:
        entry["durations_ms"] = durations_ms
    if timing is not None:
        entry["timing"] = timing
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "characters": {
                    character: {"fast": entry}
                },
            }
        ),
        encoding="utf-8",
    )


class FighterPlaybackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bitmap_manifest = json.loads(
            (BITMAPS / "manifest.json").read_text(encoding="utf-8")
        )

    def test_invalid_playback_order_reports_context(self):
        cases = [
            ([], r"order must contain 1..127"),
            ([8], r"order\[0\]=8.*bound 0..7"),
            (list(range(128)), r"expands to 128 steps.*1..127"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            for order, message in cases:
                with self.subTest(order=order):
                    write_plan(plan, "Kyo", "ura_orochi_nagi_d", order)
                    with self.assertRaisesRegex(ValueError, rf"Kyo/fast.*{message}"):
                        load_playback_plan(
                            plan, self.bitmap_manifest["characters"]
                        )

    def test_single_frame_sampling_keeps_the_first_source_frame(self):
        self.assertEqual(sample_frame_indices(8, 1), [0])

    def test_production_profile_excludes_requested_normal_fighters(self):
        arguments = profile_arguments("eighteen")
        enabled = {
            arguments[index + 1]
            for index, argument in enumerate(arguments)
            if argument == "--enabled-character"
        }
        self.assertTrue(
            {"Leona", "Iori", "Chizuru", "Boss_Kagura", "Mature"}.isdisjoint(enabled)
        )
        self.assertTrue({"Orochi_Leona", "Orochi_Iori"}.issubset(enabled))

    def test_iori_variants_bind_to_their_own_rom_pointer_tables(self):
        characters = self.bitmap_manifest["characters"]
        self.assertEqual(
            characters["Iori"]["animations"]["kin_ya_otome_d"]["pointer_table"],
            "OBJLstPtrTable_Iori_KinYaOtomeD",
        )
        self.assertEqual(
            characters["Orochi_Iori"]["animations"]["kin_ya_otome_s"]["pointer_table"],
            "OBJLstPtrTable_OIori_KinYaOtomeS",
        )
        self.assertEqual(
            len(characters["Iori"]["animations"]["kin_ya_otome_d"]["frames"]), 28
        )
        self.assertEqual(
            len(characters["Orochi_Iori"]["animations"]["kin_ya_otome_s"]["frames"]),
            16,
        )

        plan = json.loads(PLAYBACK_PLAN.read_text(encoding="utf-8"))[
            "characters"
        ]
        self.assertEqual(plan["Iori"]["fast"]["animation"], "fighter_fast_projectile")
        self.assertEqual(plan["Orochi_Iori"]["fast"]["animation"], "kin_ya_otome_s")

    def test_default_roster_has_rom_timing_and_int8_phase_offsets(self):
        plan = json.loads(PLAYBACK_PLAN.read_text(encoding="utf-8"))[
            "characters"
        ]
        roster = {
            "Kyo", "Daimon", "Terry", "Andy", "Ryo", "Robert", "Athena",
            "Mai", "Orochi_Leona", "Geese", "Krauser", "Goenitz",
            "Mr_Karate", "Orochi_Iori",
        }
        airborne = {"Andy", "Ryo", "Robert", "Athena", "Mai", "Orochi_Leona", "Mr_Karate"}
        for name in roster:
            with self.subTest(character=name):
                fast = plan[name]["fast"]
                timing = fast["timing"]
                self.assertEqual(timing["clock"], "gb-vblank")
                self.assertEqual(len(timing["step_ticks"]), len(fast["order"]))
                self.assertEqual(timing["total_ticks"], sum(timing["step_ticks"]))
                self.assertEqual(timing["disassembly_revision"], "47acd3002897ccd6b46df70809e8d6236ed3ebc3")
                offsets = fast.get("y_offsets", [])
                if name in airborne:
                    self.assertIn(-10, offsets)
                self.assertTrue(all(-127 <= value <= 127 for value in offsets))

    def test_default_mid_actions_have_reviewed_rom_timelines(self):
        plan = json.loads(PLAYBACK_PLAN.read_text(encoding="utf-8"))[
            "characters"
        ]
        roster = {
            "Kyo", "Daimon", "Terry", "Andy", "Ryo", "Robert", "Athena",
            "Mai", "Orochi_Leona", "Geese", "Krauser", "Goenitz", "Orochi_Iori",
        }
        for name in roster:
            with self.subTest(character=name):
                mid = plan[name]["mid"]
                timing = mid["timing"]
                self.assertEqual(timing["schema"], 2)
                self.assertEqual(timing["clock"], "gb-vblank")
                self.assertEqual(len(mid["order"]), len(timing["step_ticks"]))
                self.assertEqual(timing["total_ticks"], sum(timing["step_ticks"]))
                self.assertNotIn("super_sparkle", timing)

        self.assertEqual(plan["Mai"]["mid"]["timing"]["step_ticks"], [1, 1, 1, 1, 9])
        self.assertEqual(plan["Geese"]["mid"]["timing"]["step_ticks"], [2] * 7 + [31])
        self.assertEqual(
            plan["Orochi_Iori"]["mid"]["order"], [0, 1, 2, 3, 5, 6, 7]
        )

    def test_invalid_movement_reports_context(self):
        cases = [
            (["fixed"], r"movement must contain exactly 8 steps"),
            (["move"] + ["fixed"] * 7, r"movement\[0\] must be 'fixed'"),
            (["fixed"] * 8, r"must contain at least one moving step"),
            (["fixed"] * 7 + ["slide"], r"movement\[7\]='slide'"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            for movement, message in cases:
                with self.subTest(movement=movement):
                    write_plan(
                        plan,
                        "Kyo",
                        "ura_orochi_nagi_d",
                        list(range(8)),
                        movement,
                    )
                    with self.assertRaisesRegex(ValueError, rf"Kyo/fast.*{message}"):
                        load_playback_plan(plan, self.bitmap_manifest["characters"])

    def test_invalid_return_step_reports_context(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", list(range(8)), None, 4)
            with self.assertRaisesRegex(ValueError, r"return_step requires a movement table"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])

    def test_invalid_explicit_offsets_report_context(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", list(range(8)), x_offsets=[0])
            with self.assertRaisesRegex(ValueError, r"x_offsets must contain exactly 8 steps"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])
            write_plan(
                plan, "Kyo", "ura_orochi_nagi_d", list(range(8)),
                ["fixed"] + ["move"] * 7, None, [0] * 8,
            )
            with self.assertRaisesRegex(ValueError, r"cannot mix x_offsets with computed movement"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])

            movement = ["fixed"] + ["move"] * 7
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", list(range(8)), movement, 8)
            with self.assertRaisesRegex(ValueError, r"return_step must be inside 1..7"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])

    def test_invalid_explicit_durations_report_context(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            order = list(range(8))
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", order,
                       x_offsets=[0] * 8, durations_ms=[17])
            with self.assertRaisesRegex(ValueError, r"durations_ms must contain exactly 8 steps"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])
            for bad in (0, 65536, True):
                with self.subTest(duration=bad):
                    durations = [17] * 8
                    durations[3] = bad
                    write_plan(plan, "Kyo", "ura_orochi_nagi_d", order,
                               x_offsets=[0] * 8, durations_ms=durations)
                    with self.assertRaisesRegex(ValueError, r"durations_ms\[3\].*outside 1..65535"):
                        load_playback_plan(plan, self.bitmap_manifest["characters"])
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", order,
                       durations_ms=[17] * 8)
            loaded = load_playback_plan(plan, self.bitmap_manifest["characters"])
            self.assertEqual(loaded[("Kyo", "fast")]["durations_ms"], [17] * 8)

    def test_source_tick_conversion_preserves_cumulative_duration(self):
        self.assertEqual(
            gb_logic_durations([1] * 12),
            [17, 16, 17, 17, 17, 16, 17, 17, 17, 16, 17, 17],
        )
        durations = gb_logic_durations([21, 3, 9, 9, 6])
        self.assertEqual(durations, [352, 50, 151, 150, 101])
        self.assertEqual(sum(durations), gb_logic_durations([48])[0])

    def test_y_offsets_accept_airborne_and_projectile_phase_values(self):
        order = list(range(8))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "airborne.json"
            y_offsets = [0, 0, -10, -10, -10, 0, 0, 0]
            write_plan(
                plan,
                "Kyo",
                "ura_orochi_nagi_d",
                order,
                y_offsets=y_offsets,
                durations_ms=[17] * len(order),
            )
            loaded = load_playback_plan(plan, self.bitmap_manifest["characters"])
            self.assertEqual(loaded[("Kyo", "fast")]["y_offsets"], y_offsets)
            self.generate_character(directory, "Kyo", "--playback-plan", str(plan))
            header = (root / "generated" / "kof96_provider.h").read_text(encoding="utf-8")
            self.assertIn("fighter_kyo_fast_images_y_offsets[] = {0, 0, -10", header)
            self.assertIn("ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_Y_OFFSETS_DEFINE(", header)

            phase_offsets = [0, 0, -9, -10, -10, 0, 0, 0]
            write_plan(
                plan,
                "Kyo",
                "ura_orochi_nagi_d",
                order,
                y_offsets=phase_offsets,
            )
            loaded = load_playback_plan(plan, self.bitmap_manifest["characters"])
            self.assertEqual(loaded[("Kyo", "fast")]["y_offsets"], phase_offsets)

            phase_offsets[2] = -128
            write_plan(
                plan, "Kyo", "ura_orochi_nagi_d", order, y_offsets=phase_offsets
            )
            with self.assertRaisesRegex(ValueError, r"y_offsets\[2\].*outside -127..127"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])

    def test_rom_timing_schema_rejects_inconsistent_boundaries(self):
        order = list(range(8))
        timing = {
            "schema": 2,
            "rom_move": "MOVE_KYO_TEST",
            "clock": "gb-vblank",
            "branch": "test",
            "disassembly_revision": "a" * 40,
            "evidence": {"animation_table": "table", "move_code": "code"},
            "hitstop": {"ticks": 0, "scope": "none", "source": "test"},
            "startup": {"step": 0, "frame": 0, "ticks": 1, "source": "table"},
            "step_ticks": [1] * 8,
            "recovery": {
                "start_step": 7,
                "frame": 7,
                "ticks": 1,
                "exclusive_tail_ticks": 1,
                "source": "end",
            },
            "total_ticks": 8,
        }
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", order, timing=timing)
            loaded = load_playback_plan(plan, self.bitmap_manifest["characters"])
            self.assertEqual(
                loaded[("Kyo", "fast")]["durations_ms"],
                [33, 34, 33, 34, 33, 34, 33, 34],
            )

            timing["total_ticks"] = 7
            write_plan(plan, "Kyo", "ura_orochi_nagi_d", order, timing=timing)
            with self.assertRaisesRegex(ValueError, r"total_ticks must equal"):
                load_playback_plan(plan, self.bitmap_manifest["characters"])

    def test_display_divisor_preserves_states_unless_frame_drop_is_explicit(self):
        with tempfile.TemporaryDirectory() as default_directory:
            default = self.generate_character(default_directory, "Kyo")
        with tempfile.TemporaryDirectory() as reduced_directory:
            reduced = self.generate_character(
                reduced_directory,
                "Kyo",
                "--source-ticks-per-display-frame",
                "4",
            )
        with tempfile.TemporaryDirectory() as sampled_directory:
            sampled = self.generate_character(
                sampled_directory,
                "Kyo",
                "--source-ticks-per-display-frame",
                "4",
                "--allow-source-frame-drop",
            )
        default_fast = default["characters"]["Kyo"]["sequences"]["fast"]
        reduced_fast = reduced["characters"]["Kyo"]["sequences"]["fast"]
        sampled_fast = sampled["characters"]["Kyo"]["sequences"]["fast"]
        self.assertEqual(default_fast["playback_order"], reduced_fast["playback_order"])
        self.assertEqual(default_fast["playback_step_count"], 36)
        self.assertEqual(reduced_fast["playback_step_count"], 36)
        self.assertGreater(reduced_fast["duration_ms"], default_fast["duration_ms"])
        self.assertLess(sampled_fast["playback_step_count"], reduced_fast["playback_step_count"])
        self.assertEqual(sampled_fast["duration_ms"], 988)
        self.assertEqual(sampled_fast["timing_report"]["source_frame_drop_enabled"], 1)
        self.assertEqual(reduced_fast["timing_report"]["target_hz_millihertz"], 14932)

    def test_sampling_preserves_named_projectiles_or_fails_explicitly(self):
        reduced = load_playback_plan(PLAYBACK_PLAN, self.bitmap_manifest["characters"], 8)
        for character in ("Athena", "Geese", "Mr_Karate"):
            with self.subTest(character=character):
                action = reduced[(character, "fast")]
                self.assertTrue(
                    set(action["sampling_required_frames"]).issubset(action["order"])
                )

        with self.assertRaisesRegex(
            ValueError,
            r"Mr_Karate/fast cannot preserve required source frames \[39\].*8 source ticks/frame",
        ):
            load_playback_plan(
                PLAYBACK_PLAN, self.bitmap_manifest["characters"], 8, True
            )

    def test_default_30hz_quantization_keeps_every_planned_bitmap(self):
        source = json.loads(PLAYBACK_PLAN.read_text(encoding="utf-8"))["characters"]
        loaded = load_playback_plan(PLAYBACK_PLAN, self.bitmap_manifest["characters"])
        for character, sequences in source.items():
            for sequence, entry in sequences.items():
                if "timing" not in entry:
                    continue
                with self.subTest(character=character, sequence=sequence):
                    adapted = loaded[(character, sequence)]
                    self.assertEqual(set(adapted["order"]), set(entry["order"]))
                    self.assertEqual(
                        adapted["timing_report"]["source_frame_drop_enabled"], 0
                    )
                    source_states = []
                    expected_states = []
                    movement = [
                        int(value == "move") for value in entry.get("movement", [])
                    ]
                    recovery_step = entry["timing"]["recovery"]["start_step"]
                    return_step = entry.get("return_step")
                    for index, frame in enumerate(entry["order"]):
                        state = (
                            frame,
                            entry.get("x_offsets", [None] * len(entry["order"]))[index],
                            entry.get("y_offsets", [None] * len(entry["order"]))[index],
                            movement[index] if movement else None,
                        )
                        source_states.append(state)
                        may_merge = (
                            expected_states
                            and expected_states[-1] == state
                            and (not movement or not movement[index])
                            and index not in (recovery_step, return_step)
                        )
                        if not may_merge:
                            expected_states.append(state)
                    adapted_states = [
                        (
                            frame,
                            adapted.get("x_offsets", [None] * len(adapted["order"]))[index],
                            adapted.get("y_offsets", [None] * len(adapted["order"]))[index],
                            adapted.get("movement_steps", [None] * len(adapted["order"]))[index],
                        )
                        for index, frame in enumerate(adapted["order"])
                    ]
                    self.assertEqual(adapted_states, expected_states)
        for character in ("Ryo", "Robert", "Mr_Karate"):
            self.assertEqual(
                loaded[(character, "fast")]["order"],
                source[character]["fast"]["order"],
            )

    def test_generator_emits_timed_plain_and_return_macros(self):
        order = list(range(8))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain_plan = root / "plain.json"
            write_plan(
                plain_plan,
                "Kyo",
                "ura_orochi_nagi_d",
                order,
                durations_ms=[17] * len(order),
            )
            self.generate_character(directory, "Kyo", "--playback-plan", str(plain_plan))
            header = (root / "generated" / "kof96_provider.h").read_text(encoding="utf-8")
            self.assertIn("ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_TIMED_DEFINE(", header)

        timing = {
            "schema": 2,
            "rom_move": "MOVE_KYO_TEST",
            "clock": "gb-vblank",
            "branch": "test",
            "disassembly_revision": "b" * 40,
            "evidence": {"animation_table": "table", "move_code": "code"},
            "hitstop": {"ticks": 0, "scope": "none", "source": "test"},
            "startup": {"step": 0, "frame": 0, "ticks": 1, "source": "table"},
            "step_ticks": [1] * len(order),
            "recovery": {
                "start_step": 7,
                "frame": 7,
                "ticks": 1,
                "exclusive_tail_ticks": 1,
                "source": "end",
            },
            "total_ticks": len(order),
        }
        movement = ["fixed", "move", "move", "fixed", "move", "move", "fixed", "fixed"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            return_plan = root / "return.json"
            write_plan(
                return_plan,
                "Kyo",
                "ura_orochi_nagi_d",
                order,
                movement=movement,
                return_step=4,
                timing=timing,
            )
            self.generate_character(directory, "Kyo", "--playback-plan", str(return_plan))
            header = (root / "generated" / "kof96_provider.h").read_text(encoding="utf-8")
            self.assertIn(
                "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_TIMED_MOVEMENT_RETURN_DEFINE(",
                header,
            )

    def generate_character(
        self, directory: str, character: str, *playback_args: str
    ) -> dict[str, object]:
        output = Path(directory) / "generated"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--bitmaps",
                str(BITMAPS),
                "--character",
                character,
                "--enabled-character",
                character,
                *playback_args,
                "--output-dir",
                str(output),
                "--no-previews",
            ],
            check=True,
        )
        return json.loads((output / "manifest.json").read_text(encoding="utf-8"))

    def test_default_plan_expands_references_without_duplicate_images(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Kyo")
        fast = result["characters"]["Kyo"]["sequences"]["fast"]

        self.assertEqual(fast["animation"], "ura_orochi_nagi_d")
        self.assertEqual(fast["selected_frame_count"], 8)
        self.assertEqual(fast["playback_step_count"], 36)
        self.assertEqual(fast["timing_report"]["sampled_display_slots"], 47)
        self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], 11)
        self.assertEqual(fast["duration_ms"], 1574)
        self.assertEqual(fast["timing_report"]["total_ticks"], 59)
        self.assertEqual(fast["timing_report"]["target_hz_millihertz"], 29864)
        self.assertEqual(fast["movement_step_count"], 4)
        self.assertEqual(len(fast["generated_symbols"]), 8)

    def test_mai_plan_expands_landing_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Mai")
        fast = result["characters"]["Mai"]["sequences"]["fast"]

        self.assertEqual(fast["animation"], "cho_hissatsu_shinobibachi_d")
        source = json.loads(PLAYBACK_PLAN.read_text())["characters"]["Mai"]["fast"]
        self.assertEqual(source["order"], [0, 1, 2, 3, 4, 5, 6, 7] + [8, 9] * 12 + [10])
        self.assertEqual(fast["playback_step_count"], 33)
        self.assertEqual(fast["timing_report"]["sampled_display_slots"], 42)
        self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], 9)
        self.assertEqual(fast["duration_ms"], 1406)
        self.assertEqual(fast["timing_report"]["total_ticks"], 51)
        self.assertIn(-10, fast["y_offsets"])

    def test_orochi_leona_loops_then_returns(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Orochi_Leona")
        fast = result["characters"]["Orochi_Leona"]["sequences"]["fast"]

        self.assertEqual(fast["animation"], "super_moon_slasher_s")
        source = json.loads(PLAYBACK_PLAN.read_text())["characters"]["Orochi_Leona"]["fast"]
        self.assertEqual(source["order"][4:28], [4, 5, 6] * 8)
        self.assertEqual(source["return_step"], 28)
        self.assertEqual(fast["playback_step_count"], 34)
        self.assertEqual(fast["timing_report"]["sampled_display_slots"], 55)
        self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], 21)
        self.assertEqual(fast["duration_ms"], 1842)
        self.assertEqual(fast["timing_report"]["total_ticks"], 82)
        self.assertIn(-10, fast["y_offsets"])

    def test_second_batch_fast_plans_preserve_loops_and_approaches(self):
        expectations = {
            "Daimon": ("heaven_hell_drop_s", 27, 116, 89, 217, 3884),
            "Andy": ("cho_reppa_dan_s", 6, 31, 25, 58, 1038),
            "Athena": ("fighter_fast_projectile", 126, 131, 5, 137, 4387),
            "Orochi_Iori": ("kin_ya_otome_s", 37, 51, 14, 66, 1708),
        }
        for character, (
            animation, steps, slots, collapsed, total_ticks, duration_ms
        ) in expectations.items():
            with self.subTest(character=character):
                with tempfile.TemporaryDirectory() as directory:
                    result = self.generate_character(directory, character)
                fast = result["characters"][character]["sequences"]["fast"]
                self.assertEqual(fast["animation"], animation)
                self.assertEqual(fast["playback_step_count"], steps)
                self.assertEqual(fast["timing_report"]["sampled_display_slots"], slots)
                self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], collapsed)
                self.assertEqual(fast["duration_ms"], duration_ms)
                self.assertEqual(fast["timing"]["total_ticks"], sum(fast["timing"]["step_ticks"]))
                self.assertEqual(fast["timing_report"]["total_ticks"], total_ticks)
                self.assertEqual(len(fast["generated_symbols"]), fast["selected_frame_count"])
                if character == "Athena":
                    self.assertGreater(max(fast["playback_order"]), 8)

    def test_athena_crystal_and_geese_pillar_use_rom_projectile_mappings(self):
        projectile_manifest = json.loads(
            (ASSETS / "projectile_bitmaps" / "manifest.json").read_text(encoding="utf-8")
        )["frames"]
        self.assertTrue(
            {
                "athena_shcryst_swirl",
                "athena_shcryst_thrown_0",
                "athena_shcryst_thrown_1",
                "athena_shcryst_thrown_2",
                "geese_raging_storm_s0",
                "geese_raging_storm_s1",
                "geese_raging_storm_s2",
                "geese_raging_storm_s3",
            }.issubset(projectile_manifest)
        )
        for character, total_ticks, body_last in (("Athena", 137, 8), ("Geese", 83, 2)):
            with self.subTest(character=character):
                with tempfile.TemporaryDirectory() as directory:
                    result = self.generate_character(directory, character)
                fast = result["characters"][character]["sequences"]["fast"]
                self.assertEqual(fast["animation"], "fighter_fast_projectile")
                self.assertEqual(fast["timing_report"]["total_ticks"], total_ticks)
                self.assertGreater(max(fast["selected_source_indices"]), body_last)
                self.assertIn("object_table", fast["timing"]["evidence"])
                source_frames = self.bitmap_manifest["characters"][character]["animations"][
                    "fighter_fast_projectile"
                ]["frames"]
                selected_projectiles = {
                    source_frames[index]["sources"][0][1]
                    for index in fast["selected_source_indices"]
                    if source_frames[index]["sources"][0][0] == "projectile"
                }
                expected = (
                    {
                        "athena_shcryst_swirl",
                        "athena_shcryst_thrown_0",
                        "athena_shcryst_thrown_1",
                        "athena_shcryst_thrown_2",
                    }
                    if character == "Athena"
                    else {f"geese_raging_storm_s{index}" for index in range(4)}
                )
                self.assertEqual(selected_projectiles, expected)

        plan = json.loads(PLAYBACK_PLAN.read_text(encoding="utf-8"))["characters"]
        geese = plan["Geese"]["fast"]
        geese_positions = {
            frame: {
                x
                for selected, x in zip(
                    geese["order"], geese["x_offsets"], strict=True
                )
                if selected == frame
            }
            for frame in range(3, 7)
        }
        self.assertEqual(
            [next(iter(geese_positions[frame])) for frame in range(3, 7)],
            [-36, 0, -24, -13],
        )
        geese_frames = self.bitmap_manifest["characters"]["Geese"]["animations"][
            "fighter_fast_projectile"
        ]["frames"]
        geese_root = BITMAPS / "Geese" / "fighter_fast_projectile"
        self.assertEqual(
            (geese_root / geese_frames[3]["file"]).read_bytes(),
            (geese_root / geese_frames[5]["file"]).read_bytes(),
        )
        self.assertEqual(
            (geese_root / geese_frames[4]["file"]).read_bytes(),
            (geese_root / geese_frames[6]["file"]).read_bytes(),
        )

        athena = plan["Athena"]["fast"]
        athena_positions = {
            frame: [
                x
                for selected, x in zip(
                    athena["order"], athena["x_offsets"], strict=True
                )
                if selected == frame
            ]
            for frame in range(9, 13)
        }
        self.assertEqual(len(set(athena_positions[9])), 1)
        athena_y = {
            y
            for frame, y in zip(
                athena["order"], athena["y_offsets"], strict=True
            )
            if frame == 9
        }
        self.assertEqual(athena_y, {-18})
        thrown_positions = [
            x
            for frame, x in zip(
                athena["order"], athena["x_offsets"], strict=True
            )
            if frame in range(10, 13)
        ]
        self.assertLess(min(thrown_positions), max(thrown_positions))
        self.assertLess(min(thrown_positions[-4:]), thrown_positions[0])

    def test_ryo_and_robert_finish_with_reused_airborne_uppercuts(self):
        expectations = {
            "Ryo": (35, 53, 18, 102, 1775),
            "Robert": (30, 48, 18, 92, 1607),
        }
        for character, (steps, slots, collapsed, ticks, duration_ms) in expectations.items():
            with self.subTest(character=character):
                with tempfile.TemporaryDirectory() as directory:
                    result = self.generate_character(directory, character)
                fast = result["characters"][character]["sequences"]["fast"]
                self.assertEqual(fast["animation"], "fighter_fast_projectile")
                self.assertEqual(fast["playback_step_count"], steps)
                self.assertEqual(fast["timing_report"]["sampled_display_slots"], slots)
                self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], collapsed)
                self.assertEqual(fast["timing_report"]["total_ticks"], ticks)
                self.assertEqual(fast["duration_ms"], duration_ms)
                self.assertEqual(fast["movement_step_count"], 4)
                self.assertIn(-10, fast["y_offsets"])

    def test_goenitz_dashes_to_center_then_flashes_tornado_during_throw(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Goenitz")
        fast = result["characters"]["Goenitz"]["sequences"]["fast"]

        self.assertEqual(fast["animation"], "fighter_fast_projectile")
        self.assertEqual(fast["playback_step_count"], 23)
        self.assertEqual(fast["timing_report"]["sampled_display_slots"], 42)
        self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], 19)
        self.assertEqual(fast["timing_report"]["total_ticks"], 69)
        self.assertEqual(fast["duration_ms"], 1406)
        self.assertTrue({11, 12, 13}.issubset(fast["selected_source_indices"]))
        tornado_positions = {
            frame: set()
            for frame in (11, 12, 13)
        }
        for frame, x_offset in zip(
            fast["playback_order"], fast["x_offsets"], strict=True
        ):
            if frame in tornado_positions:
                tornado_positions[frame].add(x_offset)
        self.assertEqual(len({next(iter(values)) for values in tornado_positions.values()}), 3)
        self.assertIn(-32, fast["x_offsets"])
        self.assertEqual(len(fast["generated_symbols"]), 14)

    def test_mid_and_fast_reused_body_frames_share_generated_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Goenitz")
        sequences = result["characters"]["Goenitz"]["sequences"]
        shared = set(sequences["mid"]["symbols"]) & set(sequences["fast"]["symbols"])
        self.assertGreaterEqual(len(shared), 6)
        self.assertGreater(result["deduplicated_frame_count"], 0)

    def test_iori_max_runs_then_flashes_at_the_finisher(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Iori")
        fast = result["characters"]["Iori"]["sequences"]["fast"]

        self.assertEqual(fast["animation"], "fighter_fast_projectile")
        self.assertEqual(fast["playback_step_count"], 43)
        self.assertEqual(fast["playback_order"][:5], [0, 1, 1, 1, 1])
        self.assertEqual(fast["playback_order"][5:29], list(range(2, 26)))
        self.assertEqual(fast["playback_order"][29:41], [28, 25, 29, 25] * 3)
        self.assertEqual(fast["playback_order"][41:], [26, 27])
        self.assertIsNone(fast["movement"])
        self.assertEqual(fast["x_offsets"][:5], [0, -16, -32, -48, -64])
        self.assertTrue(all(-64 <= value <= 0 for value in fast["x_offsets"]))
        self.assertEqual(fast["x_offsets"][5:29], [-64] * 24)
        self.assertEqual(fast["movement_step_count"], 4)
        self.assertEqual(fast["duration_ms"], 7620)
        self.assertEqual(fast["durations_ms"][28:41], [60] + [80] * 12)
        self.assertEqual(len(fast["generated_symbols"]), 30)

    def test_terry_hidden_max_preserves_geyser_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Terry")
        fast = result["characters"]["Terry"]["sequences"]["fast"]

        self.assertEqual(fast["animation"], "fighter_fast_projectile")
        self.assertEqual(fast["playback_step_count"], 105)
        self.assertEqual(fast["duration_ms"], 5090)
        self.assertEqual(fast["timing"]["total_ticks"], 199)
        self.assertEqual(fast["timing"]["startup"]["ticks"], 21)
        self.assertEqual(fast["timing"]["recovery"]["ticks"], 61)
        self.assertEqual(fast["timing"]["recovery"]["start_step"], 95)
        self.assertEqual(
            fast["timing_report"],
            {
                "clock": "gb-vblank",
                "source_hz_millihertz": 59728,
                "source_ticks_per_display_frame": 2,
                "target_hz_millihertz": 29864,
                "sampled_display_slots": 152,
                "playback_steps": 105,
                "collapsed_hold_slots": 47,
                "source_frame_drop_enabled": 0,
                "startup_ticks": 21,
                "body_ticks": 117,
                "recovery_ticks": 61,
                "hitstop_ticks": 0,
                "total_ticks": 199,
                "startup_ms": 352,
                "body_ms": 1958,
                "recovery_ms": 1022,
                "source_total_ms": 3332,
                "total_ms": 5090,
            },
        )
        self.assertEqual(len(fast["generated_symbols"]), 5)

    def test_projectile_actions_emit_dual_object_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.generate_character(directory, "Terry")
            header = (root / "generated" / "kof96_provider.h").read_text(
                encoding="utf-8"
            )

        fast = result["characters"]["Terry"]["sequences"]["fast"]
        roles = fast["frame_roles"]
        source_frames = self.bitmap_manifest["characters"]["Terry"]["animations"][
            "fighter_fast_projectile"
        ]["frames"]
        expected = [
            int(source_frames[index]["sources"][0][0] == "projectile")
            for index in fast["playback_order"]
        ]
        self.assertEqual(roles, expected)
        self.assertEqual(roles[0], 0)
        self.assertIn(1, roles)
        self.assertIn("fighter_terry_fast_images_roles[]", header)
        self.assertIn("ZMK_DONGLE_ANIMATION_ACTION_TRACKS_DEFINE(", header)

    def test_mr_karate_finishes_with_alternating_projectile(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Mr_Karate")
        fast = result["characters"]["Mr_Karate"]["sequences"]["fast"]
        self.assertEqual(fast["animation"], "fighter_fast_projectile")
        self.assertEqual(fast["playback_step_count"], 64)
        self.assertEqual(fast["timing_report"]["sampled_display_slots"], 85)
        self.assertEqual(fast["timing_report"]["collapsed_hold_slots"], 21)
        self.assertEqual(fast["timing_report"]["total_ticks"], 132)
        self.assertEqual(fast["duration_ms"], 2846)
        self.assertTrue({38, 39}.issubset(fast["selected_source_indices"]))
        airborne = [
            (x, y)
            for frame, x, y in zip(
                fast["playback_order"],
                fast["x_offsets"],
                fast["y_offsets"],
                strict=True,
            )
            if frame in (30, 31)
        ]
        self.assertGreaterEqual(len(airborne), 8)
        self.assertEqual(airborne, sorted(airborne))
        self.assertLess(airborne[0][0], airborne[-1][0])

    def test_no_plan_preserves_sampled_ascending_order(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.generate_character(directory, "Kyo", "--no-playback-plan")
        fast = result["characters"]["Kyo"]["sequences"]["fast"]

        self.assertFalse(fast["custom_playback"])
        self.assertEqual(fast["playback_order"], list(range(8)))
        self.assertEqual(fast["selected_frame_count"], 8)
        self.assertEqual(fast["playback_step_count"], 8)

    def test_repeated_steps_do_not_duplicate_bitmap_payload(self):
        with tempfile.TemporaryDirectory() as custom_directory:
            result = self.generate_character(custom_directory, "Kyo")
        fast = result["characters"]["Kyo"]["sequences"]["fast"]
        self.assertGreater(fast["playback_step_count"], fast["selected_frame_count"])
        self.assertEqual(len(fast["generated_symbols"]), fast["selected_frame_count"])
        self.assertLessEqual(len(set(fast["symbols"])), fast["selected_frame_count"])


if __name__ == "__main__":
    unittest.main()
