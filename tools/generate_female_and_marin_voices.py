#!/usr/bin/env python3
"""
Gera dublagens com vozes femininas autênticas e alta expressividade para:
1. Marin (incluindo falas da praça, date na praia, pontes, quebra de vasos, etc.)
2. Vovó Yahoo (idosa enérgica)
3. Madam MeowMeow (burguesa extravagante)
4. Grande Fada (divina e etérea)
5. Sereia Martha (jovem atrevida)
6. Esposa de Papahl (maternal)
7. Hipopótama (modelo indignada)
8. Cucco Keeper (criadora de galinhas animada)
9. Bruxa da Floresta (voz rouca e mística)
10. Crazy Tracy (curandeira sedutora)

Corrige todas as vozes femininas que estavam indevidamente com voz masculina ou ausentes.
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
DEFAULT_DEVICE = '192.168.1.199:5555'

sys.path.insert(0, str(ROOT_DIR / 'tools/rando'))
from msbt import Msbt

# IDs de vozes femininas brasileiras no ElevenLabs
VOICE_AMANDA = 'oi8rgjIfLgJRsQ6rbZh3'    # Amanda Kelly - Jovem, doce, melódica (Marin, Grande Fada, Sereia, Tracy)
VOICE_BIANCA = 'HReOQZPV9tH5iTEnSbGo'    # Bianca - Idosa brasileira, expressiva e rouca (Vovó Yahoo, Bruxa)
VOICE_SULAMITA = 'XBqltNZ5pAkMg6TB8lGM'  # Sulamita - Mulher madura, distinta e firme (Madam MeowMeow, Mãe dos 4)
VOICE_ISABEL = '6hkkfs8V3kXPsN2SsF3W'    # Isabel - Mulher jovem adulta expressiva e enérgica (Criadora de Galinhas, Hipopótama)

FEMALE_CONFIG = {
    # =========================================================================
    # MARIN - Falas na Praça, Acompanhante e Reações Cênicas
    # =========================================================================
    'MarinSing1': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[cheerful] [playfully]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Marin na Praça (cantando e falando de Tarin colhendo cogumelos)'
    },
    'MarinSing2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[cheerful] [singing]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Marin na Praça (cantando sobre o dia lindo enquanto Tarin dorme)'
    },
    'MarinAfterBridge': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[tender] [wistful]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Marin após a ponte (revelando pedido secreto ao Peixe dos Ventos)'
    },
    'MarinAfterBridge2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[sadly] [emotional]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Marin após a ponte (despedida emotiva pedindo para nunca esquecê-la)'
    },
    'WantPlayGameMarin1': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[excited]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Marin animada querendo jogar o jogo da garra'
    },
    'WantPlayGameMarin2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[playfully] [excited]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Marin insistindo para jogar a garra'
    },
    'WantPlayGameMarin3': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[playfully]',
        'settings': {'stability': 0.38, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Marin reagindo à resposta do minigame'
    },
    'MarinDigHole': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[excited] [playfully]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Marin empolgada vendo Link cavar buraco'
    },
    'MarinBreakPot1': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[shocked] [playfully]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Marin fingindo bronca quando Link quebra vaso'
    },
    'MarinBreakPot2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[excited] [laughing]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Marin incentivando quebrar todos os vasos e rindo'
    },
    'MarinFall1': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[surprised] [gasping]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Marin assustada caindo no buraco'
    },
    'MarinFall2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[worried] [caring]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Marin se desculpando e perguntando se Link está bem'
    },
    'MarineWorry3': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[panicked] [worried]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Marin em pânico ao ver Link se machucar'
    },
    'MarineWorry4': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[flustered] [worried]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Marin envergonhada chamando Link de idiota com carinho'
    },
    'MarinCheckDresser': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[playfully] [teasing]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Marin flagrando Link mexendo na cômoda'
    },
    'MarinOcarinaHetakuso': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[giggle] [playfully]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Marin rindo do toque desafinado da ocarina'
    },

    # =========================================================================
    # VOVÓ YAHOO (Grandma Yahoo) - Idosa simpática, agitada e varrendo a rua
    # =========================================================================
    'Yahoo': {
        'source': 'Npc.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[excited] [cheerful]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo gritando YAHOO animada'
    },
    'YahooBeforeLv2': {
        'source': 'Npc.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[panicked] [worried]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo apavorada com a invasão dos moblins enquanto varre'
    },
    'YahooAfterWarashibe': {
        'source': 'Npc.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[excited] [cheerful]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo comemorando a vassoura nova'
    },
    'NoneYahooGranma': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[playfully]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Aviso de que a Vovó Yahoo foi para a Aldeia dos Animais'
    },

    # =========================================================================
    # MADAM MEOWMEOW (Mamamu Yan) - Senhora rica e apaixonada pelos Chomps
    # =========================================================================
    'WantRibbon1': {
        'source': 'Npc.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[doting] [pleading]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Madam MeowMeow bajulando CiaoCiao e querendo um laço'
    },
    'Lv3ReturnBowwow1': {
        'source': 'Scenario.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[laughing] [excited]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Madam MeowMeow rindo ho ho ho agradecendo pelo resgate do BowWow'
    },

    # =========================================================================
    # ESPOSA DE PAPAHL (Mãe dos Quadrigêmeos)
    # =========================================================================
    '4childMamaAfterWarashibe': {
        'source': 'Npc.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[tired] [affectionate]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Mãe dos 4 meninos desabafando sobre a confusão com os filhos'
    },
    'Worry4childMama': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[worried] [anxious]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Mãe dos quadrigêmeos preocupada com Papahl perdido na montanha'
    },

    # =========================================================================
    # GRANDE FADA (Great Fairy) - Voz divina, etérea e graciosa
    # =========================================================================
    'QuestGrandFairy1': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[warmly] [majestic]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Grande Fada dando as boas vindas e oferecendo poder das cores'
    },
    'QuestGrandFairy2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[calmly] [gentle]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Grande Fada explicando vermelho para ataque e azul para defesa'
    },
    'QuestGrandFairy3': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[curious]',
        'settings': {'stability': 0.38, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada perguntando se tem certeza da escolha'
    },
    'QuestGrandFairy4': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[calmly]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada explicando armadura vermelha vs túnica verde'
    },
    'QuestGrandFairy5': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[calmly]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada explicando armadura azul vs túnica verde'
    },
    'QuestGrandFairy6': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[curious]',
        'settings': {'stability': 0.38, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada perguntando se deseja manter a roupa'
    },
    'QuestGrandFairy7': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[warmly] [majestic]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Grande Fada cumprimentando e abençoando'
    },
    'QuestGrandFairy8': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[gentle]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada recomendando usar bem as roupas'
    },
    'ByebyeGrandFairy': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[warmly]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada teletransportando Link para fora'
    },
    'FairySpring': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[soothing] [gentle]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Fonte da Fada curando feridas e estresse'
    },
    'FairySpring2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[cheerful] [warmly]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Fonte da Fada elogiando a vitalidade de Link'
    },
    'AnswerGrandFairy_00': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[soothing]',
        'settings': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'use_speaker_boost': True},
        'desc': 'Grande Fada pedindo para fechar os olhos'
    },

    # =========================================================================
    # SEREIA MARTHA
    # =========================================================================
    'MermaidNearDive': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[sassy] [playfully]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Sereia Martha exigindo seu colar de volta antes de dar escamas'
    },

    # =========================================================================
    # HIPOPÓTAMA MODELO
    # =========================================================================
    'AngryHippo1': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[annoyed] [indignant]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Hipopótama pedindo para deixá-la posar em paz para a pintura'
    },
    'AngryHippo2': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[furious]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Hipopótama brava mandando parar'
    },

    # =========================================================================
    # CRIADORA DE GALINHAS (Cucco Keeper)
    # =========================================================================
    'CuccoKeeper': {
        'source': 'Npc.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[excited] [animated]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Criadora de Galinhas imitando asas e cocoricó'
    },
    'CuccoKeeperAttack1': {
        'source': 'Npc.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[angry]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Criadora de Galinhas gritando Ei você'
    },
    'CuccoKeeperAttack2': {
        'source': 'Npc.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[furious]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Criadora de Galinhas mandando parar de bater nas galinhas'
    },
    'CuccoKeeperAttack4': {
        'source': 'Npc.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[sternly] [angry]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Criadora expulsando Link do galinheiro'
    },
    'CuccoKeeperWithCocco': {
        'source': 'Npc.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[excited] [amazed]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Criadora maravilhada com o Galo Voador voando'
    },
    'FlyingCoccoKeeper': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_ISABEL,
        'tag': '[cheerful] [proudly]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Criadora comemorando que o Galo Voador é o melhor'
    },

    # =========================================================================
    # BRUXA DA FLORESTA (Witch)
    # =========================================================================
    'Rupee50MagicPowder': {
        'source': 'Npc.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[mysterious] [cackle]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Bruxa listando ingredientes bizarros e vendendo pó por 50 rúpias'
    },
    'NoRupee50MagicPowder': {
        'source': 'Npc.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[snappy] [sternly]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Bruxa exigindo dinheiro ou cogumelos'
    },

    # =========================================================================
    # CRAZY TRACY
    # =========================================================================
    'GreetingTracy': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[playfully] [seductive]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Tracy flertando e oferecendo pomada mágica'
    },
    'TracyRecovery': {
        'source': 'SubEvent.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[warmly] [magic]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Tracy aplicando pomada mágica curativa'
    },

    # =========================================================================
    # WARASHIBE (Trading Quest) - Linhas Femininas
    # =========================================================================
    # Christine (Cabra donzela)
    'QuestHibiscus': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[delighted] [warmly]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Christine encantada com o hibisco'
    },
    'WantHibiscus': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[sassy] [haughty]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Christine exigindo etiqueta e flores'
    },
    'ClearHibiscus': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[warmly] [pleading]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Christine pedindo para levar a carta ao Sr. Write'
    },
    'BadHibiscus': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[disappointed] [scoff]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Christine desapontada com a falta de gentileza'
    },

    # Madam MeowMeow / CiaoCiao (Troca da Fita)
    'QuestRibbon1': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[excited] [pleading]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'CiaoCiao desejando maquiagens, joias e vestidos'
    },
    'QuestRibbon2': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[excited] [doting]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'CiaoCiao implorando pela fita em troca de comida de cachorro'
    },
    'WantRibbon': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[longing] [dramatic]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'CiaoCiao suspirando por novos acessórios'
    },
    'ClearRibbon': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[delighted] [cheerful]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'CiaoCiao comemorando a fita e entregando comida'
    },
    'BadRibbon': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_SULAMITA,
        'tag': '[indignant] [angry]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'CiaoCiao indignada com a recusa'
    },

    # Sereia Martha (Troca do Colar / Sutiã)
    'QuestBra': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[excited] [pleading]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Sereia Martha implorando pelo retorno do colar'
    },
    'WantBra1': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[sadly] [worried]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Sereia Martha lamentando a perda do colar nas ondas'
    },
    'WantBra2': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[promising] [teasing]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.50, 'use_speaker_boost': True},
        'desc': 'Sereia Martha prometendo escama da cauda se encontrar'
    },
    'ClearBra': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[playfully] [sternly]',
        'settings': {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Sereia Martha alertando para pegar só uma escama'
    },
    'BadBra': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_AMANDA,
        'tag': '[pouting] [offended]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Sereia Martha chamando Link de sem coração'
    },

    # Vovó Yahoo (Troca da Vassoura)
    'QuestBroom': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[excited] [energetic]',
        'settings': {'stability': 0.30, 'similarity_boost': 0.75, 'style': 0.60, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo gritando YAHOO com a vassoura desgastada'
    },
    'WantBroom': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[amazed] [joyful]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.65, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo comemorando YUPIII com uma vassoura nova'
    },
    'ClearBroom': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[cheerful] [generous]',
        'settings': {'stability': 0.32, 'similarity_boost': 0.75, 'style': 0.55, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo entregando o anzol em troca da vassoura'
    },
    'BadBroom': {
        'source': 'Warashibe.msbt',
        'voice': VOICE_BIANCA,
        'tag': '[furious] [shouting]',
        'settings': {'stability': 0.28, 'similarity_boost': 0.75, 'style': 0.70, 'use_speaker_boost': True},
        'desc': 'Vovó Yahoo mandando Link varrer a ilha ele mesmo'
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
            # Nome do protagonista
            if grp == 1 and typ == 3:
                out.append('Luna')
                continue
            # Ícones de botões do controle
            if grp == 1 and typ == 1 and len(data) >= 1:
                btn_name = BUTTON_NAMES.get(data[0], '')
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
        print(f'   [ADB] Enviado e permissão 777 aplicada: {local_file.name}')
    except Exception as e:
        print(f'   [ADB] Aviso de envio para {device_serial}: {e}')

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

    # Backup caso o arquivo anterior exista (ex: voz masculina antiga)
    if dest_file.exists():
        backup_path = dest_file.with_name(f'{dest_file.stem}.backup_male.wav')
        if not backup_path.exists():
            dest_file.rename(backup_path)
        else:
            dest_file.unlink()

    temp_file.rename(dest_file)
    return True

def main():
    parser = argparse.ArgumentParser(description='Gerador de vozes femininas ElevenLabs para Link\'s Awakening (Melda)')
    parser.add_argument('--key', default=os.getenv('ELEVENLABS_API_KEY') or os.getenv('XI_API_KEY'),
                        help='Chave de API do ElevenLabs (opcional se autenticado via CLI OAuth)')
    parser.add_argument('--out', default=str(DEST_DIR), help='Diretório de saída dos WAVs')
    parser.add_argument('--model', default='eleven_v4_turbo',
                        choices=['eleven_v4_turbo', 'eleven_flash_v2_5', 'eleven_v4', 'eleven_multilingual_v2'],
                        help='Modelo ElevenLabs (padrão: eleven_v4_turbo para taxa 0.5x)')
    parser.add_argument('--specific', nargs='*', help='Filtrar para chaves específicas')
    parser.add_argument('--no-push', action='store_true', help='Não enviar via ADB para o dispositivo Android')
    parser.add_argument('--device', default=DEFAULT_DEVICE, help='Serial ADB do dispositivo')
    parser.add_argument('--force', action='store_true', help='Regenerar mesmo que backup_male exista')
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.mkdir(parents=True, exist_ok=True)

    print('=' * 75)
    print('GERADOR DE VOZES FEMININAS & MARIN NA PRAÇA (ELEVENLABS / MELDA)')
    print('=' * 75)

    sub = get_elevenlabs_subscription()
    if 'error' in sub:
        print(f'[Aviso] Não foi possível consultar saldo: {sub["error"]}')
    else:
        print(f'Saldo ElevenLabs: {sub["available"]} caracteres restantes (Usado: {sub["used"]}/{sub["limit"]}, Tier: {sub["tier"]})')
        print(f'Modelo selecionado: {args.model} (taxa de consumo 0.5x)')
    print('-' * 75)

    msbt_cache = {}
    for filename in {'Npc.msbt', 'Scenario.msbt', 'SubEvent.msbt', 'Warashibe.msbt'}:
        path = MSBT_DIR / filename
        if path.exists():
            msbt_cache[filename] = Msbt(path.read_bytes())
        else:
            print(f'Arquivo MSBT não encontrado: {path}')

    keys_to_process = list(FEMALE_CONFIG.keys())
    if args.specific:
        keys_to_process = [k for k in keys_to_process if k in args.specific]

    print(f'Total de falas femininas a processar: {len(keys_to_process)}')

    success_count = 0
    quota_exhausted = False

    for idx, key in enumerate(keys_to_process, start=1):
        config = FEMALE_CONFIG[key]
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

        backup_male = dest_wav.with_name(f'{key}.backup_male.wav')
        # Se dest_wav existe e foi gerado nesta sessão recente (< 2h), já está corrigido com ElevenLabs
        if dest_wav.exists() and not args.force:
            file_age = time.time() - dest_wav.stat().st_mtime
            if file_age < 7200:
                print(f'[{idx}/{len(keys_to_process)}] {key}: Já corrigido recentemente com ElevenLabs ({dest_wav.name}).')
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
            sub = get_elevenlabs_subscription()
            if sub.get('available', 1) <= 10:
                print('\n' + '!' * 75)
                print('[COTA ESGOTADA] O limite de caracteres do ElevenLabs para esta conta foi atingido.')
                print('!' * 75)
                quota_exhausted = True
                break
            else:
                print(f'   [FALHA] Falha ao processar {key}.')

    print('\n' + '=' * 75)
    print(f'RESUMO DE EXECUÇÃO: {success_count} falas femininas geradas e enviadas ao dispositivo.')
    print('=' * 75)

if __name__ == '__main__':
    main()
