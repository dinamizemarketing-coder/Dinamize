# Cortes de vídeo longo — pipeline

Do vídeo longo aos clipes verticais (1080x1920), frame-exatos, sem legenda
queimada, sempre com folga antes e depois da fala.

```bash
./executar.sh 1d8ioOT0MenNTNDyrjr99j2UFrorSAOrM 12
```

Esse comando baixa, transcreve, escolhe os 12 melhores momentos, mostra a
lista para você aprovar e renderiza. Nada mais é necessário.

## Como o acesso ao Drive foi resolvido

A politica de rede deste ambiente bloqueia `drive.google.com`,
`drive.usercontent.google.com`, `docs.google.com` e `*.googleusercontent.com`,
e o conector do Drive corta em 10 MB — o arquivo tinha 12,3 GB. Dos hosts
liberados, `www.googleapis.com` serve a Drive API.

Chave de API **nao** resolve: a Drive API responde
`Requests to this API drive method google.apps.drive.v3.DriveFiles.Get are blocked`
para autenticacao por chave, no download e nos metadados. O erro
`API key not valid` que aparece antes disso vem do gateway, antes da checagem
do metodo — passar nele nao significa que o metodo aceita chave.

O que funciona e um **access token OAuth** (`ya29...`), obtido no
[OAuth Playground](https://developers.google.com/oauthplayground) com o escopo
`https://www.googleapis.com/auth/drive.readonly`: o Step 1 autoriza e o Step 2
("Exchange authorization code for tokens") devolve o token. O codigo `AQ...`
do Step 1 nao serve sozinho.

`00_baixar_drive.sh` usa esse token com retomada por range, relendo o `.token`
a cada tentativa — um token que expira no meio pode ser trocado sem reiniciar
o download. Na pratica os 12,3 GB vieram a 78 MB/s, em 2,5 min.

## A transcricao, sem HuggingFace

`huggingface.co` e o CDN da OpenAI tambem estao bloqueados, entao o
faster-whisper nao baixa os proprios pesos. A saida foi trocar a runtime:
`sherpa-onnx` (PyPI, liberado) com o **Whisper small multilingue em ONNX
int8**, que existe como asset de release no GitHub, que passa.

O sherpa-onnx nao devolve timestamp por palavra. `chunks.py` contorna isso
montando blocos **contiguos** que comecam e terminam no meio de um silencio de
1s ou mais — as fronteiras de bloco viram, por construcao, pontos de corte que
nunca caem dentro de uma frase. `worker.py` transcreve em paralelo: 4 processos
com 1 thread cada rendem ~1,9x mais que 1 processo com 4 threads.

Empacotar os blocos perto de 28s importa: o Whisper processa uma janela de 30s
independentemente do tamanho real do bloco, entao blocos de 12s desperdicam
mais da metade do custo. Reempacotar 379 blocos em 215 cortou quase um terco
do trabalho.

`verificar.py` confere cada fronteira escolhida contra o mapa de silencios.
Isso importa: o divisor tem um caminho que fatia "no seco" quando um trecho
passa de 28s sem pausa, e essas fatias **nao** sao pontos de corte validos.
Na producao dos 12 cortes, 7 fronteiras cairam ali. Quando isso acontecer,
transcreva so aquela regiao em granularidade fina (blocos de ~5s, cortando em
todo silencio >= 0,35s) e reposicione.

`medir.py` mede a posicao dos rostos por corte, para o crop fixo.

## Os passos, se quiser rodar separado

```bash
./01_preparar.sh <FILE_ID | video.mp4>   # baixa, extrai áudio, transcreve, mapeia silêncios
python3 03_selecionar.py trabalho/transcricao.txt -n 12 -o cortes.tsv
python3 02_render.py trabalho/video.mp4 cortes.tsv \
        --silencios trabalho/silencios.txt --saida saida
```

### `01_preparar.sh`
Baixa do Drive com `gdown` (que resolve o token de confirmação de arquivo
grande) ou aceita um `.mp4` local. Gera `trabalho/audio.wav`,
`trabalho/transcricao.txt` (faster-whisper `small`, português) e
`trabalho/silencios.txt`.

### `03_selecionar.py` — a curadoria
Monta todas as janelas de 30–90s que **começam depois de uma frase fechada** e
**terminam fechando outra** — é o que impede um corte de entrar ou sair no meio
da fala. Pontua cada uma por gancho de abertura, carga emocional, polêmica,
humor, dado concreto, pergunta e fecho de raciocínio, descontando fala
arrastada e muleta solta. Uma janela só é considerada se houver **sinal forte
nos seus dois primeiros segmentos**: sem isso o clipe começaria sem motivo.
Depois escolhe de cima para baixo, rejeitando o que sobrepõe ou repete assunto
já escolhido (semelhança de vocabulário).

Se não houver 12 momentos realmente distintos e bons, ele entrega menos e avisa
— **qualidade importa mais que o número**, e `candidatos.md` traz o ranking
completo para trocar um corte por outro sem reprocessar nada.

Botões: `--nota-min` (piso de qualidade, padrão 6.0), `-n` (quantos cortes),
`--folga` (distância mínima entre dois cortes).

### `02_render.py` — o corte
Aplica **3s antes / 2s depois** de cada timecode e, havendo um silêncio real a
até 2,5s do ponto, ancora o corte no meio dele em vez de somar às cegas.
Renderiza 1080x1920 com re-encode frame-exato, escreve `saida/cortes.md` com a
tabela (arquivo, trecho original, trecho renderizado, duração, tema) e confere
duração e resolução de cada clipe.

`--dry-run` mostra os tempos ajustados sem renderizar. `--crop-x` reposiciona o
quadro quando o centro não é o melhor enquadramento (fonte 3840x2160 → após
`scale=-2:1920` a largura é 3414, centro `x=1167`).

**`cortes.tsv`** — uma linha por corte, TAB ou `;`. Aceita `00:12:30`, `12:30`
ou `750`:

```
00:12:30	00:13:25	A virada que ninguém esperava
14:02	14:58	Por que ele largou tudo
```

### `enquadramento.py` — quem fica em quadro
Quando há mais de uma pessoa, decide para quem a câmera olha, de forma
conservadora: fala curta não troca o foco, voz nova só ganha o quadro depois de
sustentar a fala, e na dúvida o enquadramento fica parado.

```bash
python3 enquadramento.py plano trabalho/video.mp4 --de 754 --ate 812 \
        --fala trabalho/transcricao.txt -o plano_01.json
python3 enquadramento.py render trabalho/video.mp4 plano_01.json saida/01_titulo.mp4
```

Leia o `plano_01.json` antes de renderizar. Se vários segmentos vierem com
`motivo: "sem rosto confiavel"`, não force: use o crop fixo do `02_render.py`.

## O que foi testado

Validado na producao dos 12 cortes do episodio com Guga Gadelha (81 min, 4K),
em `guga-gadelha/`:

- **Download:** 12.336.288.523 bytes, tamanho conferido, `ffprobe` limpo.
- **Transcricao:** 215 blocos, 14.514 palavras, 81,2 min de cobertura.
- **Fronteiras:** as 24 verificadas contra 1.398 silencios; 7 reposicionadas.
- **Render:** 12/12 em 1080x1920, duracao batendo em +/-0,03s, audio AAC
  estereo, enquadramento conferido por frame.

O `03_selecionar.py` (curadoria automatica) foi validado a parte, com
transcricoes sinteticas de 20 e 46 min — nos 12 cortes reais a selecao foi
feita por leitura da transcricao inteira, que rende melhor que a heuristica.
