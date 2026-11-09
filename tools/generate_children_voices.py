#!/usr/bin/env python3
"""
Gera dublagens para todas as crianças de Link's Awakening (Melda) utilizando a API do ElevenLabs.
Baseado na arquitetura e contratos de geração de voz do projeto MASHDEMU.
Garante vozes infantis dedicadas (Piku, Bittu, Vardan) em PCM 16-bit 24kHz mono.
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
try:
    from msbt import Msbt
except ImportError:
    Msbt = None

# Vozes infantis no ElevenLabs (todas adicionadas da Voice Library)
# Bittu: Menino enérgico, voz encorpada/moleque
# Vardan: Criança travessa, divertida, falante
# Piku: Criança expressiva, curiosa, infantil dramática
VOICE_BITTU = '4iqKdEXMW8NRF8USiS3Q'
VOICE_VARDAN = 'bBG9wwa23659EgIkMbc1'
VOICE_PIKU = 'EeQEodFZVtBkjtgK3HBc'

# Mapeamento de cada chave de criança para sua voz infantil, tags emocionais e configurações acústicas
CHILDREN_CONFIG = {
    # Alerta do sequestro do BowWow (duas crianças correndo pela vila em pânico absoluto, alternando as falas)
    'Lv2ChildHappening1': {
        'source': 'Scenario.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[panicked] [frantic]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Garoto 1 (Vardan) sem fôlego avisando do ataque moblin'
    },
    'Lv2ChildHappening2': {
        'source': 'Scenario.msbt',
        'voice': VOICE_BITTU,
        'tag': '[terrified] [screaming]',
        'settings': {'stability': 0.25, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Garoto 2 (Bittu) apavorado gritando que os monstros vieram'
    },
    'Lv2ChildHappening3': {
        'source': 'Scenario.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[panicked] [gasping]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Garoto 1 (Vardan) ofegante falando da gangue inteira de moblins'
    },
    'Lv2ChildHappening4': {
        'source': 'Scenario.msbt',
        'voice': VOICE_BITTU,
        'tag': '[alarmed] [frantic]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Garoto 2 (Bittu) apontando desesperado para a casa'
    },
    'Lv2ChildHappening5': {
        'source': 'Scenario.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[panicked] [worried]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Garoto 1 (Vardan) angustiado com o canil do BowWow'
    },
    'Lv2ChildHappening6': {
        'source': 'Scenario.msbt',
        'voice': VOICE_BITTU,
        'tag': '[terrified] [screaming]',
        'settings': {'stability': 0.25, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Garoto 2 (Bittu) tremendo de pavor e gritando ahh!'
    },
    'Lv2ChildHappening7': {
        'source': 'Scenario.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[urgent] [frantic]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Garoto 1 (Vardan) empurrando Link para ver com os próprios olhos'
    },
    'Lv2ChildHappening8': {
        'source': 'Scenario.msbt',
        'voice': VOICE_BITTU,
        'tag': '[alarmed] [anxious]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Garoto 2 (Bittu) arregalando os olhos dizendo que é sério'
    },
    'Lv2ChildHappening9': {
        'source': 'Scenario.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[terrified] [gasping]',
        'settings': {'stability': 0.25, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Garoto 1 (Vardan) traumatizado revivendo a cena com grito'
    },

    # Crianças e quadrigêmeos em Mabe Village
    'WeathercockChlid1': {
        'source': 'Npc.msbt',
        'voice': VOICE_BITTU,
        'tag': '[playfully] [giggle]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Garoto do Catavento debochando alegremente sobre Marin no oceano'
    },
    'WeathercockChlid2': {
        'source': 'Npc.msbt',
        'voice': VOICE_BITTU,
        'tag': '[worried] [gasping]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Garoto do Catavento assustado e preocupado com sumiço da Marin'
    },
    'TeaseChild': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_PIKU,
        'tag': '[hesitant] [nervous]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Criança tímida pega no flagra gaguejando nervosa'
    },
    'DreamshrineChild1': {
        'source': 'Npc.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[cheerful] [curious]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Garoto do Santuário dos Sonhos ensinando a salvar com empolgação'
    },
    'DreamshrineChild2': {
        'source': 'Npc.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[playfully] [laughing]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Garoto do Santuário rindo e zombando de Link sobre Marin'
    },
    'DreamshrineChild3': {
        'source': 'Npc.msbt',
        'voice': VOICE_VARDAN,
        'tag': '[whispering] [excited]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Garoto do Santuário sussurrando segredo com malícia infantil'
    },
    'MabeRedChild1': {
        'source': 'Npc.msbt',
        'voice': VOICE_BITTU,
        'tag': '[playfully] [enthusiastic]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Garoto de Vermelho gritando dica da Grande Fada jogando bola'
    },
    'MabeRedChild2': {
        'source': 'Npc.msbt',
        'voice': VOICE_BITTU,
        'tag': '[mysterious] [awed]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Garoto de Vermelho deslumbrado falando do ovo no Monte Tamaranch'
    },
    'MabeGreenChild1': {
        'source': 'Npc.msbt',
        'voice': VOICE_PIKU,
        'tag': '[curious] [confused]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Garoto de Verde curioso e intrigado com botões do mapa'
    },
    'MabeGreenChild2': {
        'source': 'Npc.msbt',
        'voice': VOICE_PIKU,
        'tag': '[wondering] [confused]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Garoto de Verde filosofando surpreso sobre o mundo exterior'
    },
    'ToolShopChlid1': {
        'source': 'Npc.msbt',
        'voice': VOICE_BITTU,
        'tag': '[excited] [bubbly]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Garoto da Loja falando super rápido sobre menus e controles'
    },
    'ToolShopChlid2': {
        'source': 'Npc.msbt',
        'voice': VOICE_BITTU,
        'tag': '[exasperated] [confused]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Garoto da Loja segurando a cabeça em choque e confusão'
    },
    'WantYosshi1': {
        'source': 'Npc.msbt',
        'voice': VOICE_PIKU,
        'tag': '[hopeful] [pleading]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Filhos de Papahl sonhando com o Boneco Yoshi para a mãe'
    },
    'WantYosshi2': {
        'source': 'Npc.msbt',
        'voice': VOICE_PIKU,
        'tag': '[excited] [awed]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Filhos de Papahl pulando de alegria vendo o Yoshi ganho'
    },
    'WantYosshi3': {
        'source': 'Npc.msbt',
        'voice': VOICE_PIKU,
        'tag': '[cheerful] [laughing]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Filhos de Papahl comemorando e rindo da mãe invejosa'
    }
}

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
            # Nome do jogador
            if grp == 1 and typ == 3:
                out.append('Luna')
                continue
            # Ícones de botões
            if grp == 1 and typ == 1 and len(data) >= 1:
                btn_code = data[0]
                btn_name = BUTTON_NAMES.get(btn_code, '')
                if btn_name:
                    out.append(f' {btn_name} ')
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
        print(f'   [ADB] Enviado com sucesso e chmod 777 aplicado: {local_file.name}')
    except Exception as e:
        print(f'   [ADB] Aviso: falha ao enviar via ADB para {device_serial}: {e}')

def get_elevenlabs_subscription():
    try:
        res = subprocess.run(['elevenlabs', 'user', 'subscription', 'get', '--format', 'json'],
                             capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        limit = data.get('character_limit', 0)
        used = data.get('character_count', 0)
        available = max(0, limit - used)
        return {'limit': limit, 'used': used, 'available': available, 'tier': data.get('tier', 'free')}
    except Exception as e:
        return {'error': str(e), 'available': 0}

def generate_voice_cli(voice_id: str, text_with_tag: str, dest_file: Path,
                       model_id: str = 'eleven_v4_turbo', voice_settings: dict = None,
                       api_key: str = None) -> bool:
    temp_file = dest_file.with_suffix('.partial.wav')
    if temp_file.exists():
        temp_file.unlink()

    cmd = [
        'elevenlabs', 'text-to-speech', 'convert',
        '--voice-id', voice_id,
        '--text', text_with_tag,
        '--model-id', model_id,
        '--language-code', 'pt',
        '--output-format', 'wav_24000',
        '--output', str(temp_file),
        '--no-retry'
    ]
    if voice_settings:
        cmd.extend(['--voice-settings', json.dumps(voice_settings)])
    if api_key:
        cmd.extend(['--xi-api-key', api_key])

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        err_msg = res.stderr or res.stdout
        print(f'   [ERRO CLI]: {err_msg.strip()}')
        if temp_file.exists():
            temp_file.unlink()
        return False

    check_wav(temp_file)

    # Backup do áudio anterior caso seja a primeira substituição
    if dest_file.exists():
        backup_path = dest_file.with_name(f'{dest_file.stem}.backup_gemini.wav')
        if not backup_path.exists():
            dest_file.rename(backup_path)
        else:
            dest_file.unlink()

    temp_file.rename(dest_file)
    return True

def main():
    parser = argparse.ArgumentParser(description='Gerador de vozes infantis ElevenLabs para Link\'s Awakening (Melda)')
    parser.add_argument('--key', default=os.getenv('ELEVENLABS_API_KEY') or os.getenv('XI_API_KEY'),
                        help='Chave de API do ElevenLabs (opcional se autenticado via CLI OAuth)')
    parser.add_argument('--out', default=str(DEST_DIR), help='Diretório de saída dos WAVs')
    parser.add_argument('--model', default='eleven_v4_turbo',
                        choices=['eleven_v4_turbo', 'eleven_flash_v2_5', 'eleven_v4', 'eleven_multilingual_v2'],
                        help='Modelo ElevenLabs (padrão: eleven_v4_turbo para custo 0.5x e alta expressividade)')
    parser.add_argument('--specific', nargs='*', help='Filtrar para chaves específicas de crianças')
    parser.add_argument('--no-push', action='store_true', help='Não enviar via ADB para o dispositivo Android')
    parser.add_argument('--device', default=DEFAULT_DEVICE, help='Serial ADB do dispositivo')
    parser.add_argument('--force', action='store_true', help='Sobrescrever mesmo se o arquivo já existir')
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.mkdir(parents=True, exist_ok=True)

    print('=' * 70)
    print('GERADOR DE VOZES INFANTIS - ELEVENLABS (MELDA / MASHDEMU PIPELINE)')
    print('=' * 70)

    # Consultar saldo
    sub = get_elevenlabs_subscription()
    if 'error' in sub:
        print(f'[Aviso] Não foi possível consultar saldo via CLI: {sub["error"]}')
    else:
        print(f'Saldo ElevenLabs: {sub["available"]} caracteres restantes (Usado: {sub["used"]}/{sub["limit"]}, Tier: {sub["tier"]})')
        print(f'Modelo selecionado: {args.model} (taxa de consumo reduzida 0.5x por caractere)')
    print('-' * 70)

    # Carregar arquivos MSBT
    msbt_cache = {}
    for filename in {'Npc.msbt', 'Scenario.msbt', 'SubEvent.msbt'}:
        path = MSBT_DIR / filename
        if path.exists():
            msbt_cache[filename] = Msbt(path.read_bytes())
        else:
            print(f'Arquivo MSBT não encontrado: {path}')

    keys_to_process = list(CHILDREN_CONFIG.keys())
    if args.specific:
        keys_to_process = [k for k in keys_to_process if k in args.specific]

    print(f'Total de falas de crianças catalogadas: {len(keys_to_process)}')

    success_count = 0
    quota_exhausted = False

    for idx, key in enumerate(keys_to_process, start=1):
        config = CHILDREN_CONFIG[key]
        src_file = config['source']
        if src_file not in msbt_cache:
            print(f'[{idx}/{len(keys_to_process)}] {key}: Arquivo {src_file} ausente.')
            continue

        raw = msbt_cache[src_file].texts.get(key)
        if not raw:
            print(f'[{idx}/{len(keys_to_process)}] {key}: Chave não encontrada no MSBT.')
            continue

        speech_text = sanitize_for_speech(raw)
        prompt_text = f"{config['tag']} {speech_text}"
        voice_id = config['voice']
        dest_wav = out_path / f'{key}.wav'

        # Verificar se já existe e não é para forçar
        # (se existir e já foi gerado nesta sessão ou tem backup_gemini, podemos considerar pronto)
        backup_gemini = dest_wav.with_name(f'{key}.backup_gemini.wav')
        if dest_wav.exists() and not args.force and backup_gemini.exists():
            print(f'[{idx}/{len(keys_to_process)}] {key}: Áudio infantil já gerado anteriormente ({dest_wav.name}).')
            continue

        print(f'\n[{idx}/{len(keys_to_process)}] Gerando {key} ({config["desc"]}):')
        print(f'   Voz: {voice_id} | Modelo: {args.model}')
        print(f'   Texto: "{prompt_text}"')

        success = generate_voice_cli(
            voice_id=voice_id,
            text_with_tag=prompt_text,
            dest_file=dest_wav,
            model_id=args.model,
            voice_settings=config.get('settings'),
            api_key=args.key
        )

        if success:
            success_count += 1
            print(f'   [OK] Salvo: {dest_wav.name} ({dest_wav.stat().st_size} bytes)')
            if not args.no_push:
                push_file_to_adb(dest_wav, args.device)
            time.sleep(1.0)
        else:
            # Checar se esgotou a cota
            sub = get_elevenlabs_subscription()
            if sub.get('available', 1) <= 10:
                print('\n' + '!' * 70)
                print('[COTA ESGOTADA] O limite de caracteres do ElevenLabs para esta conta foi atingido.')
                print(f'Caracteres restantes: {sub.get("available", 0)}.')
                print('!' * 70)
                quota_exhausted = True
                break
            else:
                print(f'   [FALHA] Falha ao processar {key}.')

    print('\n' + '=' * 70)
    print(f'RESUMO DE EXECUÇÃO: {success_count} falas infantis geradas com sucesso.')
    if quota_exhausted:
        print('Para gerar as falas restantes, autentique uma conta ElevenLabs com mais créditos:')
        print('   1. Execute: elevenlabs auth login')
        print('   OU passe a chave via: python3 tools/generate_children_voices.py --key SUA_CHAVE')
    print('=' * 70)

if __name__ == '__main__':
    main()
