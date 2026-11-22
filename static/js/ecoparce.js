// EcoParce · comportamiento mínimo sin dependencias (la política CSP no permite scripts en línea).
(function () {
  'use strict';

  // Sombra sutil en el encabezado al hacer scroll.
  var encabezado = document.getElementById('encabezado');
  if (encabezado) {
    var actualizarSombra = function () {
      encabezado.classList.toggle('con-sombra', window.scrollY > 8);
    };
    window.addEventListener('scroll', actualizarSombra, { passive: true });
    actualizarSombra();
  }

  // Modo de alto contraste (accesibilidad WCAG AAA, persistido en navegador).
  var btnContraste = document.getElementById('btn-contraste');
  function aplicarContraste(activo) {
    if (activo) {
      document.documentElement.setAttribute('data-contraste', 'alto');
    } else {
      document.documentElement.removeAttribute('data-contraste');
    }
    if (btnContraste) {
      btnContraste.setAttribute('aria-pressed', activo ? 'true' : 'false');
      btnContraste.textContent = activo ? 'Contraste normal' : 'Alto contraste';
    }
  }
  try {
    if (localStorage.getItem('ecoparce_contraste') === 'alto') { aplicarContraste(true); }
  } catch (e) { /* almacenamiento no disponible */ }
  if (btnContraste) {
    btnContraste.addEventListener('click', function () {
      var nuevo = document.documentElement.getAttribute('data-contraste') !== 'alto';
      aplicarContraste(nuevo);
      try { localStorage.setItem('ecoparce_contraste', nuevo ? 'alto' : 'normal'); } catch (e) { /* ignorar */ }
    });
  }

  // Consentimiento de cookies (sin patrones engañosos; bloquea recursos externos hasta aceptar).
  var banner = document.getElementById('banner-cookies');
  var btnAceptar = document.getElementById('cookies-aceptar');
  var btnEsenciales = document.getElementById('cookies-esenciales');
  var btnPrefs = document.getElementById('btn-preferencias-cookies');

  function leerCookies() {
    try { return localStorage.getItem('ecoparce_cookies') || ''; } catch (e) { return ''; }
  }
  function guardarCookies(valor) {
    try { localStorage.setItem('ecoparce_cookies', valor); } catch (e) { /* ignorar */ }
    document.cookie = 'ecoparce_cookies=' + encodeURIComponent(valor) + '; path=/; max-age=15552000; SameSite=Lax';
    if (banner) { banner.hidden = true; }
    window.dispatchEvent(new CustomEvent('ecoparce:cookies', { detail: valor }));
  }
  if (banner && !leerCookies()) {
    banner.hidden = false;
  }
  if (btnAceptar) { btnAceptar.addEventListener('click', function () { guardarCookies('todas'); }); }
  if (btnEsenciales) { btnEsenciales.addEventListener('click', function () { guardarCookies('esenciales'); }); }
  if (btnPrefs && banner) {
    btnPrefs.addEventListener('click', function () {
      banner.hidden = false;
      if (btnAceptar) { btnAceptar.focus(); }
    });
  }

  // Navegación con teclado: Escape cierra el banner de cookies si está abierto.
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && banner && !banner.hidden && leerCookies()) {
      banner.hidden = true;
    }
  });

  // Cerrar avisos temporales (mensajes flash).
  document.querySelectorAll('[data-cerrar-aviso]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var aviso = btn.closest('.aviso');
      if (aviso) { aviso.remove(); }
    });
  });

  // RF-14: compartir una guía con la hoja nativa del teléfono, o copiar el enlace.
  document.querySelectorAll('[data-compartir]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var url = btn.getAttribute('data-url');
      var titulo = btn.getAttribute('data-titulo');
      if (navigator.share) {
        navigator.share({ title: titulo, text: titulo + ' · EcoParce', url: url }).catch(function () {});
        return;
      }
      var mostrarCopiado = function () {
        var aviso = document.getElementById('aviso-copiado');
        if (aviso) {
          aviso.hidden = false;
          clearTimeout(aviso._t);
          aviso._t = setTimeout(function () { aviso.hidden = true; }, 5000);
        }
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(mostrarCopiado).catch(function () {});
      }
    });
  });

  // Confirmación antes de acciones irreversibles en el panel.
  document.querySelectorAll('form[data-confirmar]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (!window.confirm(f.getAttribute('data-confirmar'))) { e.preventDefault(); }
    });
  });

  // Formulario de QR: mostrar el selector de guía solo cuando el destino es una guía.
  var destino = document.getElementById('id_destino_tipo');
  var campoGuia = document.getElementById('campo-guia');
  if (destino && campoGuia) {
    var actualizar = function () { campoGuia.hidden = destino.value !== 'GUIA'; };
    destino.addEventListener('change', actualizar);
    actualizar();
  }

  // Limpieza de estado local al cerrar sesión (el servidor destruye la sesión por POST + CSRF).
  document.querySelectorAll('form[data-cerrar-sesion]').forEach(function (f) {
    f.addEventListener('submit', function () {
      try { sessionStorage.clear(); } catch (e) { /* ignorar */ }
      var b = f.querySelector('button[type=submit]');
      if (b) { b.setAttribute('aria-busy', 'true'); }
    });
  });

  // Evitar doble envío y restaurar botones si el usuario vuelve con el botón «Atrás» (bfcache).
  document.querySelectorAll('form').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (e.defaultPrevented) { return; }
      var b = f.querySelector('button[type=submit]:not([name])');
      if (b) {
        b.setAttribute('data-enviando', '1');
        setTimeout(function () { b.disabled = true; }, 0);
      }
    });
  });

  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      document.querySelectorAll('button[data-enviando="1"]').forEach(function (b) {
        b.disabled = false;
        b.removeAttribute('data-enviando');
      });
    }
  });
})();
