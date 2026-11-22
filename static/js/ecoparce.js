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

  // Búsqueda por voz progresiva en /buscar/ (Web Speech API en español Colombia).
  var btnVoz = document.getElementById('btn-voz-buscar');
  var campoQ = document.getElementById('q');
  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (btnVoz && campoQ && SpeechRec) {
    btnVoz.hidden = false;
    btnVoz.addEventListener('click', function () {
      var rec = new SpeechRec();
      rec.lang = 'es-CO';
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      btnVoz.classList.add('escuchando');
      btnVoz.setAttribute('aria-label', 'Escuchando...');
      rec.onresult = function (ev) {
        var texto = ev.results && ev.results[0] && ev.results[0][0] ? ev.results[0][0].transcript : '';
        if (texto) {
          campoQ.value = texto.replace(/\.$/, '').trim();
          if (campoQ.form) { campoQ.form.submit(); }
        }
      };
      rec.onend = function () {
        btnVoz.classList.remove('escuchando');
        btnVoz.setAttribute('aria-label', 'Buscar por voz');
      };
      rec.onerror = function () {
        btnVoz.classList.remove('escuchando');
      };
      try { rec.start(); } catch (_) {}
    });
  }

  // Checklist interactivo del hogar en /guias/ (persistido en localStorage).
  var checksEco = document.querySelectorAll('[data-eco-check]');
  if (checksEco.length) {
    var claveCheck = 'ecoparce_checklist_hogar';
    var estadoCheck = {};
    try { estadoCheck = JSON.parse(localStorage.getItem(claveCheck) || '{}'); } catch (_) {}
    var txtProg = document.getElementById('check-progreso-txt');
    var barProg = document.getElementById('check-progreso-bar');
    var avisoOk = document.getElementById('check-felicitacion');

    var actualizarCheck = function () {
      var hechos = 0;
      checksEco.forEach(function (cb) {
        if (cb.checked) hechos++;
      });
      var pct = Math.round((hechos / checksEco.length) * 100);
      if (txtProg) txtProg.textContent = hechos + ' / ' + checksEco.length + ' listos';
      if (barProg) {
        barProg.style.width = pct + '%';
        if (barProg.parentElement) barProg.parentElement.setAttribute('aria-valuenow', String(pct));
      }
      if (avisoOk) avisoOk.hidden = hechos < checksEco.length;
    };

    checksEco.forEach(function (cb) {
      var id = cb.getAttribute('data-eco-check');
      cb.checked = Boolean(estadoCheck[id]);
      cb.addEventListener('change', function () {
        estadoCheck[id] = cb.checked;
        try { localStorage.setItem(claveCheck, JSON.stringify(estadoCheck)); } catch (_) {}
        actualizarCheck();
      });
    });
    actualizarCheck();
  }

  // Botón Mostrar/Ocultar en campos de contraseña (registro e inicio de sesión).
  document.querySelectorAll('input[type="password"]').forEach(function (inp) {
    if (inp.parentElement && inp.parentElement.classList.contains('pw-wrap')) return;
    var wrap = document.createElement('div');
    wrap.className = 'pw-wrap';
    inp.parentNode.insertBefore(wrap, inp);
    wrap.appendChild(inp);
    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'pw-toggle';
    toggle.setAttribute('aria-label', 'Mostrar contraseña');
    toggle.textContent = 'Ver';
    toggle.addEventListener('click', function () {
      var esOculta = inp.type === 'password';
      inp.type = esOculta ? 'text' : 'password';
      toggle.textContent = esOculta ? 'Ocultar' : 'Ver';
      toggle.setAttribute('aria-label', esOculta ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
    wrap.appendChild(toggle);
  });

  // Medidor en tiempo real de seguridad de contraseña en /accounts/signup/.
  var medidor = document.getElementById('clave-medidor');
  var pw1 = document.getElementById('id_password1');
  var pw2 = document.getElementById('id_password2');
  var campoEmail = document.getElementById('id_email');
  var campoNombre = document.getElementById('id_nombre');
  if (medidor && pw1) {
    var fill = document.getElementById('clave-barra-fill');
    var nivelTxt = document.getElementById('clave-nivel');
    var coincideEl = document.getElementById('clave-coincide');
    var reglasEls = {
      largo: medidor.querySelector('[data-regla="largo"]'),
      minus: medidor.querySelector('[data-regla="minus"]'),
      mayus: medidor.querySelector('[data-regla="mayus"]'),
      num: medidor.querySelector('[data-regla="num"]'),
      esp: medidor.querySelector('[data-regla="esp"]'),
      personal: medidor.querySelector('[data-regla="personal"]')
    };

    var norm = function (s) {
      return (s || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    };
    var contienePersonal = function (val) {
      if (!val) return false;
      var low = norm(val);
      var partes = [];
      if (campoEmail && campoEmail.value) {
        var em = norm(campoEmail.value);
        if (em) partes.push(em);
        var loc = em.split('@')[0];
        if (loc && loc.length >= 3) partes.push(loc);
      }
      if (campoNombre && campoNombre.value) {
        norm(campoNombre.value).split(/[\s._-]+/).forEach(function (w) {
          if (w.length >= 3) partes.push(w);
        });
      }
      return partes.some(function (p) { return low.indexOf(p) !== -1; });
    };

    var evaluarCoincidencia = function () {
      if (!pw2 || !coincideEl) return;
      if (!pw2.value) { coincideEl.hidden = true; return; }
      coincideEl.hidden = false;
      if (pw1.value === pw2.value) {
        coincideEl.textContent = '✓ Las contraseñas coinciden';
        coincideEl.className = 'clave-coincide xs ok';
      } else {
        coincideEl.textContent = '✕ Las contraseñas aún no coinciden';
        coincideEl.className = 'clave-coincide xs mal';
      }
    };

    var evaluarClave = function () {
      var val = pw1.value || '';
      var checks = {
        largo: val.length > 8,
        minus: /[a-z]/.test(val),
        mayus: /[A-Z]/.test(val),
        num: /\d/.test(val),
        esp: /[^A-Za-z0-9\s]/.test(val),
        personal: val.length > 0 && !contienePersonal(val)
      };
      var cumplidas = 0;
      Object.keys(checks).forEach(function (k) {
        var ok = checks[k];
        if (ok) cumplidas++;
        var li = reglasEls[k];
        if (li) {
          li.classList.toggle('ok', ok);
          var sp = li.querySelector('span');
          if (sp) sp.textContent = ok ? '✓' : '○';
        }
      });
      var pct = val.length === 0 ? 0 : Math.round((cumplidas / 6) * 100);
      var clase = 'debil';
      var etiqueta = 'Sin escribir';
      if (val.length > 0) {
        if (cumplidas <= 2) { clase = 'debil'; etiqueta = 'Débil (' + pct + '%)'; }
        else if (cumplidas <= 4) { clase = 'media'; etiqueta = 'En progreso (' + pct + '%)'; }
        else if (cumplidas === 5) { clase = 'buena'; etiqueta = 'Casi lista (' + pct + '%)'; }
        else { clase = 'fuerte'; etiqueta = '¡Segura! (100%)'; }
      }
      if (fill) {
        fill.style.width = pct + '%';
        fill.className = 'nivel-' + clase;
        if (fill.parentElement) fill.parentElement.setAttribute('aria-valuenow', String(pct));
      }
      if (nivelTxt) {
        nivelTxt.textContent = etiqueta;
        nivelTxt.className = 'clave-nivel nivel-' + clase;
      }
      evaluarCoincidencia();
    };

    [pw1, campoEmail, campoNombre].forEach(function (el) {
      if (el) el.addEventListener('input', evaluarClave);
    });
    if (pw2) pw2.addEventListener('input', evaluarCoincidencia);
    evaluarClave();
  }

  // Detector automático de nueva versión publicada (/version.json) con botón «Actualizar ahora».
  var metaVer = document.querySelector('meta[name="app-version"]');
  var bannerUpd = document.getElementById('banner-actualizacion');
  var txtVerUpd = document.getElementById('update-ver-txt');
  var btnUpd = document.getElementById('btn-actualizar-app');
  if (metaVer && bannerUpd) {
    var verLocal = (metaVer.getAttribute('content') || '').trim();
    var revisarVersion = function () {
      fetch('/version.json?t=' + Date.now(), { cache: 'no-store', credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (d && d.version && d.version !== verLocal) {
            if (txtVerUpd) txtVerUpd.textContent = 'v' + d.version;
            bannerUpd.hidden = false;
          }
        })
        .catch(function () {});
    };
    if (btnUpd) {
      btnUpd.addEventListener('click', function () {
        var recargar = function () {
          var url = new URL(window.location.href);
          url.searchParams.set('v', String(Date.now()));
          window.location.replace(url.toString());
        };
        if (window.caches && caches.keys) {
          caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (k) { return caches.delete(k); }));
          }).finally(recargar);
        } else {
          recargar();
        }
      });
    }
    setTimeout(revisarVersion, 4000);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible') revisarVersion();
    });
    setInterval(revisarVersion, 120000);
  }

  // Asistente Experto Flotante «Escarlata · Consultor EcoParce» (100 % local y CSP-safe).
  var botFab = document.getElementById('ecobot-fab');
  var botPanel = document.getElementById('ecobot-panel');
  var botCerrar = document.getElementById('ecobot-cerrar');
  var botMsgs = document.getElementById('ecobot-msgs');
  var botForm = document.getElementById('ecobot-form');
  var botInput = document.getElementById('ecobot-input');
  if (botFab && botPanel && botMsgs && botForm && botInput) {
    var BASE_ECO = [
      { keys: ['pizza', 'grasa', 'servilleta', 'higienico', 'panal', 'colilla', 'icopor', 'aluminio sucio', 'papel carbon', 'tapabocas'],
        bolsa: 'Bolsa Negra (No aprovechables)',
        tip: 'Los residuos con grasa, higiene personal o contaminados no se pueden reciclar. Ciérralos bien en la bolsa negra.',
        link: '/guias/' },
      { keys: ['vidrio roto', 'espejo', 'ceramica', 'loza'],
        bolsa: 'Bolsa Negra (envuelto y marcado)',
        tip: 'Nunca pongas vidrio roto suelto en la bolsa blanca: envuélvelo en cartón o periódico marcado «Vidrio roto» y deposítalo en bolsa negra para proteger a los recicladores.',
        link: '/guias/' },
      { keys: ['pet', 'botella', 'plastico', 'lata', 'aluminio', 'carton', 'papel', 'cuaderno', 'vidrio', 'tetrapak', 'tetra', 'caja de leche', 'tapa', 'metal', 'frasco'],
        bolsa: 'Bolsa Blanca (Aprovechables)',
        tip: 'Vacíalo, enjuágalo rápido si tenía líquidos, déjalo escurrir/secar y aplástalo para ahorrar espacio.',
        link: '/escanear/' },
      { keys: ['cascara', 'fruta', 'verdura', 'comida', 'cafe', 'cuncho', 'huevo', 'organico', 'hoja', 'poda', 'compost'],
        bolsa: 'Bolsa Verde (Orgánicos aprovechables)',
        tip: 'Separa restos vegetales crudos, cáscaras y cuncho de café sin bolsas plásticas mezcladas para aprovecharlos como abono.',
        link: '/guias/' },
      { keys: ['aceite', 'pila', 'bateria', 'bombillo', 'led', 'medicamento', 'medicina', 'jarabe', 'celular', 'cargador', 'cable', 'raee', 'electronico', 'llanta', 'pintura', 'computador'],
        bolsa: 'Punto Posconsumo (Residuo especial)',
        tip: 'Jamás va en las bolsas comunes ni al desagüe. Guárdalo aparte (aceite frío en botella cerrada; pilas en frasco seco) y llévalo a un punto autorizado.',
        link: '/puntos/' },
      { keys: ['2184', 'resolucion', 'norma', 'colores', 'bolsa blanca', 'bolsa negra', 'bolsa verde'],
        bolsa: 'Resolución 2184 de 2019 (Colombia)',
        tip: 'Código unificado nacional: Blanca (aprovechables limpios y secos), Negra (no aprovechables) y Verde (orgánicos aprovechables). Los peligrosos van a Posconsumo.',
        link: '/guias/' }
    ];

    var normBot = function (s) {
      return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
    };

    var agregarMsg = function (texto, tipo, extraLink, extraLabel) {
      var div = document.createElement('div');
      div.className = 'ecobot-msg ' + tipo;
      div.textContent = texto;
      if (extraLink) {
        var br = document.createElement('br');
        var a = document.createElement('a');
        a.href = extraLink;
        a.className = 'ecobot-link';
        a.textContent = extraLabel || 'Ver más en EcoParce →';
        div.appendChild(br);
        div.appendChild(a);
      }
      botMsgs.appendChild(div);
      botMsgs.scrollTop = botMsgs.scrollHeight;
    };

    var responder = function (consulta) {
      var q = consulta.trim();
      if (!q) return;
      agregarMsg(q, 'user');
      var qn = normBot(q);
      var match = null;
      for (var i = 0; i < BASE_ECO.length; i++) {
        for (var j = 0; j < BASE_ECO[i].keys.length; j++) {
          if (qn.indexOf(BASE_ECO[i].keys[j]) !== -1) {
            match = BASE_ECO[i];
            break;
          }
        }
        if (match) break;
      }
      if (match) {
        agregarMsg(
          match.bolsa + ': ' + match.tip,
          'bot',
          match.link,
          match.link === '/puntos/' ? 'Abrir mapa de puntos Posconsumo →' : 'Ver guía oficial →'
        );
      } else {
        agregarMsg(
          'Puedo buscar «' + q + '» directamente en la base completa de residuos de EcoParce para darte la instrucción exacta.',
          'bot',
          '/buscar/?q=' + encodeURIComponent(q),
          'Buscar «' + q + '» en el buscador →'
        );
      }
    };

    var toggleBot = function (abrir) {
      var estado = typeof abrir === 'boolean' ? abrir : botPanel.hidden;
      botPanel.hidden = !estado;
      botFab.setAttribute('aria-expanded', String(estado));
      if (estado) botInput.focus();
    };

    botFab.addEventListener('click', function () { toggleBot(); });
    if (botCerrar) botCerrar.addEventListener('click', function () { toggleBot(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !botPanel.hidden) toggleBot(false);
    });
    botPanel.querySelectorAll('[data-ecobot-q]').forEach(function (chip) {
      chip.addEventListener('click', function () {
        responder(chip.getAttribute('data-ecobot-q') || '');
      });
    });
    botForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var val = botInput.value;
      botInput.value = '';
      responder(val);
    });
  }
})();
