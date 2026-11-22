// Escáner de EcoParce: usa BarcodeDetector del navegador si existe; si no, ZXing (incluido en el sitio).
// Incluye decodificador interactivo de símbolos de reciclaje impresos en la base de los envases.
(function () {
  'use strict';
  var script = document.getElementById('escaner-js');
  if (!script) { return; }
  var API = script.getAttribute('data-api').replace('00000000', '{c}');
  var BUSCAR = script.getAttribute('data-buscar');
  var caja = document.getElementById('escaner');
  var video = document.getElementById('video'), vacio = document.getElementById('escaner-vacio');
  var btn = document.getElementById('btn-camara'), detener = document.getElementById('btn-detener');
  var resultado = document.getElementById('resultado');
  var flujo = null, lector = null, activo = false, ultimo = '';

  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function aviso(clase, html) {
    var rol = clase === 'error' ? 'alert' : 'status';
    resultado.innerHTML = '<div class="aviso ' + clase + '" role="' + rol + '" style="margin-top:14px">' + html + '</div>';
  }

  function mostrar(d) {
    if (d.error) { aviso('error', esc(d.error)); return; }
    if (!d.encontrado) {
      aviso('info', 'No encontramos el producto <strong>' + esc(d.codigo) + '</strong> en las bases abiertas. ' +
        'Revisa el símbolo de reciclaje en la base del envase abajo o <a href="' + BUSCAR + '">búscalo por su nombre</a>.');
      return;
    }
    var h = '<section class="card" style="margin-top:14px;padding:16px"><div class="small mut">' + esc(d.marca) + '</div>' +
      '<strong style="font-size:18px">' + esc(d.nombre) + '</strong>';
    if (!d.partes.length) {
      h += '<p class="small" style="margin-top:8px">Este producto aún no tiene registrado su empaque. Mira el símbolo en la base del envase abajo: plástico, vidrio, metal, papel y cartón limpios van en la <strong>bolsa blanca</strong>; empaques metalizados o con comida, en la <strong>negra</strong>.</p>';
    } else {
      d.partes.forEach(function (p) {
        h += '<div class="row" style="margin-top:12px;align-items:flex-start"><span class="swatch chip-' + esc(p.codigo) + '" style="width:44px;height:44px;border-radius:12px"></span>' +
          '<div><strong>' + esc(p.parte) + '</strong> <span class="small mut">· ' + esc(p.material) + '</span>' +
          (p.simbolo ? ' <span class="tag">' + esc(p.simbolo) + '</span>' : '') +
          '<br>va en: <strong>' + esc(p.contenedor) + '</strong>' +
          '<div class="small mut">' + esc(p.indicacion) + '</div>' +
          (p.significado ? '<div class="xs mut" style="margin-top:4px;padding:6px 8px;background:var(--bg);border-radius:8px"><strong>Etiqueta ' + esc(p.simbolo) + ':</strong> ' + esc(p.significado) + '</div>' : '') +
          (p.puntos_url ? '<a class="btn o sm" style="margin-top:6px" href="' + esc(p.puntos_url) + '">Ver puntos de recolección</a>' : '') + '</div></div>';
      });
      h += '<p class="xs mut" style="margin-top:10px">Si sobra comida, va en la bolsa verde antes de separar el empaque.</p>';
    }
    h += '<p class="src">Datos del producto: <a href="' + esc(d.fuente_url) + '" target="_blank" rel="noopener noreferrer">' + esc(d.fuente) + '</a> (licencia ODbL).</p></section>';
    resultado.innerHTML = h;
  }

  function consultar(codigo) {
    if (!/^\d{8,14}$/.test(codigo)) { aviso('error', 'El código debe tener entre 8 y 14 dígitos.'); return; }
    aviso('info', 'Buscando el producto ' + esc(codigo) + '…');
    fetch(API.replace('{c}', codigo), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) {
        return r.json().catch(function () { return { error: 'No pudimos leer la respuesta del servidor.' }; });
      })
      .then(mostrar)
      .catch(function () { aviso('error', 'No hay conexión. Inténtalo de nuevo.'); });
  }

  function leido(texto) {
    if (!texto || texto === ultimo) { return; }
    ultimo = texto;
    if (navigator.vibrate) { navigator.vibrate(80); }
    try {
      var u = new URL(texto, location.origin);
      if (u.origin === location.origin && /^\/q\/[A-Z0-9]{8}$/.test(u.pathname)) { parar(); location.href = u.pathname; return; }
    } catch (e) { /* no es URL */ }
    if (/^\d{8,14}$/.test(texto)) { parar(); document.getElementById('codigo').value = texto; consultar(texto); return; }
    aviso('info', 'Leímos un código que no es de un producto ni de EcoParce.');
  }

  function parar() {
    activo = false;
    if (caja) { caja.classList.remove('escaner--activo'); }
    if (lector) { try { lector.reset(); } catch (e) { /* ignorar */ } lector = null; }
    if (flujo) { flujo.getTracks().forEach(function (t) { t.stop(); }); flujo = null; }
    video.srcObject = null; vacio.hidden = false; btn.hidden = false; detener.hidden = true;
  }

  function conDetector() {
    var det = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'qr_code', 'code_128'] });
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false }).then(function (s) {
      flujo = s; video.srcObject = s; video.play(); activo = true;
      if (caja) { caja.classList.add('escaner--activo'); }
      (function ciclo() {
        if (!activo) { return; }
        det.detect(video).then(function (c) { if (c.length) { leido(c[0].rawValue); } })
          .catch(function () { /* cuadro sin datos */ }).then(function () { if (activo) { setTimeout(ciclo, 250); } });
      })();
    }).catch(errorCamara);
  }

  function conZxing() {
    if (!window.ZXing) { aviso('error', 'Tu navegador no permite leer códigos. Escribe el número.'); parar(); return; }
    lector = new ZXing.BrowserMultiFormatReader();
    activo = true;
    if (caja) { caja.classList.add('escaner--activo'); }
    lector.decodeFromConstraints({ video: { facingMode: 'environment' } }, video, function (res) {
      if (res && activo) { leido(res.getText()); }
    }).catch(errorCamara);
  }

  function errorCamara(e) {
    parar();
    aviso('error', e && e.name === 'NotAllowedError'
      ? 'No diste permiso para usar la cámara. Puedes escribir el número del código.'
      : 'No pudimos abrir la cámara. Puedes escribir el número del código.');
  }

  btn.addEventListener('click', function () {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      aviso('error', 'Este navegador no permite usar la cámara aquí. Escribe el número del código.'); return;
    }
    ultimo = ''; resultado.innerHTML = ''; vacio.hidden = true; btn.hidden = true; detener.hidden = false;
    if ('BarcodeDetector' in window) {
      window.BarcodeDetector.getSupportedFormats().then(function (f) { return f.indexOf('ean_13') >= 0 ? conDetector() : conZxing(); })
        .catch(conZxing);
    } else { conZxing(); }
  });
  detener.addEventListener('click', parar);
  document.getElementById('form-codigo').addEventListener('submit', function (e) {
    e.preventDefault(); consultar(document.getElementById('codigo').value.trim());
  });
  window.addEventListener('pagehide', parar);

  // Decodificador interactivo de símbolos de reciclaje (base del envase)
  var SIMBOLOS = {
    PET: { titulo: '♳ 1 · PET (Tereftalato de polietileno)', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Presente en botellas de agua, gaseosa y aceite. Es uno de los plásticos más aprovechados por recicladores en Colombia.', prep: 'Preparación: Vacía el líquido, enjuaga rápido, aplasta y ponle la tapa.' },
    HDPE: { titulo: '♴ 2 · HDPE / PEAD (Polietileno alta densidad)', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Envases opacos y resistentes: detergente, suavizante, shampoo y leche. Altamente reciclable.', prep: 'Preparación: Enjuaga el interior para quitar jabón o restos y déjalo escurrir.' },
    PVC: { titulo: '♵ 3 · PVC (Policloruro de vinilo)', chip: 'chip-NEGRA', bolsa: 'Bolsa Negra (No aprovechables en hogar)', desc: 'Usado en blísters, tarjetas y algunos empaques rígidos. Contiene cloro y es difícil de reciclar en recolección doméstica.', prep: 'Recomendación: Evita mezclarlo con PET o HDPE en la bolsa blanca.' },
    LDPE: { titulo: '♶ 4 · LDPE / PEBD (Polietileno baja densidad)', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca si está limpio (Negra si tiene comida)', desc: 'Bolsas flexibles, empaques de pan y film plástico transparente.', prep: 'Preparación: Solo va en bolsa blanca si está completamente seco y sin grasa ni migas.' },
    PP: { titulo: '♷ 5 · PP (Polipropileno)', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Tapas de botellas, vasos de yogur, envases de margarina y recipientes rígidos.', prep: 'Preparación: Retira restos de alimento, enjuaga y seca antes de depositarlo.' },
    PS: { titulo: '♸ 6 · PS (Poliestireno / Icopor)', chip: 'chip-NEGRA', bolsa: 'Bolsa Negra (No aprovechables)', desc: 'Bandejas de comida, platos y vasos desechables de icopor. Al tener grasa o comida no se aprovecha en la ruta ordinaria.', prep: 'Recomendación: Quita restos de comida a la bolsa verde y deposita el icopor en la negra.' },
    OTROS: { titulo: '♹ 7 · Otros plásticos y laminados', chip: 'chip-NEGRA', bolsa: 'Bolsa Negra (salvo reciclaje especializado)', desc: 'Mezclas de varios plásticos o empaques metalizados (paquetes de papas/mecato). Difíciles de separar mecánicamente.', prep: 'Recomendación: Deposítalo en la bolsa negra bien cerrada.' },
    TETRA: { titulo: 'C/PAP 84 · Multicapa (Tetra Pak)', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Cajas de leche y jugo compuestas por cartón, polietileno y aluminio. En Colombia sí tienen cadena de reciclaje.', prep: 'Preparación: Vacía, enjuaga, abre las esquinas, aplasta y deja secar.' },
    PAP: { titulo: 'PAP 20 / 21 / 22 · Cartón y Papel', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Cajas de cartón corrugado, plegadizas de cereal, cuadernos y papel de oficina.', prep: 'Preparación: Desarma y aplasta las cajas; nunca mezcles cartón con grasa o aceite.' },
    GL: { titulo: 'GL 70 / 71 / 72 · Vidrio', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Frascos y botellas de vidrio transparente, verde o ámbar. Se recicla infinitas veces sin perder calidad.', prep: 'Preparación: Enjuaga y seca. Si está roto, envuélvelo en papel/cartón y márcalo «vidrio roto».' },
    ALU: { titulo: 'ALU 41 · Aluminio (y FE 40 Acero)', chip: 'chip-BLANCA', bolsa: 'Bolsa Blanca (Aprovechables)', desc: 'Latas de bebidas y conservas. Reciclar aluminio ahorra hasta un 95 % de energía.', prep: 'Preparación: Vacía, enjuaga y aplasta las latas para reducir volumen.' },
    RAEE: { titulo: 'Contenedor tachado · Residuo Posconsumo / RAEE', chip: 'chip-POSCONSUMO', bolsa: 'Punto de entrega Posconsumo (¡Nunca a la bolsa!)', desc: 'Indica pilas, baterías, bombillos ahorradores, medicamentos vencidos o aparatos electrónicos con sustancias peligrosas.', prep: 'Acción: Guárdalo aparte sin romperlo y ubícalo en el mapa de Puntos Oficiales.' }
  };

  var botonesSim = document.querySelectorAll('[data-simbolo]');
  var sSwatch = document.getElementById('sim-swatch');
  var sTit = document.getElementById('sim-titulo');
  var sBolsa = document.getElementById('sim-bolsa');
  var sDesc = document.getElementById('sim-desc');
  var sPrep = document.getElementById('sim-prep');
  botonesSim.forEach(function (b) {
    b.addEventListener('click', function () {
      var info = SIMBOLOS[b.getAttribute('data-simbolo')];
      if (!info) { return; }
      botonesSim.forEach(function (x) { x.classList.remove('activo'); x.setAttribute('aria-pressed', 'false'); });
      b.classList.add('activo');
      b.setAttribute('aria-pressed', 'true');
      if (sSwatch) { sSwatch.className = 'swatch ' + info.chip; }
      if (sTit) { sTit.textContent = info.titulo; }
      if (sBolsa) { sBolsa.textContent = info.bolsa; }
      if (sDesc) { sDesc.textContent = info.desc; }
      if (sPrep) { sPrep.textContent = info.prep; }
    });
  });
})();
