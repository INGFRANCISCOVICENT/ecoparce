// Escáner de EcoParce: usa BarcodeDetector del navegador si existe; si no, ZXing (incluido en el sitio).
// Incluye decodificador interactivo de símbolos de reciclaje impresos en la base de los envases.
(function () {
  'use strict';
  var script = document.getElementById('escaner-js');
  if (!script) { return; }
  var API = script.getAttribute('data-api').replace('00000000', '{c}');
  var API_FOTO = script.getAttribute('data-foto') || '/escanear/foto/';
  var BUSCAR = script.getAttribute('data-buscar');
  var ASISTENTE = script.getAttribute('data-asistente') || '/asistente/consultar/';
  var caja = document.getElementById('escaner');
  var video = document.getElementById('video'), vacio = document.getElementById('escaner-vacio');
  var btn = document.getElementById('btn-camara'), detener = document.getElementById('btn-detener');
  var btnFoto = document.getElementById('btn-foto'), btnCapturar = document.getElementById('btn-capturar');
  var inputFoto = document.getElementById('input-foto'), formFoto = document.getElementById('form-foto');
  var resultado = document.getElementById('resultado');
  var flujo = null, lector = null, activo = false, ultimo = '', ultimaFotoUrl = '';

  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function aviso(clase, html) {
    var rol = clase === 'error' ? 'alert' : 'status';
    resultado.innerHTML = '<div class="aviso ' + clase + '" role="' + rol + '" style="margin-top:14px">' + html + '</div>';
  }

  function mostrar(d) {
    if (d.error) { aviso('error', esc(d.error)); return; }
    if (!d.encontrado) {
      aviso('info', 'No encontramos el código <strong>' + esc(d.codigo) + '</strong> en bases externas. ' +
        '<strong>¡No importa!</strong> <button type="button" class="link-btn" data-abrir-foto>Toma una foto del producto aquí</button> o <a href="' + BUSCAR + '">búscalo por nombre</a>.');
      var bnf = resultado.querySelector('[data-abrir-foto]');
      if (bnf && inputFoto) { bnf.addEventListener('click', function () { inputFoto.click(); }); }
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

  function enfocarResultado() {
    if (resultado && resultado.scrollIntoView) {
      resultado.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function mostrarQrTexto(texto, esUrl) {
    var h = '<section class="card" style="margin-top:14px;padding:16px">' +
      '<div class="small mut">Código QR leído correctamente</div>' +
      '<strong style="font-size:17px;word-break:break-word;display:block;margin-top:4px">' + esc(texto) + '</strong>';
    if (esUrl) {
      h += '<p class="small mut" style="margin-top:8px">Este QR apunta a un enlace externo. Puedes abrirlo o buscar el producto/residuo en EcoParce:</p>' +
        '<div class="row" style="gap:8px;flex-wrap:wrap;margin-top:10px">' +
        '<a class="btn p sm" href="' + esc(texto) + '" target="_blank" rel="noopener noreferrer">Abrir enlace del QR</a>' +
        '<a class="btn o sm" href="' + BUSCAR + '">Buscar residuo en EcoParce</a></div>';
    } else {
      h += '<p class="small mut" style="margin-top:8px">No corresponde a un código de barras numérico de producto, pero puedes buscar este texto en nuestro catálogo:</p>' +
        '<div class="row" style="gap:8px;flex-wrap:wrap;margin-top:10px">' +
        '<a class="btn p sm" href="' + BUSCAR + '?q=' + encodeURIComponent(texto.slice(0, 80)) + '">Buscar «' + esc(texto.slice(0, 40)) + '» en EcoParce</a></div>';
    }
    h += '</section>';
    resultado.innerHTML = h;
    enfocarResultado();
  }

  function consultarCatalogoQr(texto) {
    aviso('info', 'QR leído: <strong>' + esc(texto) + '</strong>. Consultando en EcoParce…');
    fetch(ASISTENTE + '?q=' + encodeURIComponent(texto.slice(0, 80)), {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.encontrado) {
          var h = '<section class="card" style="margin-top:14px;padding:16px">' +
            '<div class="small mut">Código QR identificado en EcoParce</div>' +
            '<div class="row" style="margin-top:10px;align-items:flex-start">' +
            '<span class="swatch chip-' + esc(d.codigo || 'BLANCA') + '" style="width:44px;height:44px;border-radius:12px"></span>' +
            '<div><strong style="font-size:18px">' + esc(d.residuo) + '</strong>' +
            '<br>va en: <strong>' + esc(d.contenedor) + '</strong>';
          if (d.pasos && d.pasos.length) {
            h += '<ul class="small mut" style="margin:8px 0 0 18px;padding:0">';
            d.pasos.forEach(function (paso) { h += '<li>' + esc(paso) + '</li>'; });
            h += '</ul>';
          }
          h += '<div class="row" style="gap:8px;flex-wrap:wrap;margin-top:10px">';
          if (d.guia_url) { h += '<a class="btn p sm" href="' + esc(d.guia_url) + '">' + esc(d.guia_titulo || 'Ver guía') + '</a>'; }
          if (d.puntos_url) { h += '<a class="btn o sm" href="' + esc(d.puntos_url) + '">Ver puntos de recolección</a>'; }
          h += '</div></div></div></section>';
          resultado.innerHTML = h;
          enfocarResultado();
        } else {
          mostrarQrTexto(texto, false);
        }
      })
      .catch(function () { mostrarQrTexto(texto, false); });
  }

  function extraerGtinDeUrl(u) {
    var mPath = u.pathname.match(/\/01\/(\d{8,14})(?:\/|$)/);
    if (mPath) { return mPath[1]; }
    var claves = ['gtin', 'ean', 'upc', 'barcode', 'code', 'codigo'];
    for (var i = 0; i < claves.length; i++) {
      var val = (u.searchParams.get(claves[i]) || '').trim();
      if (/^\d{8,14}$/.test(val)) { return val; }
    }
    return '';
  }

  function leido(texto) {
    texto = (texto || '').trim();
    if (!texto || texto === ultimo) { return; }
    ultimo = texto;
    if (navigator.vibrate) { navigator.vibrate(80); }
    parar();

    // 1. Código QR oficial de EcoParce (/q/XXXXXXXX en cualquier dominio o ruta relativa)
    var mEco = texto.match(/\/q\/([A-Za-z0-9]{6,16})\/?(?:\?.*)?$/i);
    if (mEco) {
      aviso('ok', 'Código QR de EcoParce detectado (<strong>' + esc(mEco[1].toUpperCase()) + '</strong>). Abriendo guía…');
      location.href = '/q/' + mEco[1].toUpperCase();
      return;
    }

    // 2. Código de barras numérico estándar (EAN-8, EAN-13, UPC-A, GTIN-14)
    if (/^\d{8,14}$/.test(texto)) {
      document.getElementById('codigo').value = texto;
      consultar(texto);
      enfocarResultado();
      return;
    }

    // 3. URL en QR: verificar si es GS1 Digital Link con código de producto o enlace web normal
    if (/^https?:\/\//i.test(texto)) {
      try {
        var u = new URL(texto);
        var gtin = extraerGtinDeUrl(u);
        if (gtin) {
          document.getElementById('codigo').value = gtin;
          consultar(gtin);
          enfocarResultado();
          return;
        }
        mostrarQrTexto(texto, true);
        return;
      } catch (e) { /* continuar como texto */ }
    }

    // 4. QR con texto libre o nombre de residuo -> consultar catálogo EcoParce
    consultarCatalogoQr(texto);
  }

  function parar() {
    activo = false;
    if (caja) { caja.classList.remove('escaner--activo'); }
    if (lector) { try { lector.reset(); } catch (e) { /* ignorar */ } lector = null; }
    if (flujo) { flujo.getTracks().forEach(function (t) { t.stop(); }); flujo = null; }
    video.srcObject = null; vacio.hidden = false; btn.hidden = false; detener.hidden = true;
    if (btnCapturar) { btnCapturar.hidden = true; }
  }

  function obtenerCsrf() {
    if (!formFoto) { return ''; }
    var inp = formFoto.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : '';
  }

  function mostrarResultadoFoto(d) {
    if (d.error) { aviso('error', esc(d.error)); return; }
    var h = '<section class="card" style="margin-top:14px;padding:16px">';
    if (d.identificado === false) {
      if (ultimaFotoUrl) {
        h += '<div class="row" style="gap:12px;align-items:center;margin-bottom:10px">' +
          '<img src="' + esc(ultimaFotoUrl) + '" alt="Foto capturada" style="width:72px;height:72px;object-fit:cover;border-radius:12px;border:1px solid var(--line)">' +
          '<div><strong style="font-size:16px">¿Qué objeto fotografiaste?</strong>' +
          '<div class="xs mut" style="margin-top:3px">' + esc(d.mensaje || 'Escribe o toca el tipo de objeto para ver dónde va.') + '</div></div></div>';
      } else {
        h += '<p class="small">' + esc(d.mensaje) + '</p>';
      }
      h += '<form id="form-objeto-foto" class="search" style="margin-top:10px" autocomplete="off">' +
        '<input id="input-objeto-foto" type="text" maxlength="80" placeholder="Ej. computador, botella, pilas, cartón, cáscara..." required>' +
        '<button type="submit">Clasificar</button></form>';
    } else {
      if (ultimaFotoUrl) {
        h += '<div class="row" style="gap:12px;align-items:center;margin-bottom:12px">' +
          '<img src="' + esc(ultimaFotoUrl) + '" alt="Foto capturada del producto" style="width:72px;height:72px;object-fit:cover;border-radius:12px;border:1px solid var(--line)">' +
          '<div><div class="xs mut">' + (d.metodo === 'ia_vision' ? 'Identificado por visión IA real' : 'Clasificación EcoParce · Res. 2184') + '</div>' +
          '<strong style="font-size:18px">' + esc(d.producto) + '</strong>' +
          (d.simbolo ? ' <div><span class="tag">' + esc(d.simbolo) + '</span></div>' : '') + '</div></div>';
      } else {
        h += '<strong style="font-size:18px">' + esc(d.producto) + '</strong>';
      }
      h += '<div class="row" style="margin-top:8px;align-items:flex-start">' +
        '<span class="swatch chip-' + esc(d.codigo) + '" style="width:48px;height:48px;border-radius:12px"></span>' +
        '<div><strong>Va en: ' + esc(d.contenedor) + '</strong>' +
        '<div class="small mut" style="margin-top:4px">' + esc(d.indicacion) + '</div>' +
        (d.puntos_url ? '<a class="btn p sm" style="margin-top:8px" href="' + esc(d.puntos_url) + '">Ver puntos posconsumo cercanos</a>' : '') +
        '</div></div>';
    }

    h += '<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--line)">' +
      '<div class="xs mut" style="margin-bottom:8px">O toca la categoría real del objeto:</div>' +
      '<div class="row" style="gap:6px;flex-wrap:wrap">' +
      '<button type="button" class="btn o sm" data-tipo-foto="electronico">PC / Electrónico (RAEE)</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="plastico">Plástico / Botella</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="carton">Cartón / Papel</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="vidrio">Vidrio</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="metal">Lata / Metal</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="metalizado">Mecato / Sucio</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="organico">Orgánico</button>' +
      '<button type="button" class="btn o sm" data-tipo-foto="posconsumo">Pila / Bombillo / Aceite</button>' +
      '</div></div></section>';

    resultado.innerHTML = h;
    var fObj = document.getElementById('form-objeto-foto');
    if (fObj) {
      fObj.addEventListener('submit', function (e) {
        e.preventDefault();
        var q = (document.getElementById('input-objeto-foto').value || '').trim();
        if (q) { consultarCatalogoQr(q); }
      });
    }
    resultado.querySelectorAll('[data-tipo-foto]').forEach(function (b) {
      b.addEventListener('click', function () { enviarFoto(null, b.getAttribute('data-tipo-foto')); });
    });
    enfocarResultado();
  }

  function enviarFoto(blob, tipoManual) {
    aviso('info', tipoManual ? 'Actualizando indicación de bolsa…' : 'Analizando la foto del producto…');
    var fd = new FormData();
    if (blob) { fd.append('foto', blob, 'producto.jpg'); }
    if (tipoManual) { fd.append('tipo', tipoManual); }
    fetch(API_FOTO, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': obtenerCsrf(), 'Accept': 'application/json' },
      body: fd
    })
      .then(function (r) { return r.json().catch(function () { return { error: 'No pudimos leer la respuesta del servidor.' }; }); })
      .then(mostrarResultadoFoto)
      .catch(function () { aviso('error', 'Error de conexión al analizar la foto. Intenta de nuevo.'); });
  }

  function detectarCodigoEnImagen(blob, alTerminar) {
    if ('BarcodeDetector' in window && window.createImageBitmap) {
      var det = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'qr_code', 'code_128'] });
      window.createImageBitmap(blob).then(function (bmp) {
        return det.detect(bmp).then(function (codigos) {
          if (bmp.close) { bmp.close(); }
          alTerminar(codigos && codigos.length ? codigos[0].rawValue : '');
        });
      }).catch(function () { alTerminar(''); });
      return;
    }
    alTerminar('');
  }

  function procesarFotoCapturada(blob) {
    aviso('info', 'Escaneando foto en busca de código o producto…');
    detectarCodigoEnImagen(blob, function (codigoDetectado) {
      if (codigoDetectado) {
        ultimo = '';
        leido(codigoDetectado);
        return;
      }
      enviarFoto(blob, '');
    });
  }

  function capturarDesdeVideo() {
    if (!video || !video.videoWidth) { aviso('error', 'Espera un segundo a que la cámara enfoque.'); return; }
    var canvas = document.createElement('canvas');
    var maxDim = 800;
    var escale = Math.min(1, maxDim / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * escale);
    canvas.height = Math.round(video.videoHeight * escale);
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    ultimaFotoUrl = canvas.toDataURL('image/jpeg', 0.8);
    parar();
    canvas.toBlob(function (blob) {
      if (blob) { procesarFotoCapturada(blob); }
    }, 'image/jpeg', 0.82);
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
    if (btnCapturar) { btnCapturar.hidden = false; }
    if ('BarcodeDetector' in window) {
      window.BarcodeDetector.getSupportedFormats().then(function (f) { return f.indexOf('ean_13') >= 0 ? conDetector() : conZxing(); })
        .catch(conZxing);
    } else { conZxing(); }
  });
  detener.addEventListener('click', parar);
  if (btnCapturar) { btnCapturar.addEventListener('click', capturarDesdeVideo); }
  if (btnFoto && inputFoto) {
    btnFoto.addEventListener('click', function () { inputFoto.click(); });
    inputFoto.addEventListener('change', function () {
      var archivo = inputFoto.files && inputFoto.files[0];
      if (!archivo) { return; }
      if (ultimaFotoUrl && ultimaFotoUrl.indexOf('blob:') === 0) { URL.revokeObjectURL(ultimaFotoUrl); }
      ultimaFotoUrl = URL.createObjectURL(archivo);
      procesarFotoCapturada(archivo);
      inputFoto.value = '';
    });
  }
  document.getElementById('form-codigo').addEventListener('submit', function (e) {
    e.preventDefault();
    ultimo = '';
    leido(document.getElementById('codigo').value.trim());
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
