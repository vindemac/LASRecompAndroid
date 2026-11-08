#include "voice.h"
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include "../hle.h"
#include "../paths.h"

#ifdef __ANDROID__
#include <android/log.h>
#define LOG_VOICE(...) __android_log_print(ANDROID_LOG_INFO, "LASRecomp", __VA_ARGS__)
#else
#define LOG_VOICE(...) fprintf(stderr, __VA_ARGS__)
#endif

static SDL_AudioStream *g_voice_stream = NULL;

void voice_init(void) {
    if (g_voice_stream) return;
    SDL_AudioSpec spec = {SDL_AUDIO_S16, 1, 24000};
    g_voice_stream = SDL_OpenAudioDeviceStream(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec, NULL, NULL);
    if (g_voice_stream) {
        SDL_ResumeAudioStreamDevice(g_voice_stream);
        LOG_VOICE("[voice] Subssistema de dublagem inicializado via SDL3 (stream=%p).\n", (void *)g_voice_stream);
    } else {
        LOG_VOICE("[voice] FALHA ao inicializar SDL_OpenAudioDeviceStream: %s\n", SDL_GetError());
    }
}

void voice_play(const char *key) {
    if (!key || !key[0]) return;
    if (!g_voice_stream) voice_init();
    if (!g_voice_stream) return;

    char path[512];
    const char *root = rt_data_root();
    bool found = false;

    // Tentativa 1: Caminho absoluto com rt_data_root()
    if (root && root[0] == '/') {
        snprintf(path, sizeof(path), "%s/mods/Traducao_PTBR/voice/%s.wav", root, key);
        if (access(path, R_OK) == 0) found = true;
    }

    // Tentativa 2: getcwd absoluto
    if (!found) {
        char cwd[256];
        if (getcwd(cwd, sizeof(cwd)) && cwd[0] == '/') {
            snprintf(path, sizeof(path), "%s/mods/Traducao_PTBR/voice/%s.wav", cwd, key);
            if (access(path, R_OK) == 0) found = true;
        }
    }

    // Tentativa 3: Caminho externo Android padrao (/storage/emulated/0)
    if (!found) {
        snprintf(path, sizeof(path), "/storage/emulated/0/Android/data/com.lasrecomp.android/files/mods/Traducao_PTBR/voice/%s.wav", key);
        if (access(path, R_OK) == 0) found = true;
    }

    // Tentativa 4: Link simbolico /sdcard
    if (!found) {
        snprintf(path, sizeof(path), "/sdcard/Android/data/com.lasrecomp.android/files/mods/Traducao_PTBR/voice/%s.wav", key);
        if (access(path, R_OK) == 0) found = true;
    }

    // Tentativa 5: Relativo (fallback)
    if (!found) {
        snprintf(path, sizeof(path), "mods/Traducao_PTBR/voice/%s.wav", key);
        if (access(path, R_OK) == 0) found = true;
    }

    if (!found) {
        LOG_VOICE("[voice] Arquivo de audio nao encontrado para chave '%s'\n", key);
        return;
    }

    LOG_VOICE("[voice] Arquivo localizado: '%s'. Carregando...\n", path);

    FILE *f = fopen(path, "rb");
    if (!f) {
        LOG_VOICE("[voice] Falha ao abrir via fopen '%s': %s\n", path, strerror(errno));
        return;
    }

    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (fsize <= 44) {
        fclose(f);
        LOG_VOICE("[voice] Arquivo corrompido ou muito pequeno: %ld bytes\n", fsize);
        return;
    }

    void *buffer = malloc(fsize);
    if (!buffer) {
        fclose(f);
        return;
    }

    size_t read_bytes = fread(buffer, 1, fsize, f);
    fclose(f);

    SDL_IOStream *io = SDL_IOFromConstMem(buffer, read_bytes);
    if (!io) {
        free(buffer);
        LOG_VOICE("[voice] SDL_IOFromConstMem falhou: %s\n", SDL_GetError());
        return;
    }

    SDL_AudioSpec wav_spec;
    uint8_t *wav_data = NULL;
    uint32_t wav_len = 0;

    if (SDL_LoadWAV_IO(io, true, &wav_spec, &wav_data, &wav_len)) {
        LOG_VOICE("[voice] REPRODUZINDO FALA [%s]: (%u bytes, %d Hz, %d ch)\n",
                  key, wav_len, wav_spec.freq, wav_spec.channels);
        SDL_ClearAudioStream(g_voice_stream);
        SDL_SetAudioStreamFormat(g_voice_stream, &wav_spec, NULL);
        SDL_PutAudioStreamData(g_voice_stream, wav_data, wav_len);
        SDL_ResumeAudioStreamDevice(g_voice_stream);
        SDL_free(wav_data);
    } else {
        LOG_VOICE("[voice] SDL_LoadWAV_IO falhou (%s). Tentando como PCM cru (24000 Hz, 1 ch, S16)...\n", SDL_GetError());
        SDL_AudioSpec raw_spec = {SDL_AUDIO_S16, 1, 24000};
        SDL_ClearAudioStream(g_voice_stream);
        SDL_SetAudioStreamFormat(g_voice_stream, &raw_spec, NULL);
        SDL_PutAudioStreamData(g_voice_stream, buffer, fsize);
        SDL_ResumeAudioStreamDevice(g_voice_stream);
    }

    free(buffer);
}

void voice_stop(void) {
    if (g_voice_stream) {
        SDL_ClearAudioStream(g_voice_stream);
    }
}

void voice_on_msg_lookup(const char *s, uint64_t len) {
    if (!s || len < 3) return;

    // Ignora mensagens de interface e metadados de orador
    if (!strncmp(s, "Talker:", 7) || !strncmp(s, "UI:", 3)) {
        return;
    }

    char debug_buf[128];
    size_t dlen = len < sizeof(debug_buf) ? len : sizeof(debug_buf) - 1;
    memcpy(debug_buf, s, dlen);
    debug_buf[dlen] = '\0';
    LOG_VOICE("[voice] Interceptado: '%s'\n", debug_buf);

    const char *colon = memchr(s, ':', len);
    if (colon) {
        const char *k = colon + 1;
        size_t klen = len - (size_t)(k - s);
        if (klen > 0 && klen < 120) {
            char key[128];
            memcpy(key, k, klen);
            key[klen] = '\0';
            voice_play(key);
        }
        return;
    }

    if (len < 120) {
        char key[128];
        memcpy(key, s, len);
        key[len] = '\0';
        voice_play(key);
    }
}
