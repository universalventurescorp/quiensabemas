"""Genera las frases nuevas de un video con las 3 voces del canal (Qwen3-TTS, CPU).
Uso: python scripts/generar_voces.py contenido/maqueta_tv.json voces/maqueta [--modelo ...]
Retoma: salta las frases que ya existen.
"""
import argparse, json, os, sys, time
import soundfile as sf
import torch

VOCES = ["presentador", "copresentadora", "anunciador"]


def lineas(meta):
    out = {}
    for k, (voz, txt) in meta.get("extra_tts", {}).items():
        out[k] = (voz, txt)
    for q in meta["preguntas"]:
        n = q["n"]
        out[f"q{n:02d}_pregunta"] = ("presentador", q["tp"])
        out[f"q{n:02d}_respuesta"] = ("copresentadora", q["tr"])
        out[f"q{n:02d}_dato"] = ("copresentadora", q["td"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("contenido"); ap.add_argument("salida")
    ap.add_argument("--modelo", default=os.environ.get("QSM_TTS", "Qwen/Qwen3-TTS-12Hz-1.7B-Base"))
    ap.add_argument("--banco", default="banco")
    a = ap.parse_args()
    meta = json.load(open(a.contenido)); L = lineas(meta)
    os.makedirs(a.salida, exist_ok=True)
    pend = {k: v for k, v in L.items() if not os.path.exists(f"{a.salida}/{k}.wav")}
    print(f"{len(L)} frases, faltan {len(pend)}")
    if not pend:
        return
    ref_txt = json.load(open(f"{a.banco}/ref_textos.json"))
    torch.set_num_threads(os.cpu_count() or 4)
    from qwen_tts import Qwen3TTSModel
    model = Qwen3TTSModel.from_pretrained(a.modelo, device_map="cpu", dtype=torch.float32)
    prompts = {v: model.create_voice_clone_prompt(ref_audio=f"{a.banco}/ref_{v}.wav", ref_text=ref_txt[v]) for v in VOCES}
    t0 = time.time()
    for i, (k, (voz, txt)) in enumerate(pend.items(), 1):
        wavs, sr = model.generate_voice_clone(text=txt, language="Spanish", voice_clone_prompt=prompts[voz])
        sf.write(f"{a.salida}/{k}.wav", wavs[0], sr)
        print(f"[{i}/{len(pend)}] {k} {len(wavs[0])/sr:.1f}s · {(time.time()-t0)/60:.1f} min", flush=True)
    json.dump({k: {"voz": v, "texto": t} for k, (v, t) in L.items()}, open(f"{a.salida}/indice.json", "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
