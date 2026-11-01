"""Genera las frases de un episodio (o del banco de variantes) con las 3 voces del canal (Qwen3-TTS, CPU).
Uso:
  python scripts/generar_voces.py contenido/ep.json voces/ep [--parte 0 --partes 8] [--modelo ...]
  python scripts/generar_voces.py banco/variantes.json banco/var            (banco de variantes)
  python scripts/generar_voces.py contenido/ep.json voces/ep --listar      (solo cuenta lo que falta)
Retoma: salta las frases que ya existen. Con --parte/--partes se reparte el trabajo entre varias máquinas.
"""
import argparse, json, os, sys, time

VOCES = ["presentador", "copresentadora", "anunciador"]
UNID = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece",
        "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós",
        "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
DEC = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
CEN = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos"}


def palabras(n):
    """Número en letras (1–599), para que la voz diga «Pregunta ciento doce»."""
    if n == 100: return "cien"
    c, r = divmod(n, 100)
    out = [CEN[c]] if c else []
    if r:
        if r < 30: out.append(UNID[r])
        else:
            d, u = divmod(r, 10); out.append(DEC[d] + (f" y {UNID[u]}" if u else ""))
    return " ".join(out)


def lineas(meta):
    out = {}
    if "variantes" in meta:
        for k, (voz, textos) in meta["variantes"].items():
            for i, txt in enumerate(textos):
                out[f"{k}__{i}"] = (voz, txt)
        return out
    for k, (voz, txt) in meta.get("extra_tts", {}).items():
        out[k] = (voz, txt)
    for q in meta["preguntas"]:
        n = q["n"]
        out[f"q{n:02d}_pregunta"] = ("presentador", f"Pregunta {palabras(n)}. {q['tp']}")
        out[f"q{n:02d}_respuesta"] = ("copresentadora", q["tr"])
        out[f"q{n:02d}_dato"] = ("copresentadora", q["td"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("contenido"); ap.add_argument("salida")
    ap.add_argument("--modelo", default=os.environ.get("QSM_TTS", "Qwen/Qwen3-TTS-12Hz-1.7B-Base"))
    ap.add_argument("--banco", default="banco")
    ap.add_argument("--parte", type=int, default=0); ap.add_argument("--partes", type=int, default=1)
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    meta = json.load(open(a.contenido)); L = lineas(meta)
    os.makedirs(a.salida, exist_ok=True)
    json.dump({k: {"voz": v, "texto": t} for k, (v, t) in L.items()}, open(f"{a.salida}/indice.json", "w"),
              ensure_ascii=False, indent=1)
    claves = sorted(L)
    mias = [k for i, k in enumerate(claves) if i % a.partes == a.parte]
    pend = {k: L[k] for k in mias if not os.path.exists(f"{a.salida}/{k}.wav")}
    print(f"{len(L)} frases en total · parte {a.parte + 1}/{a.partes}: {len(mias)} · faltan {len(pend)}", flush=True)
    if a.listar or not pend:
        return
    import soundfile as sf
    import torch
    ref_txt = json.load(open(f"{a.banco}/ref_textos.json"))
    torch.set_num_threads(os.cpu_count() or 4)
    from qwen_tts import Qwen3TTSModel
    model = Qwen3TTSModel.from_pretrained(a.modelo, device_map="cpu", dtype=torch.float32)
    prompts = {v: model.create_voice_clone_prompt(ref_audio=f"{a.banco}/ref_{v}.wav", ref_text=ref_txt[v]) for v in VOCES}
    t0 = time.time()
    for i, (k, (voz, txt)) in enumerate(pend.items(), 1):
        for intento in range(2):
            try:
                wavs, sr = model.generate_voice_clone(text=txt, language="Spanish", voice_clone_prompt=prompts[voz])
                dur = len(wavs[0]) / sr
                # control: una frase no puede durar mucho más de lo razonable (alucinación del modelo)
                if dur > 4 + len(txt) / 6:
                    print(f"  {k}: {dur:.1f}s parece demasiado largo, reintento", flush=True); continue
                sf.write(f"{a.salida}/{k}.wav", wavs[0], sr); break
            except Exception as e:
                print(f"  {k}: error {e}", flush=True)
        print(f"[{i}/{len(pend)}] {k} · {(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
