import json, subprocess, tempfile, os, shutil, numpy as np, cv2
cortes = json.load(open("cortes.json"))
det = cv2.FaceDetectorYN.create("yunet.onnx", "", (640, 360), 0.65)
W2 = 3414           # largura apos scale=-2:1920
print(f"{'#':>2} {'trecho':>17}  rostos (x relativo, tamanho)            crop_x sugerido")
plano = []
for i, c in enumerate(cortes, 1):
    tmp = tempfile.mkdtemp()
    subprocess.run(["ffmpeg","-y","-v","error","-ss",f"{c['ini']}","-i","video.mp4",
                    "-t",f"{c['fim']-c['ini']}","-vf","fps=1/4,scale=640:-2","-q:v","3",
                    f"{tmp}/%03d.jpg"], check=True)
    xs = []
    for p in sorted(os.listdir(tmp)):
        img = cv2.imread(os.path.join(tmp, p)); h, w = img.shape[:2]
        det.setInputSize((w, h))
        _, fs = det.detect(img)
        for r in (fs if fs is not None else []):
            x, y, fw, fh = r[:4]
            xs.append(((x+fw/2)/w, fw/w, float(r[14])))
    shutil.rmtree(tmp, ignore_errors=True)
    if not xs:
        print(f"{i:2d} {c['ini']:8.1f}-{c['fim']:7.1f}  *** nenhum rosto ***")
        plano.append(None); continue
    xs.sort()
    # agrupa em pessoas por proximidade horizontal
    grupos, atual = [], [xs[0]]
    for v in xs[1:]:
        if v[0] - atual[-1][0] < 0.08: atual.append(v)
        else: grupos.append(atual); atual = [v]
    grupos.append(atual)
    grupos = [g for g in grupos if len(g) >= 2]
    desc = "  ".join(f"x={np.median([v[0] for v in g]):.3f} n={len(g)} tam={np.median([v[1] for v in g]):.3f}"
                     for g in grupos)
    # Guga = o da esquerda na entrevista sentada; no corte 01 (em pe) ele esta a direita
    alvo = grupos[-1] if i == 1 else grupos[0]
    cx = float(np.median([v[0] for v in alvo])) * W2
    crop = int(max(0, min(W2-1080, cx - 540)))
    plano.append(crop)
    print(f"{i:2d} {c['ini']:8.1f}-{c['fim']:7.1f}  {desc:<52} {crop}")
json.dump(plano, open("cropx.json","w"))
