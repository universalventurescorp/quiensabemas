# TRASPASO · ¿Quién Sabe Más? — 10-nov-2026, 15:20 Lima
Leer también: `contenido/navidad_plan.md` (lo que se produce ahora), `contenido/plan_crecimiento.md`, `contenido/ciudad_plan.md`.

## Qué se hizo el 10-nov (nueva cuenta de Claude)
- Nuevo formato «¿A o B? en la ciudad»: `pipeline/ciudad.py` (hereda de `pipeline/rapido.py`), guion de muestra `scripts/preparar_ciudad.py`, workflow `.github/workflows/ciudad.yml` (reusa fotos/voces de una corrida de `rapido.yml` con `run_fotos`; genera solo voces nuevas en `banco/ciudad`; `QSM_4K=1` escala a 4K; sube en privado; diagnóstico en rama `diag-ciudad`).
- Elementos: carretera elevada con subidas, caídas, curvas, túnel, puente roto, vuelta de cabeza, modo relámpago; puertas A/B (el que falla se estrella «¡PLAF!»); el equipo crece con cada correcta; vehículos sorpresa (patinetas, dragón, carrito con cohete, pato de hule); huevo de dragón que nace y crece (`assets/dragon/`); fondos y fachadas de Flow (`assets/ciudad/`), poses de Flow (`assets/corredores/`). Los nombres de las puertas se dibujan encima de todo (Luis lo pidió).
- Muestras privadas en YouTube: YTHCYXyMdDA, aLfrzZ5lzbI, XR-o2IG6laI (viejas, se pueden borrar) y **nE8FkNhO26o** (la buena, huevo de dragón, 4K). A Luis le gustó, sobre todo la vuelta de cabeza.
- Google Flow: Claude lo maneja en el navegador integrado de la app de escritorio de Luis (proyecto «¿Quién Sabe Más?», Nano Banana Pro, 9:16, x3, 0 créditos; personajes MAX y NOVA guardados como Characters). Para traer imágenes: fetch del src en la página + `a.download` → quedan como `.tmp` en `C:\Users\Lenovo\Downloads` (carpeta conectada) → `device_stage_files` → recortar verde. Abre ventanas «Guardar» en la PC de Luis: avisarle que las cancele.
- Tiempos medidos: muestra de 2,5 min en 4K tarda ~75 min de armado en una máquina → 1 h 20 necesita armado repartido (~20 máquinas).

## Pendiente inmediato (en orden)
1. Construir el armado repartido: `ciudad.py --desde/--hasta` (cuadros) por máquina + job final que une video, mezcla audio y sube. Ojo: `s._skyx` se acumula cuadro a cuadro → precalcularlo como arreglo para que no salte entre tramos.
2. Imágenes navideñas en Flow (lista en `navidad_plan.md`).
3. Escribir ~520 preguntas (quedan ~450 tras la revisión de fotos). Hay una parte A empezada: `contenido/ciudad/preguntas_a.txt` (162 fáciles, formato `pregunta ; correcta ; incorrecta ; foto ok ; foto mal ; respuesta`). Falta: partes B y C (medias/difíciles) + 30 % navideñas + script que arme el JSON (como `scripts/escribir_rapido001.py`) y revisión contra `banco/preguntas.jsonl`.
4. Generalizar `ciudad.py` a 9 zonas (fondo, fachadas, vehículo y eventos por zona) y a más etapas del dragón.
5. Producir el episodio, subir en privado, Luis revisa.

## Luis
Una sola propuesta decidida; lenguaje simple; respuestas breves; todo gratis; no construir sin su autorización (ya autorizó el episodio de Navidad); honestidad. Meta: 300K suscriptores con 2 videos (se le dijo que es muy difícil; el plan busca maximizar la probabilidad).
