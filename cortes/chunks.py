"""Blocos CONTIGUOS de ate 28s, comecando e terminando no meio de um silencio.
Contiguo importa: mantem o timestamp exato. So corta em silencio >= 1.0s, e
empacota ate perto de 28s para nao desperdicar a janela de 30s do Whisper."""
import json, re
MAX, MINSIL = 28.0, 1.0
DUR = 4870.87
sil, ini = [], None
for ln in open("silencios.txt"):
    m = re.search(r"silence_(start|end): ([-\d.]+)", ln)
    if not m: continue
    if m.group(1) == "start": ini = float(m.group(2))
    elif ini is not None: sil.append((ini, float(m.group(2)))); ini = None

# pontos de corte candidatos: meio de cada silencio longo o bastante
pontos = [0.0] + [round((a+b)/2, 3) for a, b in sil if b-a >= MINSIL] + [DUR]
pontos = sorted(set(pontos))

blocos, ini_b = [], pontos[0]
for p in pontos[1:]:
    if p - ini_b >= MAX:
        # trecho sem silencio utilizavel: fatia no seco
        while p - ini_b > MAX:
            blocos.append((round(ini_b,3), round(ini_b+MAX,3))); ini_b += MAX
        blocos.append((round(ini_b,3), round(p,3))); ini_b = p
    elif pontos.index(p) == len(pontos)-1 or p - ini_b >= MAX*0.75:
        blocos.append((round(ini_b,3), round(p,3))); ini_b = p
blocos = [(a,b) for a,b in blocos if b-a > 0.5]
json.dump(blocos, open("blocos.json","w"))
d = [b-a for a,b in blocos]
print(f"{len(blocos)} blocos | media {sum(d)/len(d):.1f}s | min {min(d):.1f}s | max {max(d):.1f}s")
print(f"cobertura: {sum(d)/60:.1f} min de {DUR/60:.1f} min")
