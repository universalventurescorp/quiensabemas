# TRASPASO · ¿Quién Sabe Más? — 10-nov-2026, 15:20 Lima
Leer también: `contenido/navidad_plan.md` (lo que se produce ahora), `contenido/plan_crecimiento.md`, `contenido/ciudad_plan.md`.

## Qué se hizo el 10-nov (nueva cuenta de Claude)
- Nuevo formato «¿A o B? en la ciudad»: `pipeline/ciudad.py` (hereda de `pipeline/rapido.py`), guion de muestra `scripts/preparar_ciudad.py`, workflow `.github/workflows/ciudad.yml` (reusa fotos/voces de una corrida de `rapido.yml` con `run_fotos`; genera solo voces nuevas en `banco/ciudad`; `QSM_4K=1` escala a 4K; sube en privado; diagnóstico en rama `diag-ciudad`).
- Elementos: carretera elevada con subidas, caídas, curvas, túnel, puente roto, vuelta de cabeza, modo relámpago; puertas A/B (el que falla se estrella «¡PLAF!»); el equipo crece con cada correcta; vehículos sorpresa (patinetas, dragón, carrito con cohete, pato de hule); huevo de dragón que nace y crece (`assets/dragon/`); fondos y fachadas de Flow (`assets/ciudad/`), poses de Flow (`assets/corredores/`). Los nombres de las puertas se dibujan encima de todo (Luis lo pidió).
- Muestras privadas en YouTube: YTHCYXyMdDA, aLfrzZ5lzbI, XR-o2IG6laI (viejas, se pueden borrar) y **nE8FkNhO26o** (la buena, huevo de dragón, 4K). A Luis le gustó, sobre todo la vuelta de cabeza.
- Google Flow: Claude lo maneja en el navegador integrado de la app de escritorio de Luis (proyecto «¿Quién Sabe Más?», Nano Banana Pro, 9:16, x3, 0 créditos; personajes MAX y NOVA guardados como Characters). Para traer imágenes: fetch del src en la página + `a.download` → quedan como `.tmp` en `C:\Users\Lenovo\Downloads` (carpeta conectada) → `device_stage_files` → recortar verde. Abre ventanas «Guardar» en la PC de Luis: avisarle que las cancele.
- Tiempos medidos: muestra de 2,5 min en 4K tarda ~75 min de armado en una máquina → 1 h 20 necesita armado repartido (~20 máquinas).

## Avance episodio de Navidad (10-nov, tarde)
- Luis autorizó producir (fecha objetivo: revisión en privado ~sáb 14-nov). Imágenes de Flow ANTES que lo demás (necesitan su PC prendida).
- `assets/navidad/`: huevo-regalo, nace (bebé con gorro), bebe_vuela, joven (bufanda), adulto (arnés con cascabeles), trineo (de espaldas) y trineo_lado. Recortados del verde.
- Flow: al mandar ~8 prompts seguidos salta «usage limit»; mandar de a 2-3 y esperar. Luis tiene otra cuenta de Google de respaldo para Flow.
- Ojo descargas: los `.tmp` desaparecen cuando Luis cancela «Guardar» → hacer `device_stage_files` justo después de descargar. Tamaño en bytes identifica cada imagen.
- Hechos (10-nov 16:40): `assets/navidad/fondos/z1..z9` (avenida, fábrica, bosque, lago, dulces, polo, montaña, tejados, cielo; 1376x768), `regalo_a.png` (rosado) y `regalo_b.png` (celeste), `max_gorro.png` (Flow) y `nova_gorro.png` (nova1 original + gorro/bufanda trasplantados por código, porque Flow cambiaba su ropa).
- Flow: Nano Banana Pro se agota rápido; **Nano Banana 2.1** (0 créditos) siguió funcionando en la cuenta principal. Con referencia de Character el botón enviar se ignora si hay otra generación en curso → enviar de a uno y limpiar la caja (ctrl+a, Delete) antes de escribir, si no se juntan prompts. Cuenta de respaldo abierta en pestaña `flow.google.com/u/1`.
- Faltan en Flow (opcionales): reno gigante, patines, trineo de madera, fachadas navideñas 9:16, 3 miniaturas.
- Música: `assets/musica_navidad.enc` (tar de `cama/*.ogg` 13 instrumentales con prefijo rapida_/jazz_/calma_/accion_/epica_ y `especial/` cierre_auld_lang_syne + final_we_wish_voz (CON VOZ: solo en el final sin diálogo)). Se descifra igual que musica.enc pero con el secret **MUSICA_NAVIDAD_CLAVE** (Luis debe crearlo). Excluidas: versiones con voz y I Have a Little Dreidel (Janucá).

- Idea de Luis (10-nov 16:36): animales «súper tiernos vestidos de Navidad». Decidido: el EQUIPO que se une al acertar (y el desfile final) usa ~40 animales de Flow con gorro/bufanda/suéter navideño, en verde 9:16, en `assets/navidad/animales/<nombre>.png`; en las PREGUNTAS se quedan las fotos reales (para que se puedan responder). Generar de a 2-3 con Nano Banana 2.1.
- Preguntas escritas: `contenido/ciudad/preguntas_a.txt` (162), `preguntas_b.txt` (~107), `preguntas_c.txt` (~77, con `## nivel`), `preguntas_navidad.txt` (~92, con `## nivel`). Faltan ~80 más (≈45 navideñas) + script que arme el JSON.
- Armado repartido HECHO en `pipeline/ciudad.py` (`--tramo i --tramos N`, `--solo-audio`; `_skyx` precalculado con `skyx_de(k)`) y `.github/workflows/navidad.yml` (preparar → voces ×16 → render ×N + audio → unir → subir privado → rama diag-navidad). Falta probarlo en Actions.

- 10-nov 16:50 (límite de uso de Luis al 91 %, se corta la sesión): Luis aclaró que la idea son animales navideños **a los lados de la carretera** (público que saluda). Hechos 54 PNG en `assets/navidad/publico/` (`<zona><n>_<animal>.png`: polar, andes, bosque, ciudad, lago, dulces, artico, africa). En Flow (cuenta principal, proyecto ¿Quién Sabe Más?, 1:1 x2, Nano Banana 2.1) quedó generado SIN descargar el lote «selva» (perezoso, jaguar, tucán, capibara). Receta: prompt «Four cute 3D Pixar-style animals ... in a row ... Clothing only red, white and gold (no green clothing) ... chroma key green» → `DIL=2 python scripts/separar_animales.py img.jpg assets/navidad/publico <pref> a,b,c,d`. Faltan: granja, Australia, aves.
- Prueba local del armado repartido OK (3 tramos unidos con concat -c copy + audio; el corte no se nota).
- Tests: el botón enviar de Flow se mueve; usar `find "arrow_forward"` y clic por ref.

## Pendiente inmediato (en orden)
1. (HECHO) Construir el armado repartido: `ciudad.py --desde/--hasta` (cuadros) por máquina + job final que une video, mezcla audio y sube. Ojo: `s._skyx` se acumula cuadro a cuadro → precalcularlo como arreglo para que no salte entre tramos.
2. Imágenes navideñas en Flow (lista en `navidad_plan.md`).
3. Escribir ~520 preguntas (quedan ~450 tras la revisión de fotos). Hay una parte A empezada: `contenido/ciudad/preguntas_a.txt` (162 fáciles, formato `pregunta ; correcta ; incorrecta ; foto ok ; foto mal ; respuesta`). Falta: partes B y C (medias/difíciles) + 30 % navideñas + script que arme el JSON (como `scripts/escribir_rapido001.py`) y revisión contra `banco/preguntas.jsonl`.
4. SIGUIENTE: Generalizar `ciudad.py` a 9 zonas (fondos `assets/navidad/fondos/z1..z9`, ZONAS, regalos A/B en vez de puertas, público de animales a los costados, 6 etapas del dragón de `assets/navidad/`, MAX/NOVA con gorro) (fondo, fachadas, vehículo y eventos por zona) y a más etapas del dragón.
5. Producir el episodio, subir en privado, Luis revisa.

## Luis
Una sola propuesta decidida; lenguaje simple; respuestas breves; todo gratis; no construir sin su autorización (ya autorizó el episodio de Navidad); honestidad. Meta: 300K suscriptores con 2 videos (se le dijo que es muy difícil; el plan busca maximizar la probabilidad).
