#!/usr/bin/env python3
"""02_render.py - aplica a folga (3s antes / 2s depois), ancora nos silencios reais
e renderiza cada corte em 9:16 (1080x1920), frame-exato, sem legenda queimada.

  python3 02_render.py trabalho/video.mp4 cortes.tsv \
      --silencios trabalho/silencios.txt --saida saida

cortes.tsv (TAB ou ';'):  inicio  fim  titulo
Aceita 00:12:30 / 12:30 / 750.
"""
import argparse, os, re, subprocess, sys

ANTES, DEPOIS = 3.0, 2.0
JANELA = 2.5          # ate onde procurar um silencio melhor que a folga fixa


def seg(t):
    t = str(t).strip().replace(",", ".")
    if re.fullmatch(r"[\d.]+", t):
        return float(t)
    p = [float(x) for x in t.split(":")]
    while len(p) < 3:
        p.insert(0, 0.0)
    return p[0] * 3600 + p[1] * 60 + p[2]


def le_silencios(path):
    """-> lista de (inicio, fim) de cada silencio detectado."""
    if not path or not os.path.exists(path):
        return []
    sil, ini = [], None
    for ln in open(path, encoding="utf-8"):
        m = re.search(r"silence_(start|end):\s*([-\d.]+)", ln)
        if not m:
            continue
        if m.group(1) == "start":
            ini = float(m.group(2))
        elif ini is not None:
            sil.append((ini, float(m.group(2))))
            ini = None
    return sil


def ancora(t, sil, borda):
    """Cai no MEIO do silencio mais proximo; sem silencio util, usa a folga fixa.
    borda='ini' procura o silencio que termina perto de t (antes da fala);
    borda='fim' procura o que comeca perto de t (depois da fala)."""
    alvo = t - ANTES if borda == "ini" else t + DEPOIS
    melhor, dist = None, JANELA
    for a, b in sil:
        if borda == "ini" and a <= t and abs(b - t) <= JANELA:
            if abs(b - t) < dist:
                melhor, dist = (a + b) / 2, abs(b - t)
        if borda == "fim" and b >= t and abs(a - t) <= JANELA:
            if abs(a - t) < dist:
                melhor, dist = (a + b) / 2, abs(a - t)
    if melhor is None:
        return max(0.0, alvo)
    # nunca deixar o corte mais apertado que a fala marcada
    return max(0.0, min(melhor, t - 0.4)) if borda == "ini" else max(melhor, t + 0.4)


def slug(s, i):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-")[:48]
    return f"{i:02d}_{s or 'corte'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("cortes")
    ap.add_argument("--silencios")
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--crop-x", default="(iw-1080)/2",
                    help="posicao horizontal do crop 9:16 (padrao: centro)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    sil = le_silencios(a.silencios)
    os.makedirs(a.saida, exist_ok=True)
    linhas, tabela = [], []

    for ln in open(a.cortes, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        p = re.split(r"\t|;", ln)
        if len(p) < 2:
            continue
        linhas.append((seg(p[0]), seg(p[1]), (p[2] if len(p) > 2 else "").strip()))

    for i, (ini, fim, titulo) in enumerate(linhas, 1):
        s = ancora(ini, sil, "ini")
        e = ancora(fim, sil, "fim")
        nome = slug(titulo, i) + ".mp4"
        dest = os.path.join(a.saida, nome)
        vf = (f"fps=30,scale=-2:1920,"
              f"crop=w=1080:h=1920:x='{a.crop_x}':y=0")
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{s:.3f}", "-i", a.video,
               "-t", f"{e - s:.3f}", "-vf", vf,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", dest]
        print(f"[{i:02d}] {ini:8.2f}->{fim:8.2f}  =>  {s:8.2f}->{e:8.2f} "
              f"({e - s:5.1f}s)  {titulo}")
        if not a.dry_run:
            subprocess.run(cmd, check=True)
        tabela.append((nome, ini, fim, s, e, e - s, titulo))

    if a.dry_run:
        return

    with open(os.path.join(a.saida, "cortes.md"), "w", encoding="utf-8") as f:
        f.write("| Arquivo | Trecho original | Trecho renderizado | Duração | Tema |\n")
        f.write("|---|---|---|---|---|\n")
        hms = lambda t: f"{int(t//3600):02d}:{int(t%3600//60):02d}:{t%60:05.2f}"
        for nome, i0, f0, s, e, d, tit in tabela:
            f.write(f"| `{nome}` | {hms(i0)} → {hms(f0)} | {hms(s)} → {hms(e)} "
                    f"| {d:.1f}s | {tit} |\n")

    print("\n>> verificando")
    for nome, *_ , d, _t in tabela:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "csv=p=0", os.path.join(a.saida, nome)],
            capture_output=True, text=True).stdout.replace("\n", " ").strip()
        print(f"  {nome}: {out}  (esperado ~{d:.1f}s 1080 1920)")


if __name__ == "__main__":
    main()
