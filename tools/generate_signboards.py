#!/usr/bin/env python3
"""
Gera todas as placas de sinalização (Place.msbt) de Link's Awakening (Melda)
utilizando ElevenLabs Turbo com voz de narrador expressivo e natural (Paulo).
Corrige problemas como o áudio corrompido de SBWeathercock que falava 'atue como narrador'.
"""

import argparse
import io
import json
import os
import re
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

ROOT_DIR = Path('/mnt/hd_externo/Projetos/Melda')
MSBT_DIR = ROOT_DIR / 'extracted/romfs/regionUS/USen/message'
DEST_DIR = ROOT_DIR / 'mods/Traducao_PTBR/voice'
ADB_TARGET = '/sdcard/Android/data/com.lasrecomp.android/files/mods/Traducao_PTBR/voice/'
DEFAULT_DEVICE = 'adb-RXCY308MNTN-BnRnBz._adb-tls-connect._tcp'

sys.path.insert(0, str(ROOT_DIR / 'tools/rando'))
from msbt import Msbt

VOICE_NARRATOR = 'Qrdut83w0Cr152Yb4Xn3'  # Paulo - Narrador brasileiro expressivo, firme e natural

BUTTON_NAMES = {
    14: 'Mais',
    15: 'Menos',
    21: 'X',
    22: 'Y',
    23: 'A',
    24: 'B',
    44: 'R',
    45: 'L',
    46: 'ZR',
    47: 'ZL'
}

def sanitize_for_speech(raw: bytes) -> str:
    out = []
    i = 0
    l = len(raw)
    while i < l:
        if raw[i] == 0x0e and i + 7 <= l:
            grp, typ, sz = struct.unpack_from('<HHH', raw, i + 1)
            data = raw[i + 7:i + 7 + sz]
            i += 7 + sz
            if grp == 1 and typ == 3:
                out.append('Luna')
                continue
            if grp == 1 and typ == 1 and len(data) >= 1:
                btn = BUTTON_NAMES.get(data[0], '')
                if btn:
                    out.append(f' {btn} ')
                continue
            continue
        if raw[i] == 0:
            break
        j = i
        while j < l and raw[j] not in (0, 0x0e):
            j += 1
        out.append(raw[i:j].decode('utf-8', 'replace'))
        i = j

    text = ''.join(out).strip()
    text = re.sub(r'\bLink\b', 'Luna', text)
    text = re.sub(r'\bLINK\b', 'Luna', text)
    text = re.sub(r'\blink\b', 'Luna', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def check_wav(path: Path):
    with wave.open(str(path), 'rb') as wf:
        channels, sampwidth, framerate, comptype = (
            wf.getnchannels(),
            wf.getsampwidth(),
            wf.getframerate(),
            wf.getcomptype()
        )
        if (channels, sampwidth, framerate, comptype) != (1, 2, 24000, 'NONE') or not wf.getnframes():
            raise ValueError(f'WAV inválido ({channels}ch, {sampwidth*8}bit, {framerate}Hz): {path}')

def push_file_to_adb(local_file: Path, device_serial: str = None):
    try:
        cmd = ['adb']
        if device_serial:
            cmd.extend(['-s', device_serial])
        cmd.extend(['push', str(local_file), ADB_TARGET])
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        chmod_cmd = ['adb']
        if device_serial:
            chmod_cmd.extend(['-s', device_serial])
        chmod_cmd.extend(['shell', f'chmod 777 {ADB_TARGET}/{local_file.name}'])
        subprocess.run(chmod_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f'   [ADB] Enviado com 777: {local_file.name}')
    except Exception as e:
        print(f'   [ADB] Falha de envio: {e}')

def generate_voice_cli(text: str, dest_file: Path, model_id: str = 'eleven_v4_turbo') -> bool:
    temp_file = dest_file.with_suffix('.partial.wav')
    if temp_file.exists():
        temp_file.unlink()

    # Tag emocional de narração clara e solene
    prompt_text = f"[calmly] [solemn] {text}"

    cmd = [
        'elevenlabs', 'text-to-speech', 'convert',
        '--voice-id', VOICE_NARRATOR,
        '--text', prompt_text,
        '--model-id', model_id,
        '--language-code', 'pt',
        '--output-format', 'wav_24000',
        '--voice-settings', json.dumps({'stability': 0.45, 'similarity_boost': 0.80, 'style': 0.35, 'use_speaker_boost': True}),
        '--output', str(temp_file),
        '--no-retry'
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        print(f'   [ERRO ELEVENLABS]: {res.stderr or res.stdout}')
        if temp_file.exists():
            temp_file.unlink()
        return False

    check_wav(temp_file)

    if dest_file.exists():
        dest_file.unlink()

    temp_file.rename(dest_file)
    return True

def main():
    parser = argparse.ArgumentParser(description='Gerador de placas de sinalização (Place.msbt) com ElevenLabs')
    parser.add_argument('--out', default=str(DEST_DIR))
    parser.add_argument('--device', default=DEFAULT_DEVICE)
    parser.add_argument('--no-push', action='store_true')
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.mkdir(parents=True, exist_ok=True)

    place_msbt = MSBT_DIR / 'Place.msbt'
    if not place_msbt.exists():
        sys.exit(f'Place.msbt não encontrado em {place_msbt}')

    m = Msbt(place_msbt.read_bytes())
    sb_keys = [k for k in m.texts if k.startswith('SB')]

    print('=' * 75)
    print(f'GERADOR DE PLACAS DE SINALIZAÇÃO - ELEVENLABS ({len(sb_keys)} placas)')
    print('Voz: Paulo (Qrdut83w0Cr152Yb4Xn3 - Expressivo, Firme e Natural)')
    print('=' * 75)

    success_count = 0
    for idx, k in enumerate(sorted(sb_keys), start=1):
        raw = m.texts[k]
        text = sanitize_for_speech(raw)
        if len(text) < 2:
            continue

        dest_wav = out_path / f'{k}.wav'

        print(f'\n[{idx}/{len(sb_keys)}] Gerando {k}:')
        print(f'   Texto: "{text}"')

        ok = generate_voice_cli(text, dest_wav)
        if ok:
            success_count += 1
            print(f'   [OK] Salvo: {dest_wav.name} ({dest_wav.stat().st_size} bytes)')
            if not args.no_push:
                push_file_to_adb(dest_wav, args.device)
            time.sleep(1.0)
        else:
            print(f'   [FALHA] Não foi possível gerar {k}.')

    print('\n' + '=' * 75)
    print(f'CONCLUÍDO: {success_count}/{len(sb_keys)} placas geradas e enviadas ao dispositivo.')
    print('=' * 75)

if __name__ == '__main__':
    main()
