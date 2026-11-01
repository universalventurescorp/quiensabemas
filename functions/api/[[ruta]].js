// API de las salas de ¿Quién Sabe Más? (Cloudflare Pages Functions + D1, plan gratis).
// El celular calcula todo el juego en local; aquí solo se guarda el reloj compartido del grupo y el marcador.
// Rutas: POST grupo · POST unir · POST control · POST marcador · GET estado?codigo= · GET fama?sala=

const LETRAS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // sin I, O, 0, 1 para no confundir
const PROHIBIDAS = /(\bput[aoi]|mierd|\bverg|\bpene\b|\bculo|\bcono\b|pinga|cabron|maric|chucha|\bctm\b|conchatu|\bnazi|hitler|porno|\bsexo|\bpoto\b|\bcaca\b)/;
const normalizar = t => t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .replace(/0/g, 'o').replace(/1/g, 'i').replace(/3/g, 'e').replace(/4/g, 'a').replace(/5/g, 's').replace(/\$/g, 's').replace(/[^a-z ]/g, ' ');

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
});
const error = (msg, status = 400) => json({ error: msg }, status);
const codigoNuevo = n => Array.from(crypto.getRandomValues(new Uint8Array(n)), b => LETRAS[b % LETRAS.length]).join('');
const limpiarCodigo = c => String(c || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8);

async function estado(db, codigo) {
  const g = await db.prepare('SELECT codigo, sala, inicio, pausa, pausado, ajuste FROM grupos WHERE codigo = ?').bind(codigo).first();
  if (!g) return null;
  const { results } = await db.prepare('SELECT apodo, puntos, aciertos FROM jugadores WHERE codigo = ? ORDER BY puntos DESC, apodo LIMIT 30').bind(codigo).all();
  return { ahora: Date.now(), grupo: g, ranking: results, jugadores: results.map(r => r.apodo) };
}

export async function onRequest({ request, env, params }) {
  const db = env.DB;
  const ruta = (params.ruta || []).join('/');
  const url = new URL(request.url);
  let c = {};
  if (request.method === 'POST') {
    try { c = await request.json(); } catch { return error('Pedido inválido'); }
  }
  const ahora = Date.now();

  if (ruta === 'grupo' && request.method === 'POST') {
    const sala = limpiarCodigo(c.sala);
    if (!sala) return error('Falta la sala');
    for (let i = 0; i < 5; i++) {
      const codigo = codigoNuevo(4);
      const r = await db.prepare('INSERT OR IGNORE INTO grupos (codigo, sala, creado, pausado, ajuste) VALUES (?, ?, ?, 0, 0)').bind(codigo, sala, ahora).run();
      if (r.meta.changes) return json({ codigo });
    }
    return error('No se pudo crear el grupo, intenta otra vez', 503);
  }

  if (ruta === 'unir' && request.method === 'POST') {
    const codigo = limpiarCodigo(c.codigo);
    const apodo = String(c.apodo || '').trim().replace(/\s+/g, ' ').slice(0, 14);
    if (apodo.length < 2) return error('Escribe un apodo de al menos 2 letras.');
    if (PROHIBIDAS.test(normalizar(apodo)) || PROHIBIDAS.test(normalizar(apodo).replace(/ /g, ''))) return error('Elige otro apodo, por favor.');
    const g = await db.prepare('SELECT codigo FROM grupos WHERE codigo = ?').bind(codigo).first();
    if (!g) return error('No encontramos ese grupo. Revisa el código.', 404);
    const n = await db.prepare('SELECT COUNT(*) AS n FROM jugadores WHERE codigo = ?').bind(codigo).first('n');
    if (n >= 30) return error('Este grupo ya está lleno (30 jugadores).', 409);
    const ya = await db.prepare('SELECT id FROM jugadores WHERE codigo = ? AND apodo = ?').bind(codigo, apodo).first();
    const id = ya ? ya.id : crypto.randomUUID();
    if (!ya) await db.prepare('INSERT INTO jugadores (id, codigo, apodo, fama, puntos, aciertos, ultima, act) VALUES (?, ?, ?, ?, 0, 0, 0, ?)')
      .bind(id, codigo, apodo, c.fama ? 1 : 0, ahora).run();
    return json({ jugador: id, ...(await estado(db, codigo)) });
  }

  if (ruta === 'control' && request.method === 'POST') {
    const codigo = limpiarCodigo(c.codigo);
    const g = await db.prepare('SELECT * FROM grupos WHERE codigo = ?').bind(codigo).first();
    if (!g) return error('No encontramos ese grupo.', 404);
    if (c.accion === 'empezar' && !g.inicio) await db.prepare('UPDATE grupos SET inicio = ? WHERE codigo = ? AND inicio IS NULL').bind(ahora, codigo).run();
    if (c.accion === 'pausa' && g.inicio && !g.pausa) await db.prepare('UPDATE grupos SET pausa = ? WHERE codigo = ?').bind(ahora, codigo).run();
    if (c.accion === 'seguir' && g.pausa) await db.prepare('UPDATE grupos SET pausado = pausado + (? - pausa), pausa = NULL WHERE codigo = ?').bind(ahora, codigo).run();
    if (c.accion === 'ajuste') {
      const v = Math.max(-600000, Math.min(600000, Math.round(Number(c.valor) || 0)));
      await db.prepare('UPDATE grupos SET ajuste = ajuste + ? WHERE codigo = ?').bind(v, codigo).run();
    }
    return json(await estado(db, codigo));
  }

  if (ruta === 'marcador' && request.method === 'POST') {
    const codigo = limpiarCodigo(c.codigo);
    const puntos = Math.max(0, Math.min(1000000, Math.round(Number(c.puntos) || 0)));
    const aciertos = Math.max(0, Math.min(1000, Math.round(Number(c.aciertos) || 0)));
    const n = Math.round(Number(c.n) || 0);
    await db.prepare('UPDATE jugadores SET puntos = ?, aciertos = ?, ultima = ?, act = ? WHERE id = ? AND codigo = ? AND ultima <= ?')
      .bind(puntos, aciertos, n, ahora, String(c.jugador || ''), codigo, n).run();
    return json(await estado(db, codigo));
  }

  if (ruta === 'estado') {
    const e = await estado(db, limpiarCodigo(url.searchParams.get('codigo')));
    return e ? json(e) : error('No encontramos ese grupo.', 404);
  }

  if (ruta === 'fama') { // lo lee el montador para el "Salón de la fama" del siguiente episodio
    const sala = limpiarCodigo(url.searchParams.get('sala'));
    const { results } = await db.prepare(
      'SELECT j.apodo, j.puntos, j.aciertos FROM jugadores j JOIN grupos g ON g.codigo = j.codigo WHERE g.sala = ? AND j.fama = 1 ORDER BY j.puntos DESC LIMIT 10'
    ).bind(sala).all();
    return json({ sala, top: results });
  }

  return error('Ruta no encontrada', 404);
}
