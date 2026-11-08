#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define VOICE_EXPORT __attribute__((visibility("default")))

VOICE_EXPORT void voice_init(void);
VOICE_EXPORT void voice_play(const char *key);
VOICE_EXPORT void voice_stop(void);
VOICE_EXPORT void voice_on_msg_lookup(const char *s, uint64_t len);

#ifdef __cplusplus
}
#endif
