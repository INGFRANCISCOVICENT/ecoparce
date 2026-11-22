// Portada interactiva de EcoParce: Escarlata volando con mensajes de sensibilización,
// píldoras de separación y ubicación en vivo privada en el navegador (RN-08).
(function () {
  'use strict';

  // 1. Mensajes de sensibilización ambiental que deja Escarlata al volar
  var mensajes = [
    'Cada botella PET limpia que separas ahorra energía para encender un bombillo LED por 3 horas.',
    '1 litro de aceite de cocina usado por el desagüe puede contaminar hasta 1.000 litros de agua.',
    'Limpio y seco en la bolsa blanca: así el reciclador de oficio sí puede aprovechar tu esfuerzo.',
    'Las pilas, bombillos y medicamentos vencidos van a puntos posconsumo, nunca a la bolsa común.',
    'Separar orgánicos en la bolsa verde reduce los gases de efecto invernadero en el relleno sanitario.',
    'El vidrio limpio se recicla infinitas veces sin perder su pureza ni calidad.'
  ];
  var txtVuelo = document.getElementById('escarlata-mensaje');
  var idx = 0;
  var reducir = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (txtVuelo) {
    setInterval(function () {
      idx = (idx + 1) % mensajes.length;
      txtVuelo.classList.add('cambiando');
      setTimeout(function () {
        txtVuelo.textContent = mensajes[idx];
        txtVuelo.classList.remove('cambiando');
      }, reducir ? 0 : 220);
    }, 5200);
  }

  // 2. Píldoras interactivas estilo CiudadReporta (Bolsa Blanca, Negra, Verde, Posconsumo)
  var pildoras = document.querySelectorAll('[data-eco-tab]');
  var detalleTxt = document.getElementById('eco-detalle-txt');
  var detalleDot = document.getElementById('eco-detalle-dot');
  var detalleLink = document.getElementById('eco-detalle-link');
  pildoras.forEach(function (btn) {
    btn.addEventListener('click', function () {
      pildoras.forEach(function (b) {
        b.classList.remove('activo');
        b.setAttribute('aria-pressed', 'false');
      });
      btn.classList.add('activo');
      btn.setAttribute('aria-pressed', 'true');
      if (detalleTxt) { detalleTxt.textContent = btn.getAttribute('data-eco-msg') || ''; }
      if (detalleDot) { detalleDot.style.background = btn.getAttribute('data-eco-color') || '#22C55E'; }
      if (detalleLink) {
        var href = btn.getAttribute('data-eco-url');
        if (href) { detalleLink.setAttribute('href', href); }
      }
    });
  });

  // 3. Ubicación en vivo privada (solo en el navegador, nunca se envía al servidor)
  var btnUbi = document.getElementById('btn-ubicacion-viva');
  var estadoUbi = document.getElementById('estado-ubicacion-viva');
  var watchId = null;
  var puntosCache = null;

  function distanciaKm(a, b, c, d) {
    var R = 6371, r = Math.PI / 180, x = (c - a) * r, y = (d - b) * r;
    var h = Math.sin(x / 2) * Math.sin(x / 2) + Math.cos(a * r) * Math.cos(c * r) * Math.sin(y / 2) * Math.sin(y / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }

  function mostrarCercano(lat, lon) {
    if (!estadoUbi) { return; }
    if (!puntosCache || !puntosCache.length) {
      estadoUbi.innerHTML = '<span class="pulso-verde"></span> Ubicación en vivo activa · <a href="/puntos/" class="portada-link-claro">Abrir mapa de puntos cercanos →</a>';
      return;
    }
    var mejor = null, mejorKm = Infinity;
    for (var i = 0; i < puntosCache.length; i++) {
      var km = distanciaKm(lat, lon, puntosCache[i].la, puntosCache[i].lo);
      if (km < mejorKm) { mejorKm = km; mejor = puntosCache[i]; }
    }
    if (!mejor) { return; }
    var dist = mejorKm < 1 ? Math.round(mejorKm * 1000) + ' m' : mejorKm.toFixed(1) + ' km';
    var urlMaps = 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(mejor.la) + ',' + encodeURIComponent(mejor.lo);
    estadoUbi.innerHTML = '<span class="pulso-verde"></span> <strong>Ubicación en vivo:</strong> punto posconsumo más cercano a <strong>' + esc(dist) + '</strong> (' + esc(mejor.n) + ') · <a href="' + urlMaps + '" target="_blank" rel="noopener noreferrer" class="portada-link-claro">Cómo llegar →</a>';
  }

  if (btnUbi && estadoUbi) {
    var datosUrl = btnUbi.getAttribute('data-puntos-url');
    btnUbi.addEventListener('click', function () {
      if (!navigator.geolocation) {
        estadoUbi.textContent = 'Tu navegador no soporta geolocalización. Puedes filtrar por localidad en Puntos.';
        return;
      }
      if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
        btnUbi.textContent = 'Activar ubicación en vivo';
        estadoUbi.textContent = 'Ubicación en vivo detenida. Tus coordenadas nunca salen de tu dispositivo.';
        return;
      }
      btnUbi.disabled = true;
      estadoUbi.textContent = 'Activando ubicación en vivo (solo en tu navegador)…';

      var iniciarSeguimiento = function () {
        watchId = navigator.geolocation.watchPosition(function (pos) {
          btnUbi.disabled = false;
          btnUbi.textContent = 'Desactivar ubicación en vivo';
          mostrarCercano(pos.coords.latitude, pos.coords.longitude);
        }, function () {
          btnUbi.disabled = false;
          watchId = null;
          estadoUbi.textContent = 'No diste permiso de ubicación. Puedes explorar puntos por localidad en el mapa.';
        }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 });
      };

      if (puntosCache) {
        iniciarSeguimiento();
      } else if (datosUrl) {
        fetch(datosUrl, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
          .then(function (r) { return r.ok ? r.json() : { puntos: [] }; })
          .then(function (d) { puntosCache = d.puntos || []; iniciarSeguimiento(); })
          .catch(function () { puntosCache = []; iniciarSeguimiento(); });
      } else {
        iniciarSeguimiento();
      }
    });
  }

  // 4. Calculadora interactiva de impacto ambiental anual en el hogar
  var slPet = document.getElementById('sl-pet');
  var slLatas = document.getElementById('sl-latas');
  var slCarton = document.getElementById('sl-carton');
  var slAceite = document.getElementById('sl-aceite');
  if (slPet && slLatas && slCarton && slAceite) {
    var actualizarCalc = function () {
      var pet = parseInt(slPet.value, 10) || 0;
      var latas = parseInt(slLatas.value, 10) || 0;
      var carton = parseInt(slCarton.value, 10) || 0;
      var aceite = parseInt(slAceite.value, 10) || 0;

      document.getElementById('val-pet').textContent = pet;
      document.getElementById('val-latas').textContent = latas;
      document.getElementById('val-carton').textContent = carton;
      document.getElementById('val-aceite').textContent = aceite;

      // Factores educativos anuales aproximados:
      // PET: ~0.08 kg CO2 y 3 h LED por botella; Aluminio: ~0.13 kg CO2 y 3 h LED por lata;
      // Cartón: ~0.22 kg CO2 por caja; Aceite usado: 1.000 L agua protegida por litro/mes.
      var co2 = Math.round((pet * 0.08 + latas * 0.13 + carton * 0.22) * 52);
      var agua = aceite * 12 * 1000;
      var horasLed = (pet * 3 + latas * 3) * 52;

      document.getElementById('res-co2').textContent = co2.toLocaleString('es-CO') + ' kg';
      document.getElementById('res-agua').textContent = agua.toLocaleString('es-CO') + ' L';
      document.getElementById('res-energia').textContent = horasLed.toLocaleString('es-CO') + ' h LED';

      var nivel = document.getElementById('calc-nivel');
      if (nivel) {
        if (co2 >= 120 || agua >= 24000) {
          nivel.textContent = 'Hogar Campeón Ambiental';
        } else if (co2 >= 40 || agua >= 12000) {
          nivel.textContent = 'Hogar Guardián';
        } else {
          nivel.textContent = 'Hogar Semilla';
        }
      }
    };
    [slPet, slLatas, slCarton, slAceite].forEach(function (el) {
      el.addEventListener('input', actualizarCalc);
    });
    actualizarCalc();
  }
})();
