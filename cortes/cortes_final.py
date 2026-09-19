import re, json
sil, ini = [], None
for ln in open("silencios.txt"):
    m = re.search(r"silence_(start|end): ([-\d.]+)", ln)
    if not m: continue
    if m.group(1) == "start": ini = float(m.group(2))
    elif ini is not None: sil.append((ini, float(m.group(2)))); ini = None

CORTES = [
 (1146.15, 1230.84, "Vendedor de carro e picareta"),
 (2162.03, 2244.88, "Aos 14 anos eu conheci a cocaina"),
 (2244.88, 2316.28, "O fundo do poco"),
 (2316.28, 2368.07, "Eu nao conseguia nem sonhar"),
 (2373.14, 2421.49, "Preciso te apresentar Jesus"),
 (2511.30, 2559.34, "Nunca mais usei droga"),
 (2763.88, 2842.98, "O login emprestado"),
 (2926.74, 3005.95, "Dois mil numa semana"),
 (3227.53, 3293.86, "19 carros em 3 dias"),
 (3308.80, 3364.28, "Jogando dinheiro pro alto"),
 (4126.27, 4203.95, "A Toyota esta derretendo"),
 (4556.77, 4608.44, "A avo de 70 anos no TikTok"),
]
def onde(t):
    for a, b in sil:
        if a <= t <= b: return (a, b)
    return None

ok, linhas = True, []
print(f"{'#':>2} {'trecho':>19} {'dur':>6}  fronteiras")
for i,(a,b,tit) in enumerate(CORTES,1):
    sa, sb = onde(a), onde(b)
    if not sa or not sb:
        ok = False
        print(f"{i:2d}  *** FORA DE SILENCIO: ini={'ok' if sa else 'NAO'} fim={'ok' if sb else 'NAO'}")
        continue
    # folga: ate 3s antes / 2s depois, limitada pela pausa real
    ini_f = max(sa[0], sa[1] - 3.0)
    fim_f = min(sb[1], sb[0] + 2.0)
    linhas.append((ini_f, fim_f, tit, a, b, sa[1]-ini_f, fim_f-sb[0]))
    print(f"{i:2d} {a:8.2f}->{b:8.2f} {b-a:5.1f}s  "
          f"render {ini_f:8.2f}->{fim_f:8.2f} ({fim_f-ini_f:5.1f}s)  "
          f"folga {sa[1]-ini_f:.2f}s / {fim_f-sb[0]:.2f}s")
if ok:
    with open("cortes.tsv","w",encoding="utf-8") as f:
        f.write("# inicio\tfim\ttitulo\n")
        for ini_f, fim_f, tit, *_ in linhas:
            f.write(f"{ini_f:.3f}\t{fim_f:.3f}\t{tit}\n")
    json.dump([dict(ini=l[0], fim=l[1], tit=l[2], fala_ini=l[3], fala_fim=l[4],
                    folga_ini=l[5], folga_fim=l[6]) for l in linhas],
              open("cortes.json","w"), ensure_ascii=False, indent=1)
    print(f"\ncortes.tsv escrito: {len(linhas)} cortes")
