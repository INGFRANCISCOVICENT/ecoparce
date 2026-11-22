/* EcoParce — Video educativo interactivo, Simulador Atrapa y Separa, Reto Diario y Certificado PNG.
   100 % local y compatible con CSP estricta (sin scripts en línea ni embeds externos). */
(function () {
  'use strict';

  /* =========================================================================
     1. VIDEO EDUCATIVO INTERACTIVO DE ESCARLATA (Canvas HD + Voz + Checkpoints)
     ========================================================================= */
  var player = document.getElementById('eco-video-player');
  if (player) {
    var canvas = player.querySelector('#eco-video-canvas');
    var ctx = canvas ? canvas.getContext('2d') : null;
    var btnPlay = player.querySelector('#ev-play');
    var btnPlayBig = player.querySelector('#ev-play-big');
    var btnRestart = player.querySelector('#ev-restart');
    var btnVoice = player.querySelector('#ev-voice');
    var btnCc = player.querySelector('#ev-cc');
    var progressWrap = player.querySelector('#ev-progress-wrap');
    var progressFill = player.querySelector('#ev-progress-fill');
    var timeLabel = player.querySelector('#ev-time');
    var captionEl = player.querySelector('#ev-caption');
    var chapterBtns = player.querySelectorAll('[data-ev-cap]');
    var checkpointBox = player.querySelector('#ev-checkpoint');
    var cpTitle = player.querySelector('#ev-cp-title');
    var cpOpts = player.querySelector('#ev-cp-opts');
    var cpFeedback = player.querySelector('#ev-cp-feedback');
    var cpContinue = player.querySelector('#ev-cp-continue');
    var cpBadge = player.querySelector('#ev-cp-score');

    var TOTAL = 60; // 60 segundos, 4 capítulos de 15 s
    var CAPITULOS = [
      {
        id: 0, start: 0, end: 15, nombre: '1. Bolsa Blanca',
        titulo: 'Bolsa Blanca · Aprovechables',
        subtitulo: 'Limpios, secos y listos para renacer',
        color: '#F8FAFC', acento: '#34D399', bolsaBg: '#E2E8F0', bolsaTxt: '#0F172A',
        items: ['Botella PET limpia', 'Cartón y papel', 'Vidrio intacto', 'Latas y Tetra Pak'],
        voz: 'Capítulo uno: Bolsa blanca para residuos aprovechables. Deposita plástico, vidrio, cartón, papel y metales, siempre limpios y secos.',
        subtitulos: [
          [0, 5, '¡Hola! Soy Escarlata. Aprende en 60 segundos el código de colores de Colombia.'],
          [5, 10, 'Bolsa BLANCA: plástico, vidrio, cartón, papel y latas limpias y secas.'],
          [10, 15, 'Truco pro: enjuaga y escurre tus envases para que no contaminen el cartón.']
        ],
        checkpoint: {
          at: 14.4,
          pregunta: 'Pausa interactiva 1/4: ¿Cómo debe ir una botella PET a la bolsa blanca?',
          opciones: [
            { t: 'Vacía, enjuagada y seca', ok: true },
            { t: 'Con líquido y mezclada con comida', ok: false },
            { t: 'En la bolsa verde', ok: false }
          ],
          tipOk: '¡Exacto! Limpia, seca y aplastada ahorra espacio y ayuda a los recicladores.',
          tipMal: 'Recuerda: la bolsa blanca recibe aprovechables limpios y secos para que sí se puedan reciclar.'
        }
      },
      {
        id: 1, start: 15, end: 30, nombre: '2. Bolsa Negra',
        titulo: 'Bolsa Negra · No aprovechables',
        subtitulo: 'Residuos con grasa, higiene o contaminados',
        color: '#94A3B8', acento: '#F59E0B', bolsaBg: '#1E293B', bolsaTxt: '#F8FAFC',
        items: ['Servilletas usadas', 'Caja de pizza con grasa', 'Papel higiénico', 'Icopor sucio'],
        voz: 'Capítulo dos: Bolsa negra para residuos no aprovechables, como servilletas usadas, papel higiénico, cartón con grasa e icopor contaminado.',
        subtitulos: [
          [15, 20, 'Bolsa NEGRA: todo lo que ya no puede reciclarse ni compostarse.'],
          [20, 25, 'Aquí van servilletas usadas, papel higiénico y cartón manchado de grasa.'],
          [25, 30, 'Si el cartón tiene grasa, ensucia el reciclaje limpio: mejor a la negra.']
        ],
        checkpoint: {
          at: 29.4,
          pregunta: 'Pausa interactiva 2/4: ¿Dónde va la parte manchada de grasa de una caja de pizza?',
          opciones: [
            { t: 'En la bolsa blanca', ok: false },
            { t: 'En la bolsa negra', ok: true },
            { t: 'En la bolsa verde', ok: false }
          ],
          tipOk: '¡Genial! La grasa daña las fibras de papel en el reciclaje; lo limpio sí va en blanca.',
          tipMal: 'El cartón con grasa no se puede reciclar: sepáralo en la bolsa negra.'
        }
      },
      {
        id: 2, start: 30, end: 45, nombre: '3. Bolsa Verde',
        titulo: 'Bolsa Verde · Orgánicos aprovechables',
        subtitulo: 'Nutrientes que vuelven a la tierra como abono',
        color: '#4ADE80', acento: '#22C55E', bolsaBg: '#15803D', bolsaTxt: '#F0FDF4',
        items: ['Cáscaras de fruta', 'Restos de comida cruda', 'Cuncho de café', 'Hojas y podas'],
        voz: 'Capítulo tres: Bolsa verde para residuos orgánicos aprovechables, como cáscaras de frutas, verduras, cuncho de café y restos de comida para compostaje.',
        subtitulos: [
          [30, 35, 'Bolsa VERDE: residuos orgánicos aprovechables que se convierten en abono.'],
          [35, 40, 'Incluye cáscaras de frutas y verduras, cuncho de café y restos agrícolas.'],
          [40, 45, 'Separarlos evita malos olores y reduce hasta la mitad la basura del hogar.']
        ],
        checkpoint: {
          at: 44.4,
          pregunta: 'Pausa interactiva 3/4: ¿Qué residuo pertenece a la bolsa verde?',
          opciones: [
            { t: 'Cáscaras de banano y cuncho de café', ok: true },
            { t: 'Bolsas plásticas rotas', ok: false },
            { t: 'Pilas descargadas', ok: false }
          ],
          tipOk: '¡Brillante! Esos orgánicos se transforman en compost nutritivo para las plantas.',
          tipMal: 'La bolsa verde es solo para orgánicos biodegradables como cáscaras y restos de comida.'
        }
      },
      {
        id: 3, start: 45, end: 60, nombre: '4. Posconsumo',
        titulo: 'Puntos Posconsumo · Especiales',
        subtitulo: 'Nunca los mezcles con la basura común',
        color: '#FCA5A5', acento: '#EF4444', bolsaBg: '#991B1B', bolsaTxt: '#FEF2F2',
        items: ['Pilas y baterías', 'Aceite usado en botella', 'Medicamentos vencidos', 'Bombillos y RAEE'],
        voz: 'Capítulo cuatro: Puntos Posconsumo. Pilas, bombillos, aceite de cocina usado, medicamentos vencidos y aparatos electrónicos nunca van en bolsas comunes; llévalos a un punto autorizado.',
        subtitulos: [
          [45, 50, '¡Atención! Hay residuos peligrosos o especiales que NO van en ninguna bolsa.'],
          [50, 55, 'Pilas, bombillos, aceite usado en botella cerrada, medicamentos y electrónicos.'],
          [55, 60, 'Ubica tu punto Posconsumo más cercano en EcoParce y protege nuestras fuentes de agua.']
        ],
        checkpoint: {
          at: 58.6,
          pregunta: 'Reto final 4/4: ¿Qué haces con el aceite de cocina usado?',
          opciones: [
            { t: 'Lo boto por el lavaplatos', ok: false },
            { t: 'Lo dejo enfriar, lo envaso en botella cerrada y lo llevo a Posconsumo', ok: true },
            { t: 'Lo mezclo con el cartón', ok: false }
          ],
          tipOk: '¡Nivel experto! Un solo litro de aceite puede contaminar miles de litros de agua.',
          tipMal: 'Jamás al desagüe: enfríalo, guárdalo en botella plástica bien cerrada y llévalo a un punto de acopio.'
        }
      }
    ];

    var escarlataImg = new Image();
    var escarlataReady = false;
    var imgUrl = player.getAttribute('data-escarlata');
    if (imgUrl) {
      escarlataImg.onload = function () { escarlataReady = true; drawFrame(); };
      escarlataImg.src = imgUrl;
    }

    var playing = false;
    var currentTime = 0;
    var lastTs = null;
    var voiceOn = true;
    var captionsOn = true;
    var spokenCap = -1;
    var answeredCps = {};
    var correctCps = 0;
    var activeCp = null;
    var particles = [];
    for (var i = 0; i < 28; i++) {
      particles.push({
        x: Math.random() * 960,
        y: Math.random() * 540,
        r: 1.5 + Math.random() * 3.5,
        vy: 0.25 + Math.random() * 0.55,
        a: 0.15 + Math.random() * 0.4
      });
    }

    function fmtTime(s) {
      var m = Math.floor(s / 60);
      var sec = Math.floor(s % 60);
      return m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    function getCap(t) {
      for (var c = 0; c < CAPITULOS.length; c++) {
        if (t >= CAPITULOS[c].start && t < CAPITULOS[c].end) return CAPITULOS[c];
      }
      return CAPITULOS[CAPITULOS.length - 1];
    }

    function speak(text) {
      if (!voiceOn || !('speechSynthesis' in window)) return;
      try {
        window.speechSynthesis.cancel();
        var u = new SpeechSynthesisUtterance(text);
        u.lang = 'es-CO';
        u.rate = 1.02;
        window.speechSynthesis.speak(u);
      } catch (_) {}
    }

    function stopVoice() {
      if ('speechSynthesis' in window) {
        try { window.speechSynthesis.cancel(); } catch (_) {}
      }
    }

    function roundRect(c, x, y, w, h, r) {
      c.beginPath();
      c.moveTo(x + r, y);
      c.arcTo(x + w, y, x + w, y + h, r);
      c.arcTo(x + w, y + h, x, y + h, r);
      c.arcTo(x, y + h, x, y, r);
      c.arcTo(x, y, x + w, y, r);
      c.closePath();
    }

    function drawFrame() {
      if (!ctx) return;
      var W = 960, H = 540;
      var cap = getCap(currentTime);
      var localT = Math.max(0, currentTime - cap.start);
      var pctCap = Math.min(1, localT / 15);

      // Fondo degradado esmeralda oscuro estilo aurora
      var bg = ctx.createLinearGradient(0, 0, W, H);
      bg.addColorStop(0, '#04120B');
      bg.addColorStop(0.55, '#082619');
      bg.addColorStop(1, '#04140C');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      // Resplandor radial dinámico del capítulo
      var glow = ctx.createRadialGradient(W * 0.72, H * 0.36, 20, W * 0.72, H * 0.36, 360);
      glow.addColorStop(0, cap.acento + '44');
      glow.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, W, H);

      // Partículas luminosas
      for (var p = 0; p < particles.length; p++) {
        var pt = particles[p];
        if (playing) {
          pt.y -= pt.vy;
          if (pt.y < -10) { pt.y = H + 10; pt.x = Math.random() * W; }
        }
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, pt.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(110, 231, 183, ' + pt.a + ')';
        ctx.fill();
      }

      // Etiqueta superior del capítulo
      roundRect(ctx, 44, 34, 240, 36, 18);
      ctx.fillStyle = 'rgba(255,255,255,0.09)';
      ctx.fill();
      ctx.strokeStyle = cap.acento;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.fillStyle = '#E2FBE9';
      ctx.font = '800 15px Nunito, system-ui, sans-serif';
      ctx.fillText('CAPÍTULO ' + (cap.id + 1) + ' DE 4 · RES. 2184', 64, 57);

      // Título y subtítulo del capítulo
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '800 36px Nunito, system-ui, sans-serif';
      ctx.fillText(cap.titulo, 44, 120);
      ctx.fillStyle = '#A7F3D0';
      ctx.font = '600 20px Nunito, system-ui, sans-serif';
      ctx.fillText(cap.subtitulo, 44, 152);

      // Lista animada de ejemplos que van apareciendo
      for (var j = 0; j < cap.items.length; j++) {
        var showAt = j * 2.2;
        var alpha = Math.max(0, Math.min(1, (localT - showAt) * 1.4));
        if (alpha <= 0.02) continue;
        var slideX = (1 - alpha) * -28;
        var iy = 192 + j * 60;
        ctx.save();
        ctx.globalAlpha = alpha;
        roundRect(ctx, 44 + slideX, iy, 380, 46, 14);
        ctx.fillStyle = 'rgba(255,255,255,0.08)';
        ctx.fill();
        ctx.strokeStyle = cap.acento + '88';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(72 + slideX, iy + 23, 9, 0, Math.PI * 2);
        ctx.fillStyle = cap.acento;
        ctx.fill();

        ctx.fillStyle = '#F8FAFC';
        ctx.font = '700 19px Nunito, system-ui, sans-serif';
        ctx.fillText(cap.items[j], 94 + slideX, iy + 30);
        ctx.restore();
      }

      // Contenedor / Bolsa 3D estilizada a la derecha
      var bx = 560, by = 188, bw = 220, bh = 240;
      var pulse = Math.sin(currentTime * 3.5) * 4;
      ctx.save();
      ctx.shadowColor = cap.acento;
      ctx.shadowBlur = 28;
      roundRect(ctx, bx, by + pulse, bw, bh, 26);
      ctx.fillStyle = cap.bolsaBg;
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = cap.acento;
      ctx.stroke();
      ctx.restore();

      // Tapa de la bolsa / contenedor
      roundRect(ctx, bx - 10, by - 18 + pulse, bw + 20, 28, 12);
      ctx.fillStyle = cap.acento;
      ctx.fill();

      // Etiqueta dentro del contenedor
      ctx.fillStyle = cap.bolsaTxt;
      ctx.font = '800 22px Nunito, system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(cap.nombre.replace(/^\d+\.\s*/, '').toUpperCase(), bx + bw / 2, by + 112 + pulse);
      ctx.font = '700 15px Nunito, system-ui, sans-serif';
      ctx.fillText('EcoParce · Colombia', bx + bw / 2, by + 144 + pulse);
      // Anillo de progreso del capítulo dentro de la bolsa
      ctx.beginPath();
      ctx.arc(bx + bw / 2, by + 194 + pulse, 24, -Math.PI / 2, -Math.PI / 2 + pctCap * Math.PI * 2);
      ctx.strokeStyle = cap.acento;
      ctx.lineWidth = 5;
      ctx.stroke();
      ctx.textAlign = 'left';

      // Escarlata volando sobre el contenedor
      if (escarlataReady) {
        var ex = 735 + Math.sin(currentTime * 1.6) * 14;
        var ey = 46 + Math.cos(currentTime * 2.4) * 10;
        ctx.drawImage(escarlataImg, ex, ey, 190, 190);
      }

      // Actualizar controles y subtítulos
      if (progressFill) progressFill.style.width = ((currentTime / TOTAL) * 100).toFixed(2) + '%';
      if (timeLabel) timeLabel.textContent = fmtTime(currentTime) + ' / ' + fmtTime(TOTAL);
      for (var k = 0; k < chapterBtns.length; k++) {
        chapterBtns[k].classList.toggle('activo', Number(chapterBtns[k].getAttribute('data-ev-cap')) === cap.id);
      }
      if (captionEl) {
        if (!captionsOn) {
          captionEl.hidden = true;
        } else {
          var textoSub = '';
          for (var s = 0; s < cap.subtitulos.length; s++) {
            if (currentTime >= cap.subtitulos[s][0] && currentTime <= cap.subtitulos[s][1]) {
              textoSub = cap.subtitulos[s][2];
              break;
            }
          }
          captionEl.hidden = !textoSub;
          captionEl.textContent = textoSub;
        }
      }
    }

    function openCheckpoint(cap) {
      activeCp = cap;
      playing = false;
      stopVoice();
      if (btnPlay) btnPlay.textContent = '▶ Reproducir';
      if (cpTitle) cpTitle.textContent = cap.checkpoint.pregunta;
      if (cpFeedback) { cpFeedback.hidden = true; cpFeedback.className = 'ev-cp-feedback'; }
      if (cpContinue) cpContinue.hidden = true;
      if (cpOpts) {
        cpOpts.innerHTML = '';
        cap.checkpoint.opciones.forEach(function (op) {
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'ev-cp-opt';
          b.textContent = op.t;
          b.addEventListener('click', function () {
            if (answeredCps[cap.id]) return;
            answeredCps[cap.id] = true;
            if (op.ok) {
              correctCps++;
              b.classList.add('ok');
              if (cpFeedback) {
                cpFeedback.textContent = '✓ ' + cap.checkpoint.tipOk;
                cpFeedback.className = 'ev-cp-feedback ok';
                cpFeedback.hidden = false;
              }
            } else {
              b.classList.add('mal');
              if (cpFeedback) {
                cpFeedback.textContent = '✕ ' + cap.checkpoint.tipMal;
                cpFeedback.className = 'ev-cp-feedback mal';
                cpFeedback.hidden = false;
              }
            }
            if (cpBadge) cpBadge.textContent = 'Retos del video: ' + correctCps + '/4';
            if (cpContinue) {
              cpContinue.textContent = cap.id === 3 ? '¡Video completado! Repetir' : 'Continuar video →';
              cpContinue.hidden = false;
            }
          });
          cpOpts.appendChild(b);
        });
      }
      if (checkpointBox) checkpointBox.hidden = false;
    }

    function tick(ts) {
      if (!playing) { lastTs = null; return; }
      if (lastTs === null) lastTs = ts;
      var dt = Math.min(0.1, (ts - lastTs) / 1000);
      lastTs = ts;
      currentTime += dt;

      var cap = getCap(currentTime);
      if (spokenCap !== cap.id) {
        spokenCap = cap.id;
        speak(cap.voz);
      }

      if (!answeredCps[cap.id] && currentTime >= cap.checkpoint.at) {
        currentTime = cap.checkpoint.at;
        drawFrame();
        openCheckpoint(cap);
        return;
      }

      if (currentTime >= TOTAL) {
        currentTime = TOTAL;
        playing = false;
        if (btnPlay) btnPlay.textContent = '↻ Ver de nuevo';
        if (btnPlayBig) btnPlayBig.hidden = false;
        drawFrame();
        return;
      }

      drawFrame();
      window.requestAnimationFrame(tick);
    }

    function startPlayback() {
      if (activeCp) return;
      if (currentTime >= TOTAL - 0.2) {
        currentTime = 0;
        spokenCap = -1;
      }
      playing = true;
      lastTs = null;
      if (btnPlayBig) btnPlayBig.hidden = true;
      if (btnPlay) btnPlay.textContent = '⏸ Pausar';
      var cap = getCap(currentTime);
      if (spokenCap !== cap.id) {
        spokenCap = cap.id;
        speak(cap.voz);
      }
      window.requestAnimationFrame(tick);
    }

    function pausePlayback() {
      playing = false;
      stopVoice();
      if (btnPlay) btnPlay.textContent = '▶ Reproducir';
    }

    if (btnPlay) {
      btnPlay.addEventListener('click', function () {
        if (playing) pausePlayback(); else startPlayback();
      });
    }
    if (btnPlayBig) {
      btnPlayBig.addEventListener('click', startPlayback);
    }
    if (btnRestart) {
      btnRestart.addEventListener('click', function () {
        activeCp = null;
        if (checkpointBox) checkpointBox.hidden = true;
        currentTime = 0;
        spokenCap = -1;
        answeredCps = {};
        correctCps = 0;
        if (cpBadge) cpBadge.textContent = 'Retos del video: 0/4';
        startPlayback();
      });
    }
    if (btnVoice) {
      btnVoice.addEventListener('click', function () {
        voiceOn = !voiceOn;
        btnVoice.textContent = voiceOn ? '🔊 Voz: ON' : '🔇 Voz: OFF';
        btnVoice.setAttribute('aria-pressed', String(voiceOn));
        if (!voiceOn) stopVoice();
        else if (playing) speak(getCap(currentTime).voz);
      });
    }
    if (btnCc) {
      btnCc.addEventListener('click', function () {
        captionsOn = !captionsOn;
        btnCc.setAttribute('aria-pressed', String(captionsOn));
        btnCc.classList.toggle('activo', captionsOn);
        drawFrame();
      });
    }
    if (progressWrap) {
      progressWrap.addEventListener('click', function (e) {
        var rect = progressWrap.getBoundingClientRect();
        var ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        activeCp = null;
        if (checkpointBox) checkpointBox.hidden = true;
        currentTime = ratio * TOTAL;
        spokenCap = -1;
        drawFrame();
        if (playing) speak(getCap(currentTime).voz);
      });
    }
    chapterBtns.forEach(function (b) {
      b.addEventListener('click', function () {
        var idx = Number(b.getAttribute('data-ev-cap'));
        if (CAPITULOS[idx]) {
          activeCp = null;
          if (checkpointBox) checkpointBox.hidden = true;
          currentTime = CAPITULOS[idx].start;
          spokenCap = -1;
          drawFrame();
          startPlayback();
        }
      });
    });
    if (cpContinue) {
      cpContinue.addEventListener('click', function () {
        var finished = activeCp && activeCp.id === 3;
        activeCp = null;
        if (checkpointBox) checkpointBox.hidden = true;
        if (finished) {
          currentTime = 0;
          spokenCap = -1;
          answeredCps = {};
          correctCps = 0;
          if (cpBadge) cpBadge.textContent = 'Retos del video: 0/4';
        } else {
          currentTime = Math.min(TOTAL, currentTime + 0.7);
        }
        startPlayback();
      });
    }

    drawFrame();
  }

  /* =========================================================================
     2. SIMULADOR ARCADE «ATRAPA Y SEPARA 30 s» (Mini-juego interactivo)
     ========================================================================= */
  var arcade = document.getElementById('eco-arcade');
  if (arcade) {
    var ITEMS = [
      { n: 'Botella PET limpia y seca', b: 'BLANCA', tip: 'Plástico limpio y seco va en la bolsa blanca.' },
      { n: 'Caja de pizza con grasa', b: 'NEGRA', tip: 'El cartón engrasado no se recicla: va en bolsa negra.' },
      { n: 'Cáscara de banano', b: 'VERDE', tip: 'Restos vegetales y frutas van en la bolsa verde.' },
      { n: 'Pila AA descargada', b: 'POSCONSUMO', tip: 'Las pilas tienen metales pesados: llévalas a Posconsumo.' },
      { n: 'Lata de aluminio enjuagada', b: 'BLANCA', tip: 'Los metales limpios son 100 % aprovechables (blanca).' },
      { n: 'Servilleta usada', b: 'NEGRA', tip: 'El papel higiénico y servilletas usadas van en negra.' },
      { n: 'Cuncho de café', b: 'VERDE', tip: 'El cuncho de café es excelente abono: bolsa verde.' },
      { n: 'Aceite de cocina usado', b: 'POSCONSUMO', tip: 'Enfríalo en botella cerrada y llévalo a un punto de acopio.' },
      { n: 'Caja de leche (Tetra Pak) limpia', b: 'BLANCA', tip: 'Enjuagada, escurrida y aplastada va en bolsa blanca.' },
      { n: 'Bombillo ahorrador dañado', b: 'POSCONSUMO', tip: 'Contiene trazas de mercurio: entrega en punto Posconsumo.' },
      { n: 'Icopor manchado de comida', b: 'NEGRA', tip: 'El icopor sucio va en la bolsa negra.' },
      { n: 'Restos de verduras crudas', b: 'VERDE', tip: 'Los residuos vegetales crudos van en bolsa verde.' }
    ];

    var btnStart = arcade.querySelector('#arc-start');
    var scoreEl = arcade.querySelector('#arc-score');
    var comboEl = arcade.querySelector('#arc-combo');
    var timerEl = arcade.querySelector('#arc-timer');
    var bestEl = arcade.querySelector('#arc-best');
    var itemEl = arcade.querySelector('#arc-item');
    var tipEl = arcade.querySelector('#arc-tip');
    var binBtns = arcade.querySelectorAll('[data-arc-bin]');

    var running = false;
    var score = 0;
    var combo = 1;
    var timeLeft = 30;
    var currentItem = null;
    var interval = null;
    var best = Number(localStorage.getItem('ecoparce_arcade_best') || '0');
    if (bestEl) bestEl.textContent = String(best);

    function nextItem() {
      var idx = Math.floor(Math.random() * ITEMS.length);
      currentItem = ITEMS[idx];
      if (itemEl) {
        itemEl.textContent = currentItem.n;
        itemEl.classList.remove('pop');
        void itemEl.offsetWidth;
        itemEl.classList.add('pop');
      }
    }

    function finishGame() {
      running = false;
      clearInterval(interval);
      if (score > best) {
        best = score;
        localStorage.setItem('ecoparce_arcade_best', String(best));
        if (bestEl) bestEl.textContent = String(best);
      }
      if (itemEl) itemEl.textContent = '¡Tiempo! Puntaje final: ' + score + ' pts';
      if (tipEl) {
        tipEl.textContent = score >= 120
          ? '¡Increíble reflejo ambiental! Superaste el nivel experto.'
          : '¡Buen entrenamiento! Vuelve a intentarlo para romper tu récord.';
        tipEl.className = 'arcade-tip ok';
      }
      if (btnStart) btnStart.textContent = '↻ Jugar otros 30 s';
      binBtns.forEach(function (b) { b.disabled = true; });
    }

    function startGame() {
      running = true;
      score = 0;
      combo = 1;
      timeLeft = 30;
      if (scoreEl) scoreEl.textContent = '0';
      if (comboEl) comboEl.textContent = 'x1';
      if (timerEl) timerEl.textContent = '30 s';
      if (tipEl) { tipEl.textContent = 'Toca la bolsa correcta (o teclas 1, 2, 3, 4).'; tipEl.className = 'arcade-tip'; }
      if (btnStart) btnStart.textContent = 'Reiniciar';
      binBtns.forEach(function (b) { b.disabled = false; });
      nextItem();
      clearInterval(interval);
      interval = setInterval(function () {
        timeLeft--;
        if (timerEl) timerEl.textContent = timeLeft + ' s';
        if (timeLeft <= 0) finishGame();
      }, 1000);
    }

    function chooseBin(bin) {
      if (!running || !currentItem) return;
      if (bin === currentItem.b) {
        score += 10 * combo;
        combo = Math.min(4, combo + 1);
        if (tipEl) { tipEl.textContent = '✓ ¡Correcto! +' + (10 * (combo - 1 || 1)) + ' pts · ' + currentItem.tip; tipEl.className = 'arcade-tip ok'; }
      } else {
        combo = 1;
        if (tipEl) { tipEl.textContent = '✕ Era ' + currentItem.b + ': ' + currentItem.tip; tipEl.className = 'arcade-tip mal'; }
      }
      if (scoreEl) scoreEl.textContent = String(score);
      if (comboEl) comboEl.textContent = 'x' + combo;
      nextItem();
    }

    if (btnStart) btnStart.addEventListener('click', startGame);
    binBtns.forEach(function (b) {
      b.disabled = true;
      b.addEventListener('click', function () { chooseBin(b.getAttribute('data-arc-bin')); });
    });
    document.addEventListener('keydown', function (e) {
      if (!running) return;
      var map = { '1': 'BLANCA', '2': 'NEGRA', '3': 'VERDE', '4': 'POSCONSUMO' };
      if (map[e.key]) { e.preventDefault(); chooseBin(map[e.key]); }
    });
  }

  /* =========================================================================
     3. RETO DIARIO ECOLÓGICO CON RACHA (localStorage por fecha)
     ========================================================================= */
  var retoBtn = document.getElementById('reto-diario-btn');
  if (retoBtn) {
    var fechaHoy = retoBtn.getAttribute('data-fecha');
    var rachaEl = document.getElementById('reto-diario-racha');
    var estadoEl = document.getElementById('reto-diario-estado');

    function leerRetos() {
      try { return JSON.parse(localStorage.getItem('ecoparce_retos_dias') || '[]'); }
      catch (_) { return []; }
    }

    function calcularRacha(dias) {
      var set = new Set(dias);
      var count = 0;
      var d = new Date(fechaHoy + 'T12:00:00');
      while (set.has(d.toISOString().slice(0, 10))) {
        count++;
        d.setDate(d.getDate() - 1);
      }
      return count;
    }

    function pintarReto() {
      var dias = leerRetos();
      var hecho = dias.indexOf(fechaHoy) !== -1;
      var racha = calcularRacha(dias);
      if (rachaEl) rachaEl.textContent = '🔥 Racha: ' + racha + (racha === 1 ? ' día' : ' días');
      if (hecho) {
        retoBtn.textContent = '✓ ¡Reto de hoy cumplido!';
        retoBtn.disabled = true;
        if (estadoEl) estadoEl.hidden = false;
      }
    }

    retoBtn.addEventListener('click', function () {
      var dias = leerRetos();
      if (dias.indexOf(fechaHoy) === -1) {
        dias.push(fechaHoy);
        localStorage.setItem('ecoparce_retos_dias', JSON.stringify(dias.slice(-60)));
      }
      pintarReto();
    });
    pintarReto();
  }

  /* =========================================================================
     4. GENERADOR DE CERTIFICADO DIGITAL AMBIENTAL EN PNG (1200x750 HD)
     ========================================================================= */
  document.querySelectorAll('[data-generar-certificado]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var nombre = btn.getAttribute('data-nombre') || 'Guardián EcoParce';
      var rango = btn.getAttribute('data-rango') || 'Semilla Inicial';
      var puntos = btn.getAttribute('data-puntos') || '0';
      var medallas = btn.getAttribute('data-medallas') || '0';
      var logoSrc = btn.getAttribute('data-logo') || '';

      var c = document.createElement('canvas');
      c.width = 1200;
      c.height = 750;
      var g = c.getContext('2d');

      function renderAndDownload(logoImg) {
        // Fondo esmeralda luminoso
        var bg = g.createLinearGradient(0, 0, 1200, 750);
        bg.addColorStop(0, '#04140C');
        bg.addColorStop(0.5, '#0A2E1D');
        bg.addColorStop(1, '#04140C');
        g.fillStyle = bg;
        g.fillRect(0, 0, 1200, 750);

        var glow = g.createRadialGradient(600, 260, 40, 600, 260, 520);
        glow.addColorStop(0, 'rgba(52,211,153,0.28)');
        glow.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = glow;
        g.fillRect(0, 0, 1200, 750);

        // Marco doble dorado-esmeralda
        g.strokeStyle = '#34D399';
        g.lineWidth = 6;
        g.strokeRect(28, 28, 1144, 694);
        g.strokeStyle = 'rgba(253,224,71,0.65)';
        g.lineWidth = 2;
        g.strokeRect(44, 44, 1112, 662);

        if (logoImg) {
          g.save();
          g.beginPath();
          g.arc(600, 130, 56, 0, Math.PI * 2);
          g.closePath();
          g.clip();
          g.drawImage(logoImg, 544, 74, 112, 112);
          g.restore();
          g.beginPath();
          g.arc(600, 130, 58, 0, Math.PI * 2);
          g.strokeStyle = '#FDE047';
          g.lineWidth = 4;
          g.stroke();
        }

        g.textAlign = 'center';
        g.fillStyle = '#86EFAC';
        g.font = '800 20px Nunito, system-ui, sans-serif';
        g.fillText('ECOPARCE · RECONOCIMIENTO AMBIENTAL COLOMBIA', 600, 228);

        g.fillStyle = '#FFFFFF';
        g.font = '800 48px Nunito, system-ui, sans-serif';
        g.fillText('Certificado de Guardián Ambiental', 600, 290);

        g.fillStyle = '#CBD5E1';
        g.font = '600 22px Nunito, system-ui, sans-serif';
        g.fillText('Otorgado con orgullo a', 600, 344);

        g.fillStyle = '#FDE047';
        g.font = '800 52px Nunito, system-ui, sans-serif';
        g.fillText(nombre, 600, 412);

        g.fillStyle = '#E2FBE9';
        g.font = '600 23px Nunito, system-ui, sans-serif';
        g.fillText('Por su compromiso con la separación en la fuente (Resolución 2184 de 2019)', 600, 468);

        // 3 insignias de estadísticas
        var cajas = [
          { k: 'RANGO ACTUAL', v: rango, x: 270 },
          { k: 'PUNTOS TRIVIA', v: puntos + ' pts', x: 600 },
          { k: 'MEDALLAS 3D', v: medallas + ' / 6', x: 930 }
        ];
        cajas.forEach(function (cx) {
          g.fillStyle = 'rgba(255,255,255,0.08)';
          g.fillRect(cx.x - 135, 506, 270, 92);
          g.strokeStyle = 'rgba(52,211,153,0.5)';
          g.lineWidth = 2;
          g.strokeRect(cx.x - 135, 506, 270, 92);
          g.fillStyle = '#A7F3D0';
          g.font = '800 14px Nunito, system-ui, sans-serif';
          g.fillText(cx.k, cx.x, 536);
          g.fillStyle = '#FFFFFF';
          g.font = '800 26px Nunito, system-ui, sans-serif';
          g.fillText(cx.v, cx.x, 576);
        });

        var hoy = new Date().toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
        g.fillStyle = '#94A3B8';
        g.font = '600 18px Nunito, system-ui, sans-serif';
        g.fillText('Emitido el ' + hoy + ' · https://ecoparce.onrender.com', 600, 668);

        var enlace = document.createElement('a');
        enlace.download = 'certificado-ecoparce.png';
        enlace.href = c.toDataURL('image/png');
        enlace.click();
      }

      if (logoSrc) {
        var img = new Image();
        img.onload = function () { renderAndDownload(img); };
        img.onerror = function () { renderAndDownload(null); };
        img.src = logoSrc;
      } else {
        renderAndDownload(null);
      }
    });
  });
})();
