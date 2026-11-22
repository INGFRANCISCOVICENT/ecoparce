// Mapa de puntos de recolección (Leaflet + OpenStreetMap).
// Respeta el consentimiento de cookies: las teselas externas de OpenStreetMap solo se cargan si el visitante acepta.
// La ubicación del visitante nunca sale del navegador.
(function () {
  'use strict';
  var cont = document.getElementById('mapa');
  if (!cont || !window.L) { return; }

  var puntos = [], mapa = null, capa = null, yo = null, datosCargados = false;
  var lista = document.getElementById('lista-puntos'), estado = document.getElementById('estado-mapa');

  var IC_PIN = '<svg class="i" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4B5A51" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>';
  var IC_CLOCK = '<svg class="i" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4B5A51" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>';
  var IC_PHONE = '<svg class="i" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4B5A51" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/></svg>';
  var IC_ARROW = '<svg class="i" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';

  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function llegar(p) { return 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(p.la) + ',' + encodeURIComponent(p.lo); }
  function tarjeta(p) {
    return '<div class="card"><strong>' + esc(p.n) + '</strong>' +
      (p.km != null ? ' <span class="tag">' + (p.km < 1 ? Math.round(p.km * 1000) + ' m' : p.km.toFixed(1) + ' km') + '</span>' : '') +
      '<div class="dato">' + IC_PIN + '<span>' + esc(p.d) + ' · ' + esc(p.l) + (p.b ? ' (' + esc(p.b) + ')' : '') + '</span></div>' +
      '<div class="dato">' + IC_CLOCK + '<span>' + esc(p.h) + '</span></div>' +
      (p.t ? '<div class="dato">' + IC_PHONE + '<span>' + esc(p.t) + '</span></div>' : '') +
      '<div class="xs mut" style="margin-top:6px">Recibe: ' + esc(p.r || '—') + (p.f ? ' · información del ' + esc(p.f) : '') + '</div>' +
      '<a class="btn o sm" style="margin-top:8px" target="_blank" rel="noopener noreferrer" href="' + llegar(p) + '">' + IC_ARROW + 'Cómo llegar</a></div>';
  }
  function pintar() {
    if (!mapa || !capa) { return; }
    capa.clearLayers();
    puntos.forEach(function (p) {
      L.circleMarker([p.la, p.lo], { radius: 6, color: '#ffffff', weight: 1.5, fillColor: '#C81E1E', fillOpacity: 0.9 })
        .bindPopup('<strong>' + esc(p.n) + '</strong><br>' + esc(p.d) + '<br><small>' + esc(p.h) + '</small><br><a target="_blank" rel="noopener noreferrer" href="' + llegar(p) + '">Cómo llegar</a>')
        .addTo(capa);
    });
    if (yo) {
      L.circleMarker(yo, { radius: 8, color: '#1F4FA3', fillColor: '#1F4FA3', fillOpacity: 0.85 }).bindTooltip('Tú').addTo(capa);
    }
    if (puntos.length && !yo) {
      mapa.fitBounds(L.latLngBounds(puntos.map(function (p) { return [p.la, p.lo]; })), { padding: [20, 20], maxZoom: 15 });
    }
  }
  function iniciarMapa() {
    if (mapa) { return; }
    cont.innerHTML = '';
    mapa = L.map(cont, { preferCanvas: true, scrollWheelZoom: false }).setView([4.65, -74.1], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright" rel="noopener noreferrer">OpenStreetMap</a> · Puntos: SDA Bogotá'
    }).addTo(mapa);
    capa = L.layerGroup().addTo(mapa);
    if (datosCargados) { pintar(); }
  }
  function mostrarBloqueoMapa() {
    cont.innerHTML = '<div class="mapa-bloqueado"><strong>Mapa interactivo bloqueado por privacidad</strong>' +
      '<p class="small mut" style="max-width:420px;margin:0">El mapa carga imágenes desde OpenStreetMap. La lista de puntos abajo ya está disponible sin recursos externos.</p>' +
      '<button type="button" class="btn p sm" id="cargar-mapa-osm">Cargar mapa de OpenStreetMap</button></div>';
    var btnOsm = document.getElementById('cargar-mapa-osm');
    if (btnOsm) { btnOsm.addEventListener('click', iniciarMapa); }
  }
  function tieneConsentimiento() {
    try { return localStorage.getItem('ecoparce_cookies') === 'todas'; } catch (e) { return false; }
  }
  if (tieneConsentimiento()) {
    iniciarMapa();
  } else {
    mostrarBloqueoMapa();
    window.addEventListener('ecoparce:cookies', function (e) {
      if (e.detail === 'todas') { iniciarMapa(); }
    });
  }

  function distancia(a, b, c, d) {
    var R = 6371, r = Math.PI / 180, x = (c - a) * r, y = (d - b) * r;
    var h = Math.sin(x / 2) * Math.sin(x / 2) + Math.cos(a * r) * Math.cos(c * r) * Math.sin(y / 2) * Math.sin(y / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function cercanos(lat, lon) {
    yo = [lat, lon];
    puntos.forEach(function (p) { p.km = distancia(lat, lon, p.la, p.lo); });
    var orden = puntos.slice().sort(function (a, b) { return a.km - b.km; }).slice(0, 15);
    lista.innerHTML = orden.map(tarjeta).join('') || '<div class="card mut">No hay puntos con este filtro.</div>';
    if (mapa && capa) {
      L.circleMarker(yo, { radius: 8, color: '#1F4FA3', fillColor: '#1F4FA3', fillOpacity: 0.85 }).bindTooltip('Tú').addTo(capa);
      if (orden.length) { mapa.fitBounds(L.latLngBounds([yo].concat(orden.slice(0, 5).map(function (p) { return [p.la, p.lo]; }))), { padding: [30, 30] }); }
    }
    if (estado) { estado.textContent = 'Los 15 puntos más cercanos a ti, ordenados por distancia en línea recta.'; }
  }
  fetch(cont.getAttribute('data-url'), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
    .then(function (r) { if (!r.ok) { throw new Error('HTTP ' + r.status); } return r.json(); })
    .then(function (d) { puntos = d.puntos || []; datosCargados = true; pintar(); })
    .catch(function () {
      if (estado) { estado.textContent = 'No pudimos cargar los datos del mapa ahora mismo. Puedes consultar la lista de puntos abajo.'; }
    });

  var boton = document.getElementById('cerca-de-mi');
  if (boton) {
    if (!navigator.geolocation) { boton.hidden = true; }
    boton.addEventListener('click', function () {
      boton.disabled = true;
      if (estado) { estado.textContent = 'Buscando tu ubicación…'; }
      navigator.geolocation.getCurrentPosition(function (pos) {
        boton.disabled = false; cercanos(pos.coords.latitude, pos.coords.longitude);
      }, function () {
        boton.disabled = false;
        if (estado) { estado.textContent = 'No pudimos obtener tu ubicación. Revisa el permiso del navegador o filtra por localidad.'; }
      }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
    });
  }
})();
