"""Control de calidad antes de subir. Si algo falla, el video NO se sube.
Uso: python scripts/control_calidad.py trabajo/episodio.json trabajo/video.mp4 trabajo/video.tiempos.json
Revisa: duración mínima del formato, voces completas, audio presente y con volumen correcto, video sin cuadros negros largos.
"""
import json, re, subprocess, sys

MINIMO = {'normal': 45 * 60, 'maraton': 3 * 3600, 'maqueta': 60}  # el maratón se programa en 3 h 20 min


def ff(*args):
    return subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *args], capture_output=True, text=True).stderr


def main(ep_path, video, sync_path):
    ep = json.load(open(ep_path)); sync = json.load(open(sync_path)); fallas = []
    fmt = ep.get('formato', 'normal')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video],
                               capture_output=True, text=True).stdout.strip() or 0)
    print(f'Duración: {dur / 60:.1f} min (mínimo {MINIMO.get(fmt, 0) / 60:.0f} min)')
    if dur < MINIMO.get(fmt, 0): fallas.append(f'dura {dur / 60:.1f} min, menos que el mínimo del formato {fmt}')
    if sync.get('faltan'): fallas.append(f"faltan {len(sync['faltan'])} voces: {sync['faltan'][:8]}")
    if len(sync['tiempos']) != len(ep['preguntas']): fallas.append('no todas las preguntas están en el video')
    # volumen integrado (EBU R128) sobre los primeros 10 minutos
    out = ff('-t', '600', '-i', video, '-af', 'ebur128', '-f', 'null', '-')
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', out)
    if m:
        lufs = float(m[-1]); print(f'Volumen: {lufs} LUFS')
        if not -20 <= lufs <= -10: fallas.append(f'volumen fuera de rango ({lufs} LUFS)')
    else: fallas.append('no se pudo medir el audio')
    out = ff('-t', '600', '-i', video, '-vf', 'blackdetect=d=3:pix_th=0.05', '-an', '-f', 'null', '-')
    if 'black_start' in out: fallas.append('hay más de 3 s de pantalla negra')
    print('Fallas:', fallas or 'ninguna')
    sys.exit(1 if fallas else 0)


if __name__ == '__main__':
    main(*sys.argv[1:])
