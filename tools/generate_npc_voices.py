#!/usr/bin/env python3
import argparse
import io
import os
import re
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path
from google import genai
from google.genai import types

sys.path.insert(0, '/mnt/hd_externo/Projetos/Melda/tools/rando')
from msbt import Msbt

VOICE_MAP = {
    # Homens idosos / voz rouca ou madura
    'tarin': 'Algenib',       # Tarin (Pai de Marin, homem mais velho, rechonchudo/Mario, guloso)
    'ulrira': 'Algenib',      # Vovô Ulrira (Ancião sábio e tímido)
    'danpei': 'Algenib',      # Dampé (Coveiro idoso e excêntrico)
    'fisherman': 'Algenib',   # Pescador sob a ponte

    # Mulheres jovens / doces / cantoras
    'marin': 'Aoede',         # Marin (Donzela de Koholint, jovem cantora, doce e expressiva)
    'tracy': 'Zephyr',        # Crazy Tracy (Curandeira jovem, misteriosa/sedutora)
    'christine': 'Aoede',     # Cabra Christine (Gentil, romântica)

    # Mulheres maduras / imponentes / idosas
    'madam': 'Kore',          # Madam MeowMeow (Senhora rica da vila, mãe dos Chain Chomps)
    'witch': 'Kore',          # Bruxa da floresta misteriosa
    'cackle': 'Kore',         # Bruxa
    'mrs': 'Kore',            # Esposa de Papahl / Mães

    # Crianças / Jovens animados
    'child': 'Puck',          # Crianças da aldeia Mabe / quadrigêmeos
    'boy': 'Puck',
    'kid': 'Puck',

    # Homens adultos / profissionais / nobres
    'shop': 'Orus',           # Lojista da loja de ferramentas (severo, firme)
    'richard': 'Orus',        # Príncipe Richard (Nobre teatral)
    'write': 'Orus',          # Sr. Write (Escritor culto)
    'papahl': 'Orus',         # Papahl (Pai trabalhador)
    'kiki': 'Puck',           # Macaco Kiki

    # Entidades místicas / solenes / narradores
    'owl': 'Charon',          # Coruja Kaepora Gaebora (Mística, profunda, solene)
    'windfish': 'Charon',     # Peixe dos Ventos
    'signboard': 'Charon',    # Placas de sinalização do mapa (Narrador neutro e grave)
    'default': 'Orus'
}

ADB_TARGET = '/sdcard/Android/data/com.lasrecomp.android/files/mods/Traducao_PTBR/voice/'

def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    if pcm_data.startswith(b'RIFF'):
        return pcm_data
    out = io.BytesIO()
    with wave.open(out, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return out.getvalue()

def sanitize_for_speech(raw: bytes) -> str:
    out = []
    i = 0
    l = len(raw)
    while i < l:
        if raw[i] == 0x0e and i + 7 <= l:
            grp, typ, sz = struct.unpack_from('<HHH', raw, i + 1)
            i += 7 + sz
            if grp == 1 and typ == 3:
                out.append('Luna')
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

def pick_voice(key: str) -> str:
    k = key.lower()
    if k.startswith('sb') or 'sign' in k:
        return VOICE_MAP['signboard']
    if 'owl' in k or 'kaepora' in k:
        return VOICE_MAP['owl']
    for name, v in VOICE_MAP.items():
        if name in k:
            return v
    return VOICE_MAP['default']

def push_file_to_adb(local_file: Path, device_serial: str = None):
    try:
        cmd = ['adb']
        if device_serial:
            cmd.extend(['-s', device_serial])
        cmd.extend(['push', str(local_file), ADB_TARGET])
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        chmod_cmd = ['adb']
        if device_serial:
            chmod_cmd.extend(['-s', device_serial])
        chmod_cmd.extend(['shell', f'chmod 777 {ADB_TARGET}/{local_file.name}'])
        subprocess.run(chmod_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f'   [ADB] Enviado e permissão 777 aplicada: {local_file.name}')
    except Exception as e:
        print(f'   [ADB] Falha ao enviar {local_file.name}: {e}')

def call_tts_api(client: genai.Client, text: str, voice: str) -> bytes:
    # Modelos em ordem de preferência/disponibilidade
    candidate_models = [
        'gemini-3.8-flash-tts',
        'gemini-3.8-flash-lite-tts',
        'gemini-2.5-flash-preview-tts',
        'gemini-3.1-flash-tts-preview'
    ]
    last_err = None
    for model_name in candidate_models:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=text,  # APENAS O TEXTO DA FALA, SEM INSTRUÇÕES DE SISTEMA
                config=types.GenerateContentConfig(
                    response_modalities=['AUDIO'],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice
                            )
                        )
                    )
                )
            )
            if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
                part = resp.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
        except Exception as e:
            last_err = e
            if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                continue
            raise e
    if last_err:
        raise last_err
    raise RuntimeError('Nenhum dado de áudio retornado pela API')

def generate_voice_pack(files_map: dict, out_dir: str, api_key: str, limit: int = None, delay: float = 6.0, push_adb: bool = True, device_serial: str = None):
    client = genai.Client(api_key=api_key)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    all_items = []
    for msbt_file, filter_prefix in files_map.items():
        if not os.path.exists(msbt_file):
            print(f'Arquivo MSBT não encontrado: {msbt_file}')
            continue
        m = Msbt(open(msbt_file, 'rb').read())
        for k, raw in m.texts.items():
            if filter_prefix and not k.startswith(filter_prefix):
                continue
            all_items.append((k, raw, msbt_file))

    print(f'Total de registros a processar: {len(all_items)}')
    generated = 0

    for idx, (key, raw, src_file) in enumerate(all_items):
        if limit and generated >= limit:
            print(f'Limite atingido ({limit} falas geradas).')
            break

        dest_file = out_path / f'{key}.wav'
        if dest_file.exists() and dest_file.stat().st_size > 1000:
            print(f'[{idx+1}/{len(all_items)}] Pulando existente: {dest_file.name}')
            continue

        text = sanitize_for_speech(raw)
        if len(text) < 2:
            continue

        voice = pick_voice(key)
        is_sb = key.startswith('SB')
        tipo = "Placa/Narrador" if is_sb else "NPC"
        print(f'[{idx+1}/{len(all_items)}] Gerando [{tipo} | {voice}]: {key} -> "{text[:60]}..."')

        success = False
        retries = 10
        while retries > 0 and not success:
            try:
                audio_data = call_tts_api(client, text, voice)
                wav_data = pcm_to_wav(audio_data)
                with open(dest_file, 'wb') as f:
                    f.write(wav_data)
                print(f'   Salvo: {dest_file.name} ({len(wav_data)} bytes)')
                generated += 1
                success = True
                if push_adb:
                    push_file_to_adb(dest_file, device_serial)
                if delay > 0:
                    time.sleep(delay)
            except Exception as e:
                err_msg = str(e)
                if '429' in err_msg or 'RESOURCE_EXHAUSTED' in err_msg:
                    print('   [Quota 429] Limite de requisições por minuto atingido. Aguardando 35 segundos...')
                    time.sleep(35)
                    retries -= 1
                else:
                    print(f'   Erro ao gerar {key}: {e}')
                    break

def main():
    parser = argparse.ArgumentParser(description='Gerador de dublagem e narração com Gemini TTS')
    parser.add_argument('--key', default=os.getenv('GEMINI_API_KEY'), help='Chave de API do Gemini')
    parser.add_argument('--out', default='/mnt/hd_externo/Projetos/Melda/mods/Traducao_PTBR/voice')
    parser.add_argument('--signboards', action='store_true', help='Gerar somente as placas de sinalização (Place.msbt)')
    parser.add_argument('--npcs', action='store_true', help='Gerar somente os diálogos de NPCs e Cenário')
    parser.add_argument('--limit', type=int, default=None, help='Limite de falas a gerar')
    parser.add_argument('--delay', type=float, default=6.0, help='Delay entre requisições em segundos (padrão: 6.0)')
    parser.add_argument('--specific', nargs='*', help='Chaves específicas a gerar')
    parser.add_argument('--no-push', action='store_true', help='Não enviar automaticamente para o celular via ADB')
    parser.add_argument('--device', default=os.getenv('ANDROID_SERIAL', 'adb-RXCY308MNTN-BnRnBz._adb-tls-connect._tcp'), help='Serial ADB do dispositivo alvo')
    args = parser.parse_args()

    if not args.key:
        sys.exit('Erro: Chave não informada. Passe via --key ou configure GEMINI_API_KEY.')

    base_romfs = '/mnt/hd_externo/Projetos/Melda/extracted/romfs/regionUS/USen/message'

    if args.specific:
        client = genai.Client(api_key=args.key)
        out_path = Path(args.out)
        out_path.mkdir(parents=True, exist_ok=True)
        sources = [
            f'{base_romfs}/Npc.msbt',
            f'{base_romfs}/Place.msbt',
            f'{base_romfs}/SubEvent.msbt',
            f'{base_romfs}/Scenario.msbt'
        ]
        all_texts = {}
        for s in sources:
            if os.path.exists(s):
                m = Msbt(open(s, 'rb').read())
                all_texts.update(m.texts)

        for key in args.specific:
            if key not in all_texts:
                print(f'Chave {key} não encontrada nos arquivos MSBT.')
                continue
            text = sanitize_for_speech(all_texts[key])
            voice = pick_voice(key)
            dest = out_path / f'{key}.wav'
            print(f'Gerando específica [{voice}]: {key} -> "{text}"')
            audio_data = call_tts_api(client, text, voice)
            wav_data = pcm_to_wav(audio_data)
            with open(dest, 'wb') as f:
                f.write(wav_data)
            print(f'Salvo com sucesso: {dest} ({len(wav_data)} bytes)')
            if not args.no_push:
                push_file_to_adb(dest, args.device)
            time.sleep(args.delay)
        return

    files_map = {}
    if args.signboards:
        files_map[f'{base_romfs}/Place.msbt'] = 'SB'
    elif args.npcs:
        files_map[f'{base_romfs}/Npc.msbt'] = None
        files_map[f'{base_romfs}/Scenario.msbt'] = None
        files_map[f'{base_romfs}/SubEvent.msbt'] = None
    else:
        files_map[f'{base_romfs}/Scenario.msbt'] = None
        files_map[f'{base_romfs}/Npc.msbt'] = None
        files_map[f'{base_romfs}/SubEvent.msbt'] = None
        files_map[f'{base_romfs}/Place.msbt'] = 'SB'

    generate_voice_pack(
        files_map=files_map,
        out_dir=args.out,
        api_key=args.key,
        limit=args.limit,
        delay=args.delay,
        push_adb=not args.no_push,
        device_serial=args.device
    )

if __name__ == '__main__':
    main()
