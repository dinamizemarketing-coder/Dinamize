# Cortes de vídeo longo — pipeline

Gera cortes verticais (1080x1920), frame-exatos, sem legenda queimada, sempre
com folga antes e depois da fala.

## Por que o pipeline está aqui em vez dos clipes prontos

A sessão remota do Claude Code não consegue buscar o arquivo: a política de
rede do ambiente bloqueia `drive.google.com`, `drive.usercontent.google.com`,
`docs.google.com` e `*.googleusercontent.com` (403 no CONNECT do proxy). O
conector do Drive lê arquivos, mas devolve o conteúdo em base64 dentro da
resposta da ferramenta — inviável para um `.mp4` de 12,3 GB.

Duas saídas:

1. **Liberar o Drive na política de rede do ambiente** (Claude Code on the web →
   configurações do ambiente → acesso de rede). Depois disso o pipeline roda
   inteiro na sessão.
2. **Rodar localmente**, com os passos abaixo.

Hosts que o ambiente já libera, caso seja mais fácil hospedar o arquivo:
`github.com`, `objects.githubusercontent.com`, `s3.amazonaws.com`,
`www.googleapis.com`.

## Uso

```bash
# 1) baixar, extrair áudio, transcrever e mapear os silêncios
./01_preparar.sh 1d8ioOT0MenNTNDyrjr99j2UFrorSAOrM      # ou ./01_preparar.sh video.mp4
# -> trabalho/video.mp4, trabalho/audio.wav, trabalho/transcricao.txt, trabalho/silencios.txt

# 2) escolher os 12 momentos (é o passo em que o Claude entra: mande a
#    transcricao.txt e ele devolve o cortes.tsv com os timecodes e os temas)

# 3) renderizar
python3 02_render.py trabalho/video.mp4 cortes.tsv \
    --silencios trabalho/silencios.txt --saida saida
```

`02_render.py` aplica **3s antes / 2s depois** de cada timecode e, havendo um
silêncio real a até 2,5s do ponto, ancora o corte no meio dele — é o que evita
entrar ou sair no meio da frase. `--dry-run` mostra os tempos ajustados sem
renderizar. `--crop-x` reposiciona o quadro 9:16 quando o centro não é o melhor
enquadramento (fonte 3840x2160 → após `scale=-2:1920` a largura é 3414, centro
`x=1167`).

Ao final ele escreve `saida/cortes.md` com a tabela (arquivo, trecho original,
trecho renderizado, duração, tema) e confere duração e resolução de cada clipe.

### cortes.tsv

Uma linha por corte, TAB ou `;` entre os campos. Aceita `00:12:30`, `12:30` ou
`750`:

```
00:12:30	00:13:25	A virada que ninguém esperava
14:02	14:58	Por que ele largou tudo
```

### Enquadramento por falante

Quando há mais de uma pessoa em quadro, `enquadramento.py` decide para quem a
câmera olha — de forma conservadora: fala curta não troca o foco, voz nova só
ganha o quadro depois de sustentar a fala, e na dúvida o enquadramento fica
parado.

```bash
python3 enquadramento.py plano trabalho/video.mp4 --de 754 --ate 812 \
    --fala trabalho/transcricao.txt -o plano_01.json
python3 enquadramento.py render trabalho/video.mp4 plano_01.json saida/01_titulo.mp4
```

Leia o `plano_01.json` antes de renderizar. Se vários segmentos vierem com
`motivo: "sem rosto confiavel"`, não force: use o crop fixo do `02_render.py`.
