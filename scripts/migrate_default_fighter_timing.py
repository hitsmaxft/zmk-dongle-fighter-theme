#!/usr/bin/env python3
"""Apply the reviewed KOF96 half-speed timelines to the production roster.

The firmware deliberately consumes finite display timelines rather than running
the original input, collision, and gravity state machines.  This script keeps
those branch choices and their disassembly evidence beside the generated plan.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REVISION = "47acd3002897ccd6b46df70809e8d6236ed3ebc3"
SPARKLE = {
    "ticks": 20,
    "parallel": True,
    "source": "src/bank02.asm:ExOBJ_SuperSparkle",
}
MID_MOVES = {
    "Andy": "MOVE_ANDY_SHO_RYU_DAN_L",
    "Athena": "MOVE_ATHENA_PSYCHO_SWORD_L",
    "Daimon": "MOVE_DAIMON_HEAVEN_DROP_L",
    "Geese": "MOVE_GEESE_REPPUKEN_H",
    "Goenitz": "MOVE_GOENITZ_SHINYAOTOME_THROW_H",
    "Krauser": "MOVE_KRAUSER_LEG_TOMAHAWK_L",
    "Kyo": "MOVE_KYO_ONI_YAKI_L",
    "Mai": "MOVE_MAI_RYU_EN_BU_H",
    "Orochi_Iori": "MOVE_IORI_KOTO_TSUKI_IN_L",
    "Orochi_Leona": "MOVE_LEONA_X_CALIBUR_L",
    "Robert": "MOVE_ROBERT_RYUU_GEKI_KEN_L",
    "Ryo": "MOVE_RYO_KYOKUKEN_RYU_RENBU_KEN_L",
    "Terry": "MOVE_TERRY_RISING_TACKLE_L",
}


def timing(
    move: str,
    table: str,
    code: str,
    branch: str,
    order: list[int],
    ticks: list[int],
    recovery_start: int,
    *,
    projectile: str | None = None,
    startup_source: str | None = None,
    recovery_source: str | None = None,
    include_super_sparkle: bool = True,
) -> dict[str, object]:
    if len(order) != len(ticks):
        raise ValueError(f"{move}: {len(order)} frames != {len(ticks)} tick entries")
    evidence = {"animation_table": table, "move_code": code}
    if projectile:
        evidence["projectile_code"] = projectile
    result = {
        "schema": 2,
        "rom_move": move,
        "clock": "gb-vblank",
        "branch": branch,
        "disassembly_revision": REVISION,
        "evidence": evidence,
        "hitstop": {
            "ticks": 0,
            "scope": "opponent-hit-reaction-only; excluded from player timeline",
            "source": "selected successful-hit display branch",
        },
        "startup": {
            "step": 0,
            "frame": order[0],
            "ticks": ticks[0],
            "source": startup_source or f"{table}; initial FrameTotal+1",
        },
        "step_ticks": ticks,
        "recovery": {
            "start_step": recovery_start,
            "frame": order[recovery_start],
            "ticks": sum(ticks[recovery_start:]),
            "exclusive_tail_ticks": ticks[-1],
            "source": recovery_source or f"{code}; final visible path to Play_Pl_EndMove",
        },
        "total_ticks": sum(ticks),
    }
    if include_super_sparkle:
        result["super_sparkle"] = dict(SPARKLE)
    return result


def set_timing(
    characters: dict[str, object],
    name: str,
    ticks: list[int],
    recovery_start: int,
    **metadata: object,
) -> None:
    entry = characters[name]["fast"]
    entry.pop("durations_ms", None)
    entry["timing"] = timing(
        order=entry["order"], ticks=ticks, recovery_start=recovery_start, **metadata
    )


def set_mid_timing(
    characters: dict[str, object],
    name: str,
    animation: str,
    order: list[int],
    ticks: list[int],
    recovery_start: int,
    *,
    table: str,
    code: str,
    branch: str,
    x_offsets: list[int] | None = None,
    y_offsets: list[int] | None = None,
) -> None:
    entry: dict[str, object] = {"animation": animation, "order": order}
    if x_offsets is not None:
        entry["x_offsets"] = x_offsets
    if y_offsets is not None:
        entry["y_offsets"] = y_offsets
    entry["timing"] = timing(
        move=MID_MOVES[name],
        table=table,
        code=code,
        branch=branch,
        order=order,
        ticks=ticks,
        recovery_start=recovery_start,
        include_super_sparkle=False,
    )
    characters.setdefault(name, {})["mid"] = entry


def apply_mid_migration(characters: dict[str, object]) -> None:
    # Static FrameTotal paths.  Each tick list includes the visible recovery
    # mapping through the source move's Play_Pl_EndMove branch.
    set_mid_timing(
        characters, "Daimon", "heaven_drop_l", list(range(10)),
        [11] * 7 + [31, 6, 6], 9,
        table="src/bank03.asm:MoveAnimTbl_Daimon",
        code="src/bank05.asm:MoveC_Daimon_HeavenDrop",
        branch="successful light command throw",
        x_offsets=[0] * 10,
    )
    set_mid_timing(
        characters, "Geese", "reppuken_h", list(range(8)),
        [2] * 7 + [31], 7,
        table="src/bank03.asm:MoveAnimTbl_Geese",
        code="src/bank06.asm:MoveC_Geese_ReppukenH",
        branch="heavy Reppuken through frame #6 dynamic recovery speed",
        x_offsets=[0, 0, 0, -7, -7, -7, -7, -7],
    )
    set_mid_timing(
        characters, "Robert", "ryuu_geki_ken_l", list(range(10)),
        [2] * 10, 9,
        table="src/bank03.asm:MoveAnimTbl_Robert",
        code="src/bank02.asm:MoveC_Robert_RyuuGekiKen",
        branch="light version with two seven-pixel frame-start advances",
        x_offsets=[0, -7, -14, -14, -14, -14, -14, -14, -14, -14],
    )
    set_mid_timing(
        characters, "Ryo", "kyokuken_ryu_renbu_ken_l", list(range(8)),
        [2] * 8, 7,
        table="src/bank03.asm:MoveAnimTbl_Ryo",
        code="src/bank02.asm:MoveC_Robert_KyokugenRyuRanbuKyaku",
        branch="light Ryo branch with frame-start 4/2/6-pixel advances",
        x_offsets=[0, -4, -4, -6, -6, -12, -12, -12],
    )
    set_mid_timing(
        characters, "Mai", "ryu_en_bu_h", list(range(5)),
        [1, 1, 1, 1, 9], 4,
        table="src/bank03.asm:MoveAnimTbl_Mai",
        code="src/bank06.asm:MoveC_Mai_RyuEnBu",
        branch="heavy Ryu En Bu with frame #3 setting recovery speed $08",
        x_offsets=[0, -4, -11, -11, -11],
    )
    set_mid_timing(
        characters, "Orochi_Iori", "iori_koto_tsuki_in_l",
        [0, 1, 2, 3, 5, 6, 7], [2, 2, 2, 2, 1, 3, 11], 6,
        table="src/bank03.asm:MoveAnimTbl_OIori",
        code="src/bank05.asm:MoveC_Iori_KotoTsukiIn",
        branch="deterministic near/collision success; whiff friction frame #4 omitted",
        x_offsets=[0, -12, -24, -32, -32, -32, -32],
    )

    # Gravity paths use the source 8.8 speeds and +$0060 gravity.  Repeated
    # mappings below are the finite results of threshold loops, not GIF padding.
    kyo_order = [0, 1, 2, 3, 4, 5, 6]
    set_mid_timing(
        characters, "Kyo", "oni_yaki_l", kyo_order,
        [2, 2, 1, 1, 18, 11, 11], 6,
        table="src/bank03.asm:MoveAnimTbl_Kyo",
        code="src/bank06.asm:MoveC_Kyo_OniYaki",
        branch="light jump speed -$0600, gravity +$0060, landing frame #6",
        y_offsets=[0, 0, -10, -10, -10, -10, 0],
    )

    rising_body = [1, 2, 3, 4, 2, 3, 4, 2, 3, 4, 5, 6]
    set_mid_timing(
        characters, "Terry", "rising_tackle_l", [0] + rising_body + [7],
        [2] + [1] * 10 + [8, 13, 9], 13,
        table="src/bank03.asm:MoveAnimTbl_Terry",
        code="src/bank02.asm:MoveC_Terry_RisingTackle",
        branch="light -$0600 arc; #2-#4 loops until Y speed exceeds -$03",
        y_offsets=[0] + [-10] * len(rising_body) + [0],
    )

    sho_body = [1, 2, 3, 4, 2, 3, 4, 2, 3, 4, 5, 6, 7]
    for name, animation, startup, table in (
        ("Andy", "sho_ryu_dan_l", 3, "src/bank03.asm:MoveAnimTbl_Andy"),
        ("Athena", "psycho_sword_l", 2, "src/bank03.asm:MoveAnimTbl_Athena"),
    ):
        set_mid_timing(
            characters, name, animation, [0] + sho_body + [8],
            [startup] + [1] * 10 + [8, 1, 12, 9], 14,
            table=table,
            code="src/bank06.asm:MoveC_Andy_ShoRyuDan",
            branch="light -$0600 arc; #2-#4 threshold loops and landing frame #8",
            y_offsets=[0] + [-10] * len(sho_body) + [0],
        )

    leona_order = [0, 1, 2, 3] + [frame for _ in range(12) for frame in (4, 5)] + [4, 6, 7]
    set_mid_timing(
        characters, "Orochi_Leona", "leona_x_calibur_l", leona_order,
        [2, 1, 3, 8] + [1] * 25 + [3, 11], len(leona_order) - 2,
        table="src/bank03.asm:MoveAnimTbl_OLeona",
        code="src/bank02.asm:MoveC_Leona_XCalibur",
        branch="light distance-selected arc, #4/#5 loop until landing, 3+11 recovery",
        y_offsets=[0] + [-10] * (len(leona_order) - 3) + [0, 0],
    )

    set_mid_timing(
        characters, "Krauser", "leg_tomahawk_l", list(range(7)),
        [2, 1, 6, 14, 7, 7, 7], 4,
        table="src/bank03.asm:MoveAnimTbl_Krauser",
        code="src/bank09.asm:MoveC_Krauser_LegTomahawk",
        branch="light -$0400 arc, threshold frames #1/#2, landing sequence #4-#6",
        y_offsets=[0, -10, -10, -10, 0, 0, 0],
    )

    set_mid_timing(
        characters, "Goenitz", "shinyaotome_throw_h", list(range(7)),
        [3, 7, 7, 7, 24, 5, 5], 5,
        table="src/bank03.asm:MoveAnimTbl_Goenitz",
        code="src/bank0A.asm:MoveC_Goenitz_ShinyaotomeThrowH",
        branch="heavy throw, -$0600 jump, +$0060 gravity and grounded release",
        y_offsets=[0, 0, 0, -10, -10, 0, 0],
    )


def apply_migration(document: dict[str, object]) -> None:
    characters = document["characters"]

    # REV2's maximum B hold is fifteen #1/#2 cycles.  All source mappings are
    # retained; the release and friction tail stays finite for OLED playback.
    kyo = characters["Kyo"]["fast"]
    kyo["order"] = [0] + [frame for _ in range(15) for frame in (1, 2)] + list(range(3, 8))
    kyo["movement"] = ["fixed"] * 32 + ["move"] * 4
    set_timing(
        characters, "Kyo", [1] * 32 + [1, 8, 9, 9], 35,
        move="MOVE_KYO_URA_OROCHI_NAGI_D",
        table="src/bank03.asm:MoveAnimTbl_Kyo",
        code="src/bank06.asm:MoveC_Kyo_UraOrochiNagi",
        branch="REV2 maximum fifteen-cycle B charge, release and friction tail",
    )

    set_timing(
        characters, "Daimon",
        [11] + [6] * 4 + [5] * 4 + [4] * 4 + [3] * 4 + [2] * 4 + [1] * 3 + [11] * 2 + [101],
        24,
        move="MOVE_DAIMON_HEAVEN_HELL_DROP_S",
        table="src/bank03.asm:MoveAnimTbl_Daimon",
        code="src/bank05.asm:MoveC_Daimon_HeavenHellDrop",
        branch="successful command throw with two normal-super grab loops",
    )

    # Terry is the reviewed pilot and is composed by the projectile generator.

    andy = characters["Andy"]["fast"]
    andy["y_offsets"] = [0, 0, -10, -10, -10, 0]
    set_timing(
        characters, "Andy", [2, 2, 13, 5, 17, 19], 5,
        move="MOVE_ANDY_CHO_REPPA_DAN_S",
        table="src/bank03.asm:MoveAnimTbl_Andy",
        code="src/bank06.asm:MoveC_Andy_ChoReppaDan",
        branch="normal-super gravity path through landing frame #5",
    )

    # Successful rush collision is represented by four deterministic approach
    # positions.  The chained heavy uppercut uses its own gravity/landing phase.
    for name, body_end, code, uppercut in (
        ("Ryo", 25, "src/bank02.asm:MoveC_Ryo_RyuKoRanbuS", "MOVE_RYO_KO_HOU_H"),
        ("Robert", 20, "src/bank02.asm:MoveC_Robert_RyuKoRanbuS", "MOVE_ROBERT_RYUU_GA_H"),
    ):
        entry = characters[name]["fast"]
        entry["y_offsets"] = [0] * len(entry["order"])
        for step in range(body_end + 1, len(entry["order"]) - 1):
            entry["y_offsets"][step] = -10
        body_ticks = [9, 4, 4, 4, 4] + [2] * (body_end - 5)
        upper_ticks = [1, 1, 4, 4, 4, 4, 4, 4, 4, 7]
        set_timing(
            characters, name, body_ticks + upper_ticks, len(entry["order"]) - 1,
            move=f"MOVE_{name.upper()}_RYU_KO_RANBU_S -> {uppercut}",
            table=f"src/bank03.asm:MoveAnimTbl_{name}",
            code=code,
            branch="successful rush collision followed by heavy uppercut and landing",
        )

    characters["Athena"]["fast"] = {
        "animation": "shining_crystal_bit_as",
        "order": [0] + [frame for _ in range(14) for frame in (1, 2)] + list(range(3, 9)),
        "x_offsets": [0] * 35,
    }
    athena = characters["Athena"]["fast"]
    athena["y_offsets"] = [-10] * (len(athena["order"]) - 1) + [0]
    set_timing(
        characters, "Athena", [9] + [2] * 28 + [2, 1, 41, 4, 20, 4], 34,
        move="MOVE_ATHENA_SHINING_CRYSTAL_BIT_AS",
        table="src/bank03.asm:MoveAnimTbl_Athena",
        code="src/bank06.asm:MoveC_Athena_ShCryst",
        branch="air S, fourteen orbit loops, deterministic release and landing",
        projectile="src/bank06.asm:ProjC_Athena_ShCrystCharge",
    )

    mai = characters["Mai"]["fast"]
    mai["y_offsets"] = [(-10 if frame in (7, 8, 9) else 0) for frame in mai["order"]]
    set_timing(
        characters, "Mai", [1] * 32 + [19], 32,
        move="MOVE_MAI_CHO_HISSATSU_SHINOBIBACHI_D",
        table="src/bank03.asm:MoveAnimTbl_Mai",
        code="src/bank06.asm:MoveC_Mai_ChoHissatsuShinobibachiD",
        branch="desperation dash, gravity loop #8/#9, and landing frame #A",
    )

    leona = characters["Orochi_Leona"]["fast"]
    leona["y_offsets"] = [(-10 if frame in (7, 8, 9, 10, 11) else 0) for frame in leona["order"]]
    set_timing(
        characters, "Orochi_Leona", [2, 2, 2, 17] + [1] * 24 + [5, 5, 4, 4, 8, 9], 33,
        move="MOVE_OLEONA_SUPER_MOON_SLASHER_S",
        table="src/bank03.asm:MoveAnimTbl_OLeona",
        code="src/bank02.asm:MoveC_OLeona_SuperMoonSlasher",
        branch="successful hit, eight slash loops, backward gravity arc and landing",
    )

    characters.setdefault("Geese", {})["fast"] = {
        "animation": "raging_storm_s", "order": [0, 1, 2]
    }
    set_timing(
        characters, "Geese", [21, 1, 61], 2,
        move="MOVE_GEESE_RAGING_STORM_S",
        table="src/bank03.asm:MoveAnimTbl_Geese",
        code="src/bank06.asm:MoveC_Geese_RagingStorm",
        branch="normal super through frame #2 projectile spawn",
        projectile="src/bank06.asm:ProjInit_Geese_RagingStormS",
    )

    characters.setdefault("Krauser", {})["fast"] = {
        "animation": "kaiser_wave_s", "order": list(range(6))
    }
    set_timing(
        characters, "Krauser", [3, 3, 3, 3, 11, 3], 5,
        move="MOVE_KRAUSER_KAISER_WAVE_S",
        table="src/bank03.asm:MoveAnimTbl_Krauser",
        code="src/bank09.asm:MoveC_Krauser_KaiserWave",
        branch="normal Kaiser Wave spawn and recovery",
        projectile="src/bank09.asm:ProjInit_Krauser_KaiserWave",
    )

    set_timing(
        characters, "Goenitz", [2] * 4 + [3] * 3 + [5] * 8 + [3] * 4, 15,
        move="MOVE_GOENITZ_SHINYAOTOME_JISSOUKOKU_DL -> THROW_H/YONOKAZE",
        table="src/bank03.asm:MoveAnimTbl_Goenitz",
        code="src/bank0A.asm:MoveC_Goenitz_ShinyaotomeJissoukokuDL",
        branch="successful rush, lifted throw pose, two deterministic Yonokaze rounds",
        projectile="src/bank08.asm:ProjC_Goenitz_Yonokaze",
    )

    karate = characters["Mr_Karate"]["fast"]
    if len(karate["order"]) == 51:
        karate["y_offsets"] = [0] * len(karate["order"])
        karate["y_offsets"][35:38] = [-10, -10, -10]
        set_timing(
            characters, "Mr_Karate",
            [2] * 20 + [2] * 15 + [8] * 3 + [2] * 5 + [1] * 8,
            43,
            move="MOVE_MRKARATE_RYUKO_RANBU_S -> ZENRETSUKEN_H -> HOP_B -> HAOHS",
            table="src/bank03.asm:MoveAnimTbl_MrKarate",
            code="src/bank02.asm:MoveC_MrKarate_RyukoRanbuS",
            branch="legacy composite before reviewed D3 hop migration",
            projectile="src/bank02.asm:ProjC_MrKarate_HaohShoKohKen",
        )

    iori = characters["Orochi_Iori"]["fast"]
    set_timing(
        characters, "Orochi_Iori", [13, 6, 5, 5, 5] + [1] * 32, 35,
        move="MOVE_OIORI_KIN_YA_OTOME_S",
        table="src/bank03.asm:MoveAnimTbl_OIori",
        code="src/bank05.asm:MoveC_OIori_KinYaOtome",
        branch="successful dash, four #2-#5 loops, four #8/#9 loops, recovery",
        startup_source="MoveAnimTbl_OIori byte4=$0C; FrameTotal+1",
    )

    apply_mid_migration(characters)



def main() -> None:
    module_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "plan", nargs="?", type=Path, default=module_root / "data/fighter_playback.json"
    )
    args = parser.parse_args()
    document = json.loads(args.plan.read_text(encoding="utf-8"))
    apply_migration(document)
    args.plan.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
