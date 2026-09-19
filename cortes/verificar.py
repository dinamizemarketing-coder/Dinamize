import re, json
sil, ini = [], None
for ln in open("silencios.txt"):
    m = re.search(r"silence_(start|end): ([-\d.]+)", ln)
    if not m: continue
    if m.group(1) == "start": ini = float(m.group(2))
    elif ini is not None: sil.append((ini, float(m.group(2)))); ini = None

CORTES = [
 (2162.03, 2244.88, "Aos 14 anos eu conheci a cocaina"),
 (2244.88, 2316.28, "O fundo do poco"),
 (2316.28, 2372.28, "Eu nao conseguia nem sonhar"),
 (2373.14, 2421.49, "Preciso te apresentar Jesus"),
 (2511.30, 2564.90, "Nunca mais usei droga"),
 (2780.01, 2842.98, "O login emprestado"),
 (2926.74, 2983.99, "Dois mil numa semana"),
 (3227.53, 3293.86, "19 carros em 3 dias"),
 (3317.89, 3377.51, "Jogando dinheiro pro alto"),
 (1138.27, 1194.27, "Vendedor de carro e picareta"),
 (4150.57, 4203.95, "A Toyota esta derretendo"),
 (4556.77, 4615.00, "A avo de 70 anos no TikTok"),
]
def onde(t):
    for a, b in sil:
        if a <= t <= b: return (a, b)
    return None
print(f"{'#':>2} {'ponto':>9}  {'dentro de silencio?':<22} folga possivel")
for i,(a,b,tit) in enumerate(CORTES,1):
    for rot, t, lim in (("ini", a, 3.0), ("fim", b, 2.0)):
        s = onde(t)
        if s: 
            folga = (t - s[0]) if rot=="fim" else (s[1] - t)
            dur = s[1]-s[0]
            print(f"{i:2d} {rot} {t:9.2f}  SIM  [{s[0]:.2f}-{s[1]:.2f}] {dur:.2f}s   "
                  f"max {min(lim, dur):.2f}s")
        else:
            print(f"{i:2d} {rot} {t:9.2f}  *** NAO — corte no seco ***")
