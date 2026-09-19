#!/usr/bin/env bash
# executar.sh - do video aos clipes, num comando so.
# Uso: ./executar.sh <FILE_ID_DO_DRIVE | video.mp4> [quantidade_de_cortes]
set -euo pipefail
cd "$(dirname "$0")"

ENTRADA="${1:?informe o FILE_ID do Drive ou o caminho do video}"
N="${2:-12}"
export TRAB="${TRAB:-./trabalho}"

./01_preparar.sh "$ENTRADA"
python3 03_selecionar.py "$TRAB/transcricao.txt" -n "$N" \
        -o cortes.tsv --candidatos candidatos.md

echo
echo ">> Cortes propostos acima. Enter renderiza; Ctrl-C para editar o cortes.tsv antes."
read -r _

VIDEO="$TRAB/video.mp4"; [ -f "$ENTRADA" ] && VIDEO="$ENTRADA"
python3 02_render.py "$VIDEO" cortes.tsv --silencios "$TRAB/silencios.txt" --saida saida

echo
echo ">> Pronto: saida/  (clipes + cortes.md)"
