import sys, time, json, wave, re, numpy as np, sherpa_onnx
wid, nw = int(sys.argv[1]), int(sys.argv[2])
blocos = json.load(open("blocos.json"))
meus = [(i, a, b) for i, (a, b) in enumerate(blocos) if i % nw == wid]
r = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder="sherpa-onnx-whisper-small/small-encoder.int8.onnx",
    decoder="sherpa-onnx-whisper-small/small-decoder.int8.onnx",
    tokens="sherpa-onnx-whisper-small/small-tokens.txt",
    language="pt", task="transcribe", num_threads=1)
w = wave.open("audio.wav"); sr = w.getframerate()
out = open(f"parte_{wid}.jsonl", "w", encoding="utf-8")
t0 = time.time()
for k, (i, a, b) in enumerate(meus):
    w.setpos(int(a*sr))
    x = np.frombuffer(w.readframes(int((b-a)*sr)), dtype=np.int16).astype(np.float32)/32768
    s = r.create_stream(); s.accept_waveform(sr, x); r.decode_stream(s)
    ts = list(getattr(s.result, "timestamps", []) or [])
    out.write(json.dumps(dict(i=i, a=a, b=b, txt=s.result.text.strip(),
                              ts=ts[:2000]), ensure_ascii=False) + "\n")
    out.flush()
    if k % 5 == 0:
        print(f"w{wid}: {k+1}/{len(meus)} blocos | {(time.time()-t0)/60:.1f} min", flush=True)
print(f"w{wid}: FIM {len(meus)} blocos em {(time.time()-t0)/60:.1f} min", flush=True)
