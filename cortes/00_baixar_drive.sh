#!/usr/bin/env bash
# baixa o arquivo do Drive com access token OAuth, com retomada.
cd "$(dirname "$0")"
ID="${DRIVE_FILE_ID:?informe o FILE_ID}"
URL="https://www.googleapis.com/drive/v3/files/$ID?alt=media"
ESPERADO=12336288523
log(){ echo "[$(date +%H:%M:%S)] $*" >> baixar.log; }

: > baixar.log
[ -s .token ] || { log "ABORTADO: sem .token"; exit 1; }

log "checando o token"
T=$(cat .token)
code=$(curl -sS -m 45 -H "Authorization: Bearer $T" -r 0-65535 -o p.bin -w "%{http_code}" "$URL" || echo 000)
if [ "$code" = "000" ] || head -c 1 p.bin 2>/dev/null | grep -q '{'; then
  log "ABORTADO: token recusado (HTTP $code)"; head -c 300 p.bin >> baixar.log; rm -f p.bin; exit 1
fi
rm -f p.bin
log "token OK (HTTP $code) - baixando 12,3 GB com retomada"

for t in $(seq 1 12); do
  T=$(cat .token)                       # rele a cada volta: permite trocar o token no meio
  curl -sS -L -C - --retry 5 --retry-delay 5 --retry-all-errors \
       -H "Authorization: Bearer $T" -o video.mp4 "$URL" 2>>baixar.log
  sz=$(stat -c%s video.mp4 2>/dev/null || echo 0)
  log "tentativa $t: $sz / $ESPERADO bytes ($((sz*100/ESPERADO))%)"
  [ "$sz" = "$ESPERADO" ] && break
  if tail -c 300 video.mp4 2>/dev/null | grep -q '401'; then
    log "TOKEN EXPIROU - cole um ya29 novo em .token; retomo em 60s"; sleep 60
  else
    sleep 8
  fi
done

sz=$(stat -c%s video.mp4 2>/dev/null || echo 0)
if [ "$sz" = "$ESPERADO" ]; then
  log "OK - tamanho confere"
  ffprobe -v error -show_entries format=duration -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate -of default=nw=1 video.mp4 >> baixar.log 2>&1
else
  log "INCOMPLETO: $sz bytes"
fi
log "FIM"
