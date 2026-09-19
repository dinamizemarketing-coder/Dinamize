#!/usr/bin/env python3
"""enquadramento.py - camada de enquadramento por falante (9:16).

  plano   VIDEO --de 754 --ate 812 --fala transcricao.txt -o plano.json
  render  VIDEO plano.json saida.mp4

Decide QUANDO vale mudar o foco (conservador: na duvida, mantem) e
ONDE cortar o 9:16, entregando poucos keyframes com pan suave.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, tempfile
import cv2, numpy as np

FPS_A = 6      # amostragem da analise
FPS_O = 30     # fps de saida
CROPW = 1080

def sh(c): subprocess.run(c, check=True, capture_output=True)

def dims(video):
    o = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height","-of","csv=p=0:s=x",video],
        capture_output=True, text=True, check=True).stdout.strip().split("x")
    w, h = int(o[0]), int(o[1])
    return w, h, int(round(w*1920/h/2))*2

# ---------- 1. rostos ----------
YUNET = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

def detector(w, h):
    """YuNet (da os landmarks da boca, pega rosto de perfil). Sem rede, cai no
    Haar que ja vem dentro do opencv - pior em perfil, mas nunca deixa a skill parada."""
    m = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yunet.onnx")
    if not os.path.exists(m) or os.path.getsize(m) < 100000:
        subprocess.run(["curl","-sLf","-m","90","-o",m,YUNET], capture_output=True)
    if os.path.exists(m) and os.path.getsize(m) > 100000:
        return "yunet", cv2.FaceDetectorYN.create(m, "", (w, h), 0.6)
    return "haar", cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")

def _boca(img, mx, my, r):
    h, w = img.shape[:2]
    x0, x1 = max(0,int(mx-r)), min(w,int(mx+r))
    y0, y1 = max(0,int(my-r*0.7)), min(h,int(my+r*0.7))
    if x1 <= x0+3 or y1 <= y0+3: return None
    return cv2.resize(cv2.cvtColor(img[y0:y1,x0:x1], cv2.COLOR_BGR2GRAY),(24,24)).astype(np.float32)

def detecta(video, t0, dur, tmp):
    sh(["ffmpeg","-y","-v","error","-ss",f"{t0}","-i",video,"-t",f"{dur}",
        "-vf",f"fps={FPS_A},scale=640:-2","-q:v","4",f"{tmp}/%05d.jpg"])
    arqs = sorted(os.listdir(tmp))
    h, w = cv2.imread(os.path.join(tmp, arqs[0])).shape[:2]
    tipo, det = detector(w, h)
    quadros = []
    for p in arqs:
        img = cv2.imread(os.path.join(tmp, p)); caras = []
        if tipo == "yunet":
            _, fs = det.detect(img)
            for r in (fs if fs is not None else []):
                x, y, fw, fh = r[:4]
                oD, oE, nz = (r[4], r[5]), (r[6], r[7]), (r[8], r[9])
                mx, my = (r[10]+r[12])/2, (r[11]+r[13])/2          # meio da boca
                olhos = abs(oD[0]-oE[0]) or 1e-6
                caras.append(dict(cx=(x+fw/2)/w, w=fw/w, score=float(r[14]),
                                  patch=_boca(img, mx, my, max(8, fw*0.24)),
                                  gaze=max(-1.0, min(1.0, (nz[0]-(oD[0]+oE[0])/2)/olhos))))
        else:
            g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            for x, y, fw, fh in det.detectMultiScale(g, 1.1, 6, minSize=(int(w*0.05),)*2):
                caras.append(dict(cx=(x+fw/2)/w, w=fw/w, score=1.0, gaze=0.0,
                                  patch=_boca(img, x+fw/2, y+fh*0.78, max(8, fw*0.24))))
        quadros.append(caras)
    return quadros

def rastreia(quadros):
    """Mesma pessoa mantem o mesmo id mesmo mudando de posicao."""
    tracks = []
    for i, caras in enumerate(quadros):
        usados = set()
        for c in sorted(caras, key=lambda c: -c["score"]):
            alvo, melhor = None, 1e9
            for t in tracks:
                if t["id"] in usados or i - t["ult"] > 12: continue
                d = abs(c["cx"]-t["cx"]) / max(0.04, (c["w"]+t["w"])/2)
                if d < 1.2 and d < melhor: alvo, melhor = t, d
            if alvo is None:
                alvo = dict(id=len(tracks), cx=c["cx"], w=c["w"], obs={}, ult=i, ativ={})
                tracks.append(alvo)
            alvo.update(cx=c["cx"], w=c["w"], ult=i); alvo["obs"][i] = c; usados.add(alvo["id"])
    return [t for t in tracks if len(t["obs"]) >= 5]

def atividade(tracks, n):
    """Movimento da boca = quem provavelmente esta falando."""
    for t in tracks:
        idx = sorted(t["obs"])
        for a, b in zip(idx, idx[1:]):
            pa, pb = t["obs"][a]["patch"], t["obs"][b]["patch"]
            if b-a <= 2 and pa is not None and pb is not None:
                t["ativ"][b] = float(np.abs(pb-pa).mean())
    for i in range(n):                      # tira movimento global (camera, luz)
        v = [t["ativ"][i] for t in tracks if i in t["ativ"]]
        if len(v) >= 2:
            m = float(np.median(v))*0.6
            for t in tracks:
                if i in t["ativ"]: t["ativ"][i] = max(0.0, t["ativ"][i]-m)
    return tracks

# ---------- 2. quem fala ----------
def le_fala(path, t0, t1):
    segs = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\s*\[?\s*([\d.]+)\s*(?:->|→|-)\s*([\d.]+)\s*\]?\s*(.*)", ln)
        if not m: continue
        a, b = float(m.group(1)), float(m.group(2))
        if b > t0 and a < t1 and b > a:
            segs.append(dict(a=max(a,t0)-t0, b=min(b,t1)-t0, txt=m.group(3).strip()))
    return segs

def atribui(segs, tracks, minativ=1.2, ambiguo=0.72):
    for s in segs:
        i0, i1 = int(s["a"]*FPS_A), int(math.ceil(s["b"]*FPS_A))
        pont = {}
        for t in tracks:
            v = [t["ativ"][i] for i in range(i0, i1+1) if i in t["ativ"]]
            vis = sum(1 for i in range(i0, i1+1) if i in t["obs"])
            if len(v) >= 2 and vis >= 0.4*(i1-i0+1):
                pont[t["id"]] = float(np.mean(sorted(v)[len(v)//4:]))   # ignora o quartil parado
        s["pont"] = {str(k): round(v,2) for k, v in pont.items()}
        ordem = sorted(pont.items(), key=lambda kv: -kv[1])
        if not ordem or ordem[0][1] < minativ:
            s["quem"] = None; s["motivo"] = "sem rosto confiavel"
        elif len(ordem) > 1 and ordem[1][1] > ambiguo*ordem[0][1]:
            s["quem"] = None; s["motivo"] = "vozes sobrepostas/ambiguo"
        else:
            s["quem"] = ordem[0][0]; s["motivo"] = "ok"
    return segs

# ---------- 3. decidir as trocas ----------
def limiar(trocas, t, segs):
    """Quanto de fala continua o novo falante precisa antes de merecer o foco."""
    lim = 2.5 + min(3.0, 1.2*sum(1 for tt, _ in trocas if t-tt <= 15))
    jan = [s for s in segs if s["quem"] is not None and t-8 <= s["a"] <= t]
    if len(jan) >= 3:
        media = sum(s["b"]-s["a"] for s in jan)/len(jan)
        if media < 2.5: lim += 1.5          # conversa rapida: resistir mais
        elif media > 6: lim -= 0.5
    return max(2.0, min(7.0, lim))

def decide(segs):
    trocas, alvo, t_troca, cand = [], None, -99.0, None
    for s in segs:
        q = s["quem"]
        if q is None or q == alvo: cand = None; continue
        if cand and cand["quem"] == q and s["a"]-cand["fim"] <= 1.2:
            cand["fim"] = s["b"]; cand["dur"] += s["b"]-s["a"]
        else:
            cand = dict(quem=q, ini=s["a"], fim=s["b"], dur=s["b"]-s["a"])
        if alvo is None and cand["dur"] >= 0.8:            # abertura do clipe
            alvo, t_troca = q, 0.0; trocas.append((0.0, q)); cand = None; continue
        lim = limiar(trocas, cand["ini"], segs)
        if cand["dur"] >= lim and cand["ini"]-t_troca >= max(3.0, lim*0.8):
            t = max(0.0, cand["ini"]-0.15)
            trocas.append((t, q)); alvo, t_troca, cand = q, t, None
    return trocas or [(0.0, None)]

# ---------- 4. onde cortar o quadro ----------
def keyframes(trocas, tracks, dur, W2):
    lim = lambda x: float(max(0, min(W2-CROPW, x)))
    byid = {t["id"]: t for t in tracks}
    bordas = [t for t, _ in trocas][1:] + [dur]
    kfs = []
    for k, (t0, quem) in enumerate(trocas):
        t1 = bordas[k]
        pts = []
        if quem in byid:
            for i, c in byid[quem]["obs"].items():
                ts = i/FPS_A
                if t0-0.3 <= ts <= t1:
                    pts.append((ts, c["cx"]*W2 + c["gaze"]*110))   # espaco na direcao do olhar
        if len(pts) < 3:
            kfs.append(dict(t=t0, x=lim((W2-CROPW)/2), ramp=0.0 if k == 0 else 0.7)); continue
        pts.sort()
        anc = float(np.median([x for _, x in pts[:max(3, len(pts)//5)]]))
        kfs.append(dict(t=t0, x=lim(anc-CROPW/2), ramp=0.0 if k == 0 else 0.7))
        desde = None
        for ts, x in pts:                     # so re-ancora se a deriva se sustentar
            if abs(x-anc) > 170:
                desde = ts if desde is None else desde
                if ts-desde >= 1.5:
                    anc = float(np.median([v for u, v in pts if ts-1.5 <= u <= ts]))
                    kfs.append(dict(t=round(desde,2), x=lim(anc-CROPW/2), ramp=1.2)); desde = None
            else: desde = None
    return sorted(kfs, key=lambda k: k["t"])

def expr(kfs):
    T = f"(n/{FPS_O})"
    e = f"{kfs[0]['x']:.0f}"
    for p, k in zip(kfs, kfs[1:]):
        r = max(0.05, k.get("ramp", 0.7)); d = k["x"]-p["x"]
        if abs(d) < 8: continue
        ramp = f"({p['x']:.0f}+({d:.0f})*({T}-{k['t']:.2f})/{r:.2f})"
        e = f"if(lt({T},{k['t']:.2f}),{e},if(lt({T},{k['t']+r:.2f}),{ramp},{k['x']:.0f}))"
    return e

# ---------- comandos ----------
def cmd_plano(a):
    dur = a.ate - a.de
    w, h, W2 = dims(a.video)
    tmp = tempfile.mkdtemp()
    try:
        quadros = detecta(a.video, a.de, dur, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tracks = atividade(rastreia(quadros), len(quadros))
    segs = atribui(le_fala(a.fala, a.de, a.ate), tracks) if a.fala else []
    trocas = decide(segs) if segs else [(0.0, None)]
    kfs = keyframes(trocas, tracks, dur, W2)
    plano = dict(video=a.video, de=a.de, ate=a.ate, dur=round(dur,2), W2=W2, crop_w=CROPW,
                 pessoas=len(tracks), trocas=[dict(t=round(t,2), pessoa=q) for t, q in trocas],
                 keyframes=kfs, expr=expr(kfs),
                 fala=[dict(a=round(s["a"],2), b=round(s["b"],2), quem=s["quem"],
                            motivo=s["motivo"], txt=s["txt"][:70]) for s in segs])
    json.dump(plano, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"pessoas={len(tracks)} trocas={len(trocas)} keyframes={len(kfs)} -> {a.out}")
    for t, q in trocas: print(f"  {t:7.2f}s  foco -> pessoa {q}")

def cmd_render(a):
    p = json.load(open(a.plano))
    # seek so no input: e frame-exato com re-encode E zera o contador de frames do
    # filtro, sem o que a expressao de crop rodaria adiantada (o pan sai na hora errada).
    vf = f"fps={FPS_O},scale=-2:1920,crop=w={p['crop_w']}:h=1920:x='{p['expr']}':y=0"
    sh(["ffmpeg","-y","-v","error","-ss",f"{p['de']}","-i",p["video"],"-t",f"{p['dur']}",
        "-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-movflags","+faststart",a.saida])
    print(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-show_entries","stream=width,height","-of","csv=p=0",a.saida],
        capture_output=True, text=True).stdout.strip())

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("plano"); p1.add_argument("video"); p1.add_argument("--de", type=float, required=True)
    p1.add_argument("--ate", type=float, required=True); p1.add_argument("--fala")
    p1.add_argument("-o", "--out", default="plano.json"); p1.set_defaults(f=cmd_plano)
    p2 = sub.add_parser("render"); p2.add_argument("video"); p2.add_argument("plano")
    p2.add_argument("saida"); p2.set_defaults(f=cmd_render)
    a = ap.parse_args(); a.f(a)
