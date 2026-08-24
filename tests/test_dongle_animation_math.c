#include <assert.h>
#include <stddef.h>
#include <stdint.h>

#include "animation_math.h"

int main(void) {
    assert(zmk_dongle_animation_waits_for_paint(true, 0, 8, 0));
    assert(!zmk_dongle_animation_waits_for_paint(true, 0, 8, 1));
    assert(zmk_dongle_animation_waits_for_paint(false, 500, 8, 0));
    assert(zmk_dongle_animation_waits_for_paint(false, 500, 8, 7));
    assert(!zmk_dongle_animation_waits_for_paint(false, 500, 8, 6));
    assert(!zmk_dongle_animation_waits_for_paint(false, 0, 8, 0));

    assert(zmk_dongle_animation_charge_demo_band(0) == ZMK_DONGLE_ANIMATION_IDLE_BAND);
    assert(zmk_dongle_animation_charge_demo_band(1) == ZMK_DONGLE_ANIMATION_SLOW_BAND);
    assert(zmk_dongle_animation_charge_demo_band(2) == ZMK_DONGLE_ANIMATION_SLOW_BAND);
    assert(zmk_dongle_animation_charge_demo_band(3) == ZMK_DONGLE_ANIMATION_MID_BAND);
    assert(zmk_dongle_animation_charge_demo_band(4) == ZMK_DONGLE_ANIMATION_MID_BAND);
    assert(zmk_dongle_animation_charge_demo_band(5) == ZMK_DONGLE_ANIMATION_IDLE_BAND);
    assert(zmk_dongle_animation_charge_demo_band(6) == ZMK_DONGLE_ANIMATION_FAST_BAND);

    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_IDLE_BAND, false) == 0);
    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_SLOW_BAND, false) == 5);
    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_MID_BAND, false) == 10);
    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_FAST_BAND, false) == 0);
    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_SLOW_BAND, true) == 0);
    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_MID_BAND, true) == 50);
    assert(zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_FAST_BAND, true) == 0);
    assert(zmk_dongle_animation_charge_add(0, 5) == 5);
    assert(zmk_dongle_animation_charge_add(95, 10) == 100);
    assert(zmk_dongle_animation_charge_add(100, 10) == 100);
    uint8_t demo_charge = zmk_dongle_animation_charge_add(
        0, zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_MID_BAND, true));
    assert(demo_charge == 50);
    assert(!zmk_dongle_animation_charge_ready(demo_charge));
    demo_charge = zmk_dongle_animation_charge_add(
        demo_charge,
        zmk_dongle_animation_charge_gain(ZMK_DONGLE_ANIMATION_MID_BAND, true));
    assert(demo_charge == 100);
    assert(zmk_dongle_animation_charge_ready(demo_charge));
    assert(!zmk_dongle_animation_charge_ready(99));
    assert(zmk_dongle_animation_charge_ready(100));
    assert(zmk_dongle_animation_charge_wpm_band(ZMK_DONGLE_ANIMATION_IDLE_BAND) == 0);
    assert(zmk_dongle_animation_charge_wpm_band(ZMK_DONGLE_ANIMATION_SLOW_BAND) == 1);
    assert(zmk_dongle_animation_charge_wpm_band(ZMK_DONGLE_ANIMATION_MID_BAND) == 2);
    assert(zmk_dongle_animation_charge_wpm_band(ZMK_DONGLE_ANIMATION_FAST_BAND) == 2);
    assert(zmk_dongle_animation_charge_wpm_band(12) == 2);

    assert(zmk_dongle_animation_start_index(123, 0) == 0);
    assert(zmk_dongle_animation_next_index(0, 0) == 0);
    assert(zmk_dongle_animation_next_index(0, 1) == 0);

    bool boot_start_seen[14] = {false};
    size_t unique_boot_starts = 0;
    uint32_t boot_nonce = 0;
    for (size_t reset = 0; reset < 64; reset++) {
        boot_nonce += UINT32_C(0x9e3779b9);
        size_t start = zmk_dongle_animation_start_index(
            zmk_dongle_animation_mix_start_seed(UINT32_C(0x12345678), boot_nonce), 14);
        if (!boot_start_seen[start]) {
            boot_start_seen[start] = true;
            unique_boot_starts++;
        }
    }
    assert(unique_boot_starts >= 12);

    for (size_t count = 1; count <= 32; count++) {
        for (uint32_t random_value = 0; random_value < 256; random_value++) {
            size_t start = zmk_dongle_animation_start_index(random_value, count);
            assert(start < count);

            for (size_t current = 0; current < count; current++) {
                size_t next = zmk_dongle_animation_next_index(current, count);
                assert(next < count);
                if (count > 1) {
                    assert(next == (current + 1) % count);
                } else {
                    assert(next == 0);
                }
            }
        }
    }

    assert(zmk_dongle_animation_origin_x(128, 50) == 78);
    assert(zmk_dongle_animation_target_x(128, 50, 0) == 78);
    assert(zmk_dongle_animation_target_x(128, 50, 1) == 35);
    assert(zmk_dongle_animation_target_x(128, 50, 2) == 0);

    for (uint8_t count = 2; count <= 32; count++) {
        int32_t previous = 78;
        for (uint8_t frame = 0; frame < count; frame++) {
            int32_t x = zmk_dongle_animation_frame_x(78, 0, count, frame);
            assert(x <= previous);
            assert(x >= 0 && x <= 78);
            previous = x;
        }
        assert(zmk_dongle_animation_frame_x(78, 0, count, count - 1) == 0);
    }

    const uint8_t movement_steps[] = {0, 0, 1, 0, 1, 0};
    assert(zmk_dongle_animation_movement_count(movement_steps, 6) == 2);
    assert(zmk_dongle_animation_movement_index(movement_steps, 6, 0) == 0);
    assert(zmk_dongle_animation_movement_index(movement_steps, 6, 1) == 0);
    assert(zmk_dongle_animation_movement_index(movement_steps, 6, 2) == 1);
    assert(zmk_dongle_animation_movement_index(movement_steps, 6, 3) == 1);
    assert(zmk_dongle_animation_movement_index(movement_steps, 6, 4) == 2);
    assert(zmk_dongle_animation_movement_index(movement_steps, 6, 5) == 2);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, movement_steps, 6, 0) == 78);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, movement_steps, 6, 1) == 78);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, movement_steps, 6, 2) == 39);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, movement_steps, 6, 3) == 39);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, movement_steps, 6, 4) == 0);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, movement_steps, 6, 5) == 0);
    assert(zmk_dongle_animation_movement_count(NULL, 6) == 5);
    assert(zmk_dongle_animation_frame_x_steps(78, 0, NULL, 6, 5) == 0);

    const uint8_t return_steps[] = {0, 1, 1, 0, 1, 1, 0};
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 0, 4) == 78);
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 1, 4) == 39);
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 2, 4) == 0);
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 3, 4) == 0);
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 4, 4) == 39);
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 5, 4) == 78);
    assert(zmk_dongle_animation_frame_x_action(78, 0, return_steps, 7, 6, 4) == 78);

    for (uint32_t duration = 1; duration <= 1000; duration++) {
        for (uint8_t count = 1; count <= 32; count++) {
            uint32_t sum = 0;
            for (uint8_t frame = 0; frame < count; frame++) {
                sum += zmk_dongle_animation_frame_period(duration, count, frame, 0);
            }
            assert(sum == duration);
        }
    }

    for (uint8_t count = 2; count <= 32; count++) {
        uint32_t duration = 1000U + 200U * (count - 2U);
        uint32_t sum = 0;
        for (uint8_t frame = 0; frame < count; frame++) {
            uint32_t period =
                zmk_dongle_animation_frame_period(duration, count, frame, 500);
            assert(period == ((frame == 0 || frame == count - 1) ? 500U : 200U));
            sum += period;
        }
        assert(sum == duration);
    }

    assert(zmk_dongle_animation_frame_period(999, 2, 0, 500) == 0);
    assert(zmk_dongle_animation_frame_period(1001, 2, 0, 500) == 0);
    assert(zmk_dongle_animation_frame_period(1000, 1, 0, 500) == 0);

    return 0;
}
