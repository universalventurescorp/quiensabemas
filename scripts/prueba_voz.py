"""Prueba de voz en CPU (máquinas gratis de GitHub, sin GPU, sin Kaggle).
Clona las 3 voces del canal desde banco/ref_*.wav con Qwen3-TTS y mide cuánto tarda.
Uso: python scripts/prueba_voz.py --modelo Qwen/Qwen3-TTS-12Hz-1.7B-Base --salida pruebas/voz/17b
"""
import argparse, json, os, time
import soundfile as sf
import torch

FRASES = [
    ("presentador", "¿Cuál es el océano más grande del mundo? ¿Atlántico, Índico, Ártico o Pacífico?"),
    ("copresentadora", "¡El océano Pacífico! Es tan grande, que todos los continentes juntos cabrían dentro de él."),
    ("anunciador", "¡Hoy jugamos: Cultura general, Perú y el mundo!"),
    ("presentador", "¿Qué lago comparten el Perú y Bolivia? ¿Titicaca, Junín, Parinacochas o Maracaibo?"),
]
VOCES = ["presentador", "copresentadora", "anunciador"]


def transcribir(banco, cache):
    if os.path.exists(cache):
        return json.load(open(cache))
    from transformers import pipeline
    asr = pipeline("automatic-speech-recognition", model="openai/whisper-small", device="cpu")
    out = {}
    for v in VOCES:
        r = asr(f"{banco}/ref_{v}.wav", generate_kwargs={"language": "spanish", "task": "transcribe"},
                return_timestamps=True)
        out[v] = r["text"].strip()
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(out, open(cache, "w"), ensure_ascii=False, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    ap.add_argument("--banco", default="banco")
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    torch.set_num_threads(os.cpu_count() or 4)
    rep = {"modelo": a.modelo, "cpus": os.cpu_count()}
    t = time.time()
    ref_txt = transcribir(a.banco, "banco/ref_textos.json")
    rep["transcripcion_s"] = round(time.time() - t, 1)
    rep["ref_textos"] = ref_txt

    from qwen_tts import Qwen3TTSModel
    t = time.time()
    model = Qwen3TTSModel.from_pretrained(a.modelo, device_map="cpu", dtype=torch.float32)
    rep["carga_s"] = round(time.time() - t, 1)
    prompts = {v: model.create_voice_clone_prompt(ref_audio=f"{a.banco}/ref_{v}.wav", ref_text=ref_txt[v])
               for v in VOCES}
    rep["frases"] = []
    for i, (v, txt) in enumerate(FRASES, 1):
        t = time.time()
        wavs, sr = model.generate_voice_clone(text=txt, language="Spanish", voice_clone_prompt=prompts[v])
        dt = time.time() - t
        dur = len(wavs[0]) / sr
        sf.write(f"{a.salida}/{i:02d}_{v}.wav", wavs[0], sr)
        rep["frases"].append({"voz": v, "texto": txt, "audio_s": round(dur, 1), "tarda_s": round(dt, 1),
                              "veces_tiempo_real": round(dt / max(dur, 0.1), 1)})
        print(rep["frases"][-1], flush=True)
    json.dump(rep, open(f"{a.salida}/informe.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
