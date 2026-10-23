# Briefing: vinheta animada do Auto Posto Santa Fé

Cole este arquivo inteiro no chat do Claude que tem acesso ao seu computador. Ele foi escrito para o Claude continuar o trabalho de onde parou.

---

## Para o Claude: o que eu preciso

Sou da Dinamize Marketing. Começamos uma vinheta animada de 16 segundos, em formato vertical para Reels e Stories, para o cliente **Auto Posto Santa Fé**, um posto Shell em Santa Bárbara de Goiás. A vinheta já existe e tem as cores da marca. Agora quero que ela fique parecida com o posto de verdade.

Tenho fotos reais do posto no meu computador: `[COLE AQUI O CAMINHO DA PASTA COM AS FOTOS]`

### Tarefas

1. **Olhe as fotos do posto** e descreva o que importa para o desenho:
   - a cor e o formato da cobertura;
   - onde e como o nome "AUTO POSTO SANTA FÉ" aparece na fachada (cor, fonte, posição);
   - onde fica o símbolo da Shell (na cobertura, no totem de preços, nas bombas);
   - como são o totem, as bombas, as ilhas e a loja de conveniência.
2. **Ajuste a cena** (`cena.html`) para parecer com o posto real:
   - coloque o nome "AUTO POSTO SANTA FÉ" na fachada do jeito que está nas fotos;
   - coloque o símbolo da Shell onde ele aparece no posto real. Também pode entrar um totem de preços, se houver um nas fotos.
3. **Gere o vídeo de novo** (instruções abaixo) e me mostre alguns quadros antes do MP4 final.
4. **Salve no repositório**, na mesma branch, com um commit claro.

### Regra importante sobre logos

**Não redesenhe à mão o símbolo da Shell nem o logo SF.** Use o arquivo oficial em PNG transparente ou SVG. Se ele não estiver no computador, me peça. Para usar o arquivo na cena, converta-o em data URI base64 e coloque-o dentro do SVG com `<image href="data:image/png;base64,..." x=".." y=".." width=".." height=".."/>`. Assim o vídeo é gerado sem depender de arquivo externo.

---

## Onde está o trabalho

- **Repositório no GitHub:** `dinamizemarketing-coder/Dinamize`
- **Branch:** `ccr-884f6d1f-hmt0pm`
- **Pasta:** `videos/clientes/auto-posto-santa-fe/`
  - `cena.html`: a animação inteira, desenhada em SVG e animada em JavaScript. Abra no navegador para assistir, pausar e arrastar a linha do tempo.
  - `render.js`: gera os quadros do vídeo com o Playwright.
  - `auto-posto-santa-fe-vinheta.mp4`: a versão atual.
- **Ficha do cliente:** `clientes/auto-posto-santa-fe.md`, com cores, fontes, tom de voz e cuidados. Leia antes de mexer.
- **Skill de animação:** `.claude/skills/rossark-motion-skill/`. Para instalar no computador: `npx skills@latest add rossark0/rossark-motion-skill`

Se o repositório ainda não estiver no computador:

```bash
git clone https://github.com/dinamizemarketing-coder/Dinamize.git
cd Dinamize
git checkout ccr-884f6d1f-hmt0pm
```

## Como a cena está hoje

**Duração:** 16 s, em 1080×1920 e 30 fps. Tudo é calculado a partir de um único relógio, pela função `render(t)`, com `t` em milissegundos.

| Tempo | O que acontece |
|---|---|
| 0–2,5 s | Noite. As luzes da cobertura acendem uma a uma, piscando como lâmpada de verdade, e o letreiro e a conveniência se iluminam. A bandeira tremula. |
| 2,5–5,9 s | Um carro prata entra já em movimento, freia e a frente abaixa e balança de volta ao parar na bomba. |
| 5,9–9,7 s | O bico vai da bomba até o carro e o visor conta os litros (42,30). |
| 9,7–11,8 s | O carro arranca, a frente sobe na aceleração e ele sai pela esquerda. |
| 11,8–16 s | Um painel vermelho sobe com "AUTO POSTO / SANTA FÉ", uma linha amarela e a assinatura "Primeiro posto da cidade · Aberto 24h" e "GO-060, Km 42 · Santa Bárbara de Goiás". |

**Onde mexer no `cena.html`:**
- A cobertura e o letreiro estão no bloco `<!-- Canopy -->`. A faixa vermelha fica em `x=20 y=246`, com 320 × 40, e o nome é o `<text class="sign">`.
- A loja de conveniência está no bloco `<!-- Convenience store behind -->`.
- A bomba está no bloco `<!-- Pump -->`.
- O painel final está em `#endPanel`, `#kicker`, `#title`, `#underline` e `#slogan`.
- Os tempos e os números ficam no topo do script, na seção `// ---- Tokens ----`.
- A área desenhada vai de 0 a 360 na horizontal e de 0 a 640 na vertical. O grupo `#cam` aplica um zoom leve, de 1,22 a 1,27.

## Identidade do posto

- **Cores:** vermelho Shell `#C8102E`, amarelo Shell `#FBCE07` e preto para contraste. O roxo do Shell Box só entra em posts do app.
- **Fonte:** Poppins ExtraBold Italic nos títulos e Poppins Regular nos textos de apoio.
- **Elementos:** faixas diagonais vermelhas e amarelas e o logo SF no rodapé.
- **Dados:** GO-060, Km 42, Santa Bárbara de Goiás. Aberto 24h. Primeiro posto da cidade, inaugurado em outubro de 2023. Instagram @santa_fe_posto.
- **Tom:** português do Brasil, simples. Sem clichês e sem travessão no meio das frases.

## Regras de animação

São da rossark-motion-skill. Mantenha-as ao mexer:

- **Nada teletransporta:** tudo passa de um valor a outro com curva.
- **Movimento calmo e pequeno**, sem quicar demais. É uma marca séria.
- **Um relógio só:** cada parte é uma função do tempo `t`.
- **Entradas:** o que entra em cena já entra em movimento, de fora da tela.
- **Opacidade** só para aparecer ou sumir.
- **Movimento reduzido:** a página mostra um quadro parado que funcione sozinho.

## Como gerar o vídeo

É preciso ter Node, o Playwright (com o Chromium) e o ffmpeg.

```bash
cd videos/clientes/auto-posto-santa-fe
npm i -D playwright && npx playwright install chromium
node render.js sheet 2000,7600,14500       # alguns quadros em PNG para conferir
node render.js video                        # 480 quadros em ./frames
ffmpeg -framerate 30 -i frames/%04d.png -vf format=yuv420p -c:v libx264 -preset slow -crf 18 -movflags +faststart auto-posto-santa-fe-vinheta.mp4
```

O `render.js` abre o Chromium em `/opt/pw-browsers/chromium`. Se esse caminho não existir, ele usa o Chromium do próprio Playwright.

## Quando terminar

- Confira se o nome e o símbolo da Shell aparecem nítidos no celular, em 1080×1920.
- Confira se o símbolo usado é o arquivo oficial, sem distorção e sem trocar as cores.
- Faça o commit e o push na branch `ccr-884f6d1f-hmt0pm`.
- Me mande o MP4 e diga o que mudou.
