// Frame pacing: the game's speed doesn't depend on the frame rate.
// The game advances its world each frame by its frame period (16.67 ms) times the swap interval its frame timer
// (f_700000c910) reads from the system object - normally 1. When a frame takes longer than a vsync (GPU-bound at
// 32:9, a hitch), the next frame starts a vsync later but still advanced only 16.67 ms: slow motion (30 fps = half
// speed). tools/patches.py FRAME_STEPS_SITE routes that read here: we return how many vsyncs really passed since
// the last frame, so the world advances by the time that passed. The game's own waiting is unaffected (it reads
// the interval nowhere else). Shared by the macOS and Windows builds.
// FINDING (2026-10-09): forcing 2 steps did NOT change Link's walking speed - gameplay is a true fixed step per
// frame; this timer feeds something else. Kept for research, off by default.
//   LARECOMP_FRAMEPACE=1     hand the timer the vsyncs elapsed (default: the game's own value)
//   LARECOMP_FRAME_STEPS_MAX maximum steps per frame (default 4: after a long stall the game doesn't jump ahead)
//   LARECOMP_FORCE_STEPS=<n> (test) always n
#include <stdlib.h>

#include "../hle.h"

extern volatile uint64_t g_vsync_count;  // runtime/hle/vi.c
uint64_t g_frame_steps_late;             // (stats) frames that advanced more than one step

#ifdef __ANDROID__
#include "../settings.h"
// Frame rate 30 (Video): the frame timer picks its interval from the vsyncs a frame really took, clamped to its
// state's minimum (+0x4e2) and maximum (+0x4e3); its GPU time only lets it step down. A frame that fits one vsync
// (Turnip with the render thread) brought the 60 fps mode back however slow the counters said the GPU was. So for
// the fixed 30 the minimum is raised to the maximum - the game's own 30 fps mode, two world steps a frame - and put
// back for Auto / 60. (We are inside the frame timer here, tools/patches.py FRAME_STEPS_SITE: x23 is its state.)
// Auto holds its 30 the same way while the pacer (vulkan/exec.c) holds it: the counters alone left the game choosing
// 60 for one frame in eight (2026-10-23, the stock driver at 23 ms of GPU a frame: slow motion in each) - after
// LASRecomp beta_5 cb9bc8d, "a real 30".
static void fixed_30(void) {
    Cpu *c = kernel_current_cpu();
    uint64_t sys = c ? c->x[23] : 0;
    if (!sys) return;
    // In sys (main_000.c:8663, 0x01000000 at +0x4e0):
    //   +0x4e0 = extra world updates per frame (0 = 60 fps [1 tick/frame], 1 = 30 fps [2 ticks/frame])
    //   +0x4e1 = swap_interval - 1             (0 = 60 fps [interval 1],   1 = 30 fps [interval 2])
    //   +0x4e2 = min (0 = 60 fps)
    //   +0x4e3 = max (1 = 30 fps)
    uint8_t *min   = (uint8_t *)(uintptr_t)(sys + 0x4e2);
    uint8_t *max   = (uint8_t *)(uintptr_t)(sys + 0x4e3);
    extern bool vk_pace_holds_30(void);
    bool auto_hold = g_settings.fps_mode == 0 && vk_pace_holds_30();
    if (g_settings.fps_mode == 1 || auto_hold) {
        if (*min != 1 || *max != 1) {
            *min = 1;
            *max = 1;
            LOG("[pace] %s: the game's interval clamped to [1, 1] (30 fps)\n", auto_hold ? "auto holds 30" : "frame rate 30");
        }
    } else {
        // Auto (0) or 60 fps (2): allow 60 fps (min=0) and allow 30 fps if GPU is overloaded (max=1)
        // so that if framerate drops to 30 fps (e.g. in 4K), 2 steps/frame run and game does NOT slow down!
        if (*min != 0 || *max != 1) {
            *min = 0;
            *max = 1;
            LOG("[pace] the game's interval set to [0, 1] (dynamic 60/30 fps, no slow-motion)\n");
        }
    }
}
#endif

uint32_t rt_frame_steps(uint32_t interval) {
#ifdef __ANDROID__
    fixed_30();
    if (g_settings.fps_mode == 1) return 2;
    // For mode 0 (Auto) and mode 2 (60 fps): return the game's actual interval (1 at 60 fps, 2 at 30 fps)
    // so gameplay speed is ALWAYS 1.0x real time, even when rendering at 4K drops to 30 fps!
    return interval;
#endif
    static int on = -1, max_steps, forced;
    if (on < 0) {
        const char *e = ENV("LARECOMP_FRAMEPACE");
        on = e ? atoi(e) != 0 : 0;  // off by default: the world (Link's movement) doesn't use this step (tested)
        e = ENV("LARECOMP_FRAME_STEPS_MAX");
        max_steps = e ? atoi(e) : 4;
        if (max_steps < 1) max_steps = 1;
        e = ENV("LARECOMP_FORCE_STEPS");
        forced = e ? atoi(e) : 0;
    }
    static int ncall;
    if (ENV("LARECOMP_LOG_FRAMEPACE") && ncall++ % 120 == 0) LOG("[framepace] call %d interval %u vsync %llu\n", ncall, interval, (unsigned long long)g_vsync_count);
    if (forced > 0) return (uint32_t)forced;
    static uint64_t last;
    uint64_t now = __atomic_load_n(&g_vsync_count, __ATOMIC_RELAXED);
    uint64_t steps = last ? now - last : 1;
    last = now;
    if (!on) return interval;
    if (steps < interval) steps = interval;  // (the game's own 30 fps mode: it waits that many vsyncs anyway)
    if (steps < 1) steps = 1;
    if (steps > (uint64_t)max_steps) steps = (uint64_t)max_steps;
    if (steps > 1) g_frame_steps_late++;
    return (uint32_t)steps;
}
