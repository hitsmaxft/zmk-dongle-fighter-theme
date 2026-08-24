import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_fighter_gif.py"
sys.path.insert(0, str(ROOT / "scripts"))

from render_fighter_gif import frame_x


class FighterGifTest(unittest.TestCase):
    def test_fixed_steps_hold_and_moving_steps_reach_target(self):
        movement = [0] * 8 + [1] * 4
        positions = [frame_x(53, 0, 12, index, movement) for index in range(12)]
        self.assertEqual(positions[:8], [53] * 8)
        self.assertEqual(positions[8:], [40, 26, 13, 0])

    def test_return_step_reaches_target_then_origin(self):
        movement = [0, 1, 1, 0, 1, 1, 0]
        positions = [frame_x(78, 0, 7, index, movement, 4) for index in range(7)]
        self.assertEqual(positions, [78, 39, 0, 0, 39, 78, 78])

    def test_orochi_leona_gif_uses_game_loop_and_return(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "orochi-leona.gif"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--character",
                    "Orochi_Leona",
                    "--sequence",
                    "fast",
                    "--scale",
                    "1",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            data = output.read_bytes()

        self.assertEqual(data.count(b"\x21\xf9\x04"), 34)
        self.assertIn("34 steps/1842ms, 30 moving", result.stdout)

    def test_kyo_custom_sequence_gif_has_firmware_delays(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "kyo.gif"
            details = Path(directory) / "kyo.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--character",
                    "Kyo",
                    "--sequence",
                    "fast",
                    "--scale",
                    "1",
                    "--output",
                    str(output),
                    "--details-json",
                    str(details),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            data = output.read_bytes()
            report = json.loads(details.read_text(encoding="utf-8"))

        self.assertTrue(data.startswith(b"GIF89a"))
        self.assertTrue(data.endswith(b";"))
        controls = data.split(b"\x21\xf9\x04")[1:]
        self.assertEqual(len(controls), 36)
        delays = [int.from_bytes(control[1:3], "little") for control in controls]
        self.assertGreaterEqual(min(delays), 3)
        self.assertEqual(report["timing_report"]["total_ticks"], 59)
        self.assertEqual(report["timing_report"]["source_ticks_per_display_frame"], 2)
        self.assertEqual(report["timing_report"]["target_hz_millihertz"], 29864)
        self.assertEqual(report["timing_report"]["sampled_display_slots"], 47)
        self.assertEqual(report["timing_report"]["collapsed_hold_slots"], 11)
        self.assertEqual(report["timing_report"]["source_total_ms"], 988)
        self.assertEqual(report["timing_report"]["total_ms"], 1574)
        self.assertIn("4 moving", result.stdout)

    def test_terry_hidden_max_gif_uses_replacing_geyser_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "terry-hidden-max.gif"
            details = Path(directory) / "terry-hidden-max.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--character",
                    "Terry",
                    "--sequence",
                    "fast",
                    "--scale",
                    "1",
                    "--output",
                    str(output),
                    "--details-json",
                    str(details),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            data = output.read_bytes()
            report = json.loads(details.read_text(encoding="utf-8"))

        self.assertEqual(data.count(b"\x21\xf9\x04"), 105)
        self.assertIn("105 steps/5090ms, 102 moving", result.stdout)
        controls = data.split(b"\x21\xf9\x04")[1:]
        delays = [int.from_bytes(control[1:3], "little") for control in controls]
        self.assertTrue({3, 4}.issubset(delays))
        self.assertGreater(max(delays), 4)
        self.assertEqual(report["timing_report"]["startup_ticks"], 21)
        self.assertEqual(report["timing_report"]["body_ticks"], 117)
        self.assertEqual(report["timing_report"]["recovery_ticks"], 61)
        self.assertEqual(report["timing_report"]["source_ticks_per_display_frame"], 2)
        self.assertEqual(report["timing_report"]["sampled_display_slots"], 152)
        self.assertEqual(report["timing_report"]["collapsed_hold_slots"], 47)
        self.assertEqual(report["timing_report"]["source_total_ms"], 3332)
        self.assertEqual(report["timing_report"]["total_ms"], 5090)

    def test_composite_projectile_phase_offsets_render(self):
        for character in ("Athena", "Goenitz", "Mr_Karate"):
            with self.subTest(character=character), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / f"{character}.gif"
                subprocess.run(
                    [
                        sys.executable,
                        str(RENDERER),
                        "--character",
                        character,
                        "--sequence",
                        "fast",
                        "--scale",
                        "1",
                        "--output",
                        str(output),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertTrue(output.read_bytes().startswith(b"GIF89a"))

    def test_cli_order_overrides_the_project_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "short.gif"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--character",
                    "Kyo",
                    "--sequence",
                    "fast",
                    "--order",
                    "0,2,1,7",
                    "--scale",
                    "1",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            data = output.read_bytes()

        self.assertIn("4 selected frames -> 4 steps/1400ms, 3 moving", result.stdout)
        self.assertEqual(data.count(b"\x21\xf9\x04"), 4)


if __name__ == "__main__":
    unittest.main()
