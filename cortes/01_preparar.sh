#!/usr/bin/env bash
# 01_preparar.sh - baixa o video, extrai o audio, transcreve e mapeia os silencios.
# Uso: ./01_preparar.sh <FILE_ID_DO_DRIVE | caminho/do/video.mp4>
set -euo pipefail

ENTRADA="${1:?informe o FILE_ID do Drive ou o caminho do video}"
TRAB="${TRAB:-./trabalho}"
mkdir -p "$TRAB"
VIDEO="$TRAB/video.mp4"

command -v ffmpeg >/dev/null || { echo "instale o ffmpeg"; exit 1; }

if [ -f "$ENTRADA" ]; then
  VIDEO="$ENTRADA"
else
  # arquivo grande do Drive: o gdown resolve o token de confirmacao sozinho
  python3 -m pip install -q --upgrade gdown
  python3 -m gdown "$ENTRADA" -O "$VIDEO" --no-cookies
fi

ffprobe -v error -show_entries format=duration \
  -select_streams v:0 -show_entries stream=width,height,r_frame_rate \
  -of default=nw=1 "$VIDEO"

echo ">> extraindo audio"
ffmpeg -y -v error -i "$VIDEO" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$TRAB/audio.wav"

echo ">> mapeando silencios"
ffmpeg -v info -i "$TRAB/audio.wav" -af silencedetect=n=-32dB:d=0.35 -f null - 2>&1 \
  | grep -o 'silence_[a-z]*: [-0-9.]*' > "$TRAB/silencios.txt"

echo ">> transcrevendo (faster-whisper small, pt)"
python3 -m pip install -q faster-whisper
python3 - "$TRAB" <<'PY'
import sys
from faster_whisper import WhisperModel
trab = sys.argv[1]
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, info = m.transcribe(f"{trab}/audio.wav", vad_filter=True, language="pt")
with open(f"{trab}/transcricao.txt", "w", encoding="utf-8") as f:
    for s in segs:
        f.write(f"[{s.start:.2f} -> {s.end:.2f}] {s.text.strip()}\n")
print("transcricao pronta")
PY

echo
echo "Pronto. Envie para o Claude: $TRAB/transcricao.txt"
