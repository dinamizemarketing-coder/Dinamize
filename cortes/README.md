# Cortes de vídeo longo — pipeline

Do vídeo longo aos clipes verticais (1080x1920), frame-exatos, sem legenda
queimada, sempre com folga antes e depois da fala.

```bash
./executar.sh 1d8ioOT0MenNTNDyrjr99j2UFrorSAOrM 12
```

Esse comando baixa, transcreve, escolhe os 12 melhores momentos, mostra a
lista para você aprovar e renderiza. Nada mais é necessário.

## Por que o pipeline está aqui em vez dos clipes prontos

A sessão remota do Claude Code não alcança o arquivo. Os quatro caminhos
possíveis foram testados e todos estão fechados:

| Caminho | Resultado |
|---|---|
| `curl`/`gdown` nos hosts do Drive | 403 no CONNECT do proxy — `drive.google.com`, `drive.usercontent.google.com`, `docs.google.com` e `*.googleusercontent.com` estão fora da política de rede do ambiente |
| API do Drive via `www.googleapis.com` / `drive.googleapis.com` (hosts liberados) | `403 The request is missing a valid API key` — o arquivo é público (`type: anyone`), falta só uma chave de API, que a sessão não tem |
| Conector do Drive (`download_file_content`) | `File too large for download, over limit of 10 MB` — o arquivo tem 12.336 MB |
| Outro ambiente com rede diferente | só existe um ambiente na conta (`Default`), com esta mesma política |

Para rodar tudo dentro da sessão, basta liberar `drive.usercontent.google.com`
na política de rede do ambiente (Claude Code on the web → configurações do
ambiente → acesso de rede). Hosts que o ambiente **já** libera, caso seja mais
prático hospedar o arquivo: `github.com`, `objects.githubusercontent.com`,
`s3.amazonaws.com`, `www.googleapis.com`.

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

Sem o vídeo real, a validação foi feita com material sintético:

- **Render:** vídeo gerado com `testsrc`, cortes conferidos com `ffprobe` —
  durações exatas (21,0s / 20,0s / 38,7s), saída 1080x1920, tabela gerada.
- **Seleção:** transcrições sintéticas de 20 e 46 min. Na de 46 min saem 12
  cortes; com o piso de nota em 6.0, 9 — todos com gancho na abertura. Antes da
  regra de sinal forte, uma janela de conversa fiada (nota 3,68) entrava por
  forma; depois dela, não entra mais.
- **Cadeia inteira:** transcrição → `03_selecionar.py` → `02_render.py` →
  clipe 1080x1920 de 38,7s conferido.

O que **não** foi testado: o download do Drive (`gdown`) e a transcrição
(`faster-whisper`), porque ambos dependem de rede bloqueada nesta sessão.
