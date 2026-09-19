#!/usr/bin/env python3
"""03_selecionar.py - escolhe os melhores momentos a partir da transcricao.

  python3 03_selecionar.py trabalho/transcricao.txt -n 12 -o cortes.tsv

Monta janelas de 30-90s que comecam num gancho e terminam numa ideia
concluida, pontua cada uma, descarta as redundantes e devolve as N melhores
em ordem cronologica. Gera tambem candidatos.md com o ranking completo, para
trocar um corte por outro sem reprocessar nada.
"""
import argparse, re, sys, unicodedata
from collections import Counter

MIN_DUR, MAX_DUR, IDEAL = 30.0, 90.0, 55.0

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

# --- lexicos: o que costuma segurar o espectador -------------------------
# Listas em vez de regex cruas: expressoes com espaco ("de rir") continuam
# valendo, coisa que o re.X silenciosamente destruiria.
GANCHO = ["o que ninguem", "ninguem te conta", "a verdade e", "olha so",
 "presta atencao", "vou te contar", "voce sabia", "sabe por que", "por que e que",
 "teve uma vez", "um dia eu", "quando eu", "aconteceu", "o segredo", "a real e",
 "deixa eu te", "pensa comigo", "imagina"]
EMOCAO = ["incrivel", "absurdo", "surreal", "impressionante", "chocante",
 "inacreditavel", "assustador", "emocionante", "chorei", "arrepiei", "apaixonado",
 "medo", "coragem", "sonho", "fracasso", "perdi", "ganhei", "quebrei", "virada",
 "mudou minha vida", "nunca mais", "jamais", "pior", "melhor", "maior", "dificil",
 "desesperado", "orgulho", "vergonha"]
POLEMICA = ["discordo", "polemico", "verdade seja dita", "todo mundo erra",
 "o problema e", "ninguem fala", "tabu", "odeio", "detesto", "nao aguento",
 "critica", "briga", "confesso", "admito", "errei"]
HUMOR = ["de rir", "morri de", "que loucura", "pelo amor", "(risos)", "(riso)"]
FECHO = ["entao e isso", "no final das contas", "resumindo", "a licao",
 "por isso que", "e foi assim", "deu certo", "valeu a pena", "aprendi que"]

def termos(lista):
    """Casa cada expressao com limite de palavra nas duas pontas."""
    return re.compile("|".join(r"\b" + re.escape(t) + r"\b" for t in lista), re.I)

GANCHO, EMOCAO, POLEMICA = termos(GANCHO), termos(EMOCAO), termos(POLEMICA)
HUMOR, FECHO = termos(HUMOR), termos(FECHO)
RISADA = re.compile(r"kkk+|haha+|rsrs+|\(risos?\)", re.I)
DADO = re.compile(r"r\$ ?\d|\d+ ?%|\b\d{2,}\b|\bmil\b|\bmilh(ao|oes)\b|\bbilhao\b", re.I)
FRACO = re.compile(r"^(e|ai|entao|tipo|assim|ne|ta|sei la|enfim|hum|ah|eh)\b", re.I)

PESOS = dict(gancho=3.0, emocao=2.2, polemica=2.4, humor=2.0, dado=1.6,
             pergunta=1.8, fecho=1.5)

STOP = set("""a o e de da do que em um uma os as para com nao se na no por mais
 as dos das ao aos eu voce ele ela nos eles isso isto aquilo meu sua seu minha
 mas ja quando muito tem ter sou era foi vai vou esta estao como ou tambem so
 la ca ai entao tipo assim ne ta cara gente coisa fazer feito bem ser esse essa
 aqui agora sempre nunca cada todo toda tudo nada pra pro""".split())

def le(path):
    segs = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\s*\[?\s*([\d.]+)\s*(?:->|→|-)\s*([\d.]+)\s*\]?\s*(.*)", ln)
        if m and float(m.group(2)) > float(m.group(1)):
            txt = m.group(3).strip()
            if txt:
                segs.append(dict(a=float(m.group(1)), b=float(m.group(2)), txt=txt))
    return segs

def pontua(seg):
    t = norm(seg["txt"])
    p, tags = 0.0, []
    for nome, padrao in (("gancho", GANCHO), ("emocao", EMOCAO),
                         ("polemica", POLEMICA), ("humor", HUMOR), ("dado", DADO)):
        n = len(padrao.findall(t))
        if nome == "humor":
            n += len(RISADA.findall(seg["txt"]))
        if n:
            p += PESOS[nome] * min(n, 2); tags.append(nome)
    if "?" in seg["txt"]:
        p += PESOS["pergunta"]; tags.append("pergunta")
    if FECHO.search(t):
        p += PESOS["fecho"]; tags.append("fecho")
    dur = seg["b"] - seg["a"]
    dens = len(t.split()) / dur if dur > 0 else 0
    p += max(-1.0, min(1.0, (dens - 2.0)))        # fala arrastada perde ponto
    if FRACO.match(t) and len(t.split()) < 6:
        p -= 1.0                                   # muleta solta, sem conteudo
    seg["p"], seg["tags"] = p, tags
    return seg

fecha_frase = lambda s: s["txt"].rstrip().endswith((".", "!", "?", "...", "…"))

def janelas(segs):
    """Toda janela comeca depois de uma frase fechada e termina fechando outra."""
    out = []
    for i, s in enumerate(segs):
        if i > 0 and not fecha_frase(segs[i - 1]):
            continue                               # comecaria no meio da frase
        for j in range(i, len(segs)):
            dur = segs[j]["b"] - s["a"]
            if dur < MIN_DUR:
                continue
            if dur > MAX_DUR:
                break
            if not fecha_frase(segs[j]):
                continue
            bloco = segs[i:j + 1]
            # abre com gancho de verdade? sem isso o clipe comeca sem motivo
            if not any(x["tags"] for x in bloco[:2]):
                continue
            base = sum(x["p"] for x in bloco)
            # o gancho tem que estar no comeco, nao perdido no meio
            abre = max((x["p"] for x in bloco[:2]), default=0)
            forma = 1.0 - abs(dur - IDEAL) / 90.0   # perto do ideal vale mais
            nota = base / len(bloco) * 2.2 + abre * 0.9 + forma * 2.0
            if FECHO.search(norm(bloco[-1]["txt"])):
                nota += 1.0
            out.append(dict(a=s["a"], b=segs[j]["b"], dur=dur, nota=nota,
                            segs=bloco,
                            tags=sorted({t for x in bloco for t in x["tags"]})))
    return out

def sacola(j):
    return Counter(w for x in j["segs"] for w in norm(x["txt"]).split()
                   if w not in STOP and len(w) > 3)

def parecido(a, b, lim=0.42):
    ca, cb = a["_sac"], b["_sac"]
    if not ca or not cb:
        return False
    inter = sum((ca & cb).values())
    return inter / min(sum(ca.values()), sum(cb.values())) > lim

def titulo(j):
    c = sacola(j)
    top = [w for w, _ in c.most_common(4)]
    frase = j["segs"][0]["txt"][:60].strip()
    return (frase.rstrip(".,;: ") or " ".join(top)) if frase else " ".join(top)

def hms(t):
    return f"{int(t//3600):02d}:{int(t%3600//60):02d}:{int(t%60):02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcricao")
    ap.add_argument("-n", type=int, default=12)
    ap.add_argument("-o", "--out", default="cortes.tsv")
    ap.add_argument("--candidatos", default="candidatos.md")
    ap.add_argument("--nota-min", type=float, default=6.0,
                    help="nota minima para um trecho ser considerado bom")
    ap.add_argument("--folga", type=float, default=4.0,
                    help="distancia minima entre dois cortes, em segundos")
    a = ap.parse_args()

    segs = [pontua(s) for s in le(a.transcricao)]
    if not segs:
        sys.exit("transcricao vazia ou em formato nao reconhecido")
    cands = sorted(janelas(segs), key=lambda j: -j["nota"])
    if not cands:
        sys.exit("nenhuma janela de 30-90s fechando frase; revise a transcricao")
    for j in cands:
        j["_sac"] = sacola(j)

    esc = []
    for j in cands:
        if len(esc) >= a.n:
            break
        if any(j["a"] < e["b"] + a.folga and e["a"] < j["b"] + a.folga for e in esc):
            continue                                # sobrepoe / cola num ja escolhido
        if j["nota"] < a.nota_min:
            break                                   # ranking desce: daqui pra baixo nao presta
        if any(parecido(j, e) for e in esc):
            continue                                # mesmo assunto, outro trecho
        esc.append(j)
    esc.sort(key=lambda j: j["a"])

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# inicio\tfim\ttitulo\n")
        for j in esc:
            f.write(f"{j['a']:.2f}\t{j['b']:.2f}\t{titulo(j)}\n")

    with open(a.candidatos, "w", encoding="utf-8") as f:
        f.write(f"# Candidatos ({len(cands)} janelas) — os {len(esc)} escolhidos "
                "estao marcados\n\n| # | Trecho | Dur | Nota | Sinais | Abertura |\n"
                "|---|---|---|---|---|---|\n")
        marc = {(round(j["a"], 2), round(j["b"], 2)) for j in esc}
        for k, j in enumerate(cands[:80], 1):
            m = "**✓**" if (round(j["a"], 2), round(j["b"], 2)) in marc else str(k)
            ab = j["segs"][0]["txt"][:70].replace("|", "/")
            f.write(f"| {m} | {hms(j['a'])} → {hms(j['b'])} | {j['dur']:.0f}s "
                    f"| {j['nota']:.2f} | {', '.join(j['tags']) or '—'} | {ab} |\n")

    print(f"{len(cands)} janelas avaliadas, {len(esc)} cortes -> {a.out}")
    for i, j in enumerate(esc, 1):
        print(f"[{i:02d}] {hms(j['a'])} → {hms(j['b'])} ({j['dur']:4.0f}s) "
              f"nota {j['nota']:5.2f}  {', '.join(j['tags']) or '—'}")
    if len(esc) < a.n:
        print(f"\naviso: so {len(esc)} momentos distintos passaram nos criterios "
              f"(pedido: {a.n}).\n  Qualidade vale mais que o numero — confira "
              f"{a.candidatos} antes de forcar.\n  Para afrouxar: --nota-min "
              f"{max(0.0, a.nota_min - 2):.0f} (piso de nota) ou aumente o limite "
              f"de semelhanca em parecido().")

if __name__ == "__main__":
    main()
