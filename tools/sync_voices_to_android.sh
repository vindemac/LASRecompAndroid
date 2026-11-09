#!/usr/bin/env bash
set -euo pipefail

DEST_DIR="/mnt/hd_externo/Projetos/Melda/mods/Traducao_PTBR/voice"
ADB_TARGET="/sdcard/Android/data/com.lasrecomp.android/files/mods/Traducao_PTBR/voice/"

DEVICE="${1:-}"

if [ -z "$DEVICE" ]; then
    # Procura dispositivo ativo no adb devices
    DEVICE=$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')
fi

if [ -z "$DEVICE" ]; then
    echo "[ERRO] Nenhum dispositivo Android conectado no ADB."
    echo "Conecte via USB ou ative a Depuração por Wi-Fi no dispositivo e execute:"
    echo "  $0 <ip:porta_ou_serial>"
    exit 1
fi

echo "==========================================================================="
echo "SINCRONIZAÇÃO DE VOZES COM O DISPOSITIVO ANDROID ($DEVICE)"
echo "==========================================================================="

echo "[1/4] Garantindo diretório de destino no dispositivo..."
adb -s "$DEVICE" shell "mkdir -p '$ADB_TARGET'"

echo "[2/4] Enviando arquivos de áudio (.wav) para $ADB_TARGET..."
adb -s "$DEVICE" push "$DEST_DIR/." "$ADB_TARGET"

echo "[3/4] Ajustando permissões de leitura/escrita/execução (0777)..."
adb -s "$DEVICE" shell "chmod -R 777 '$ADB_TARGET'"

echo "[4/4] Verificando total de arquivos sincronizados..."
TOTAL_LOCAL=$(find "$DEST_DIR" -maxdepth 1 -name "*.wav" | wc -l)
TOTAL_REMOTE=$(adb -s "$DEVICE" shell "ls -1 '$ADB_TARGET'*.wav 2>/dev/null" | wc -l)

echo "Total local: $TOTAL_LOCAL arquivos WAV"
echo "Total no dispositivo: $TOTAL_REMOTE arquivos WAV"
echo "==========================================================================="
echo "Sincronização concluída com sucesso no dispositivo: $DEVICE"
echo "==========================================================================="
