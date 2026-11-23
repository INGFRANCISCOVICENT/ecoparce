/* EcoParce — Generador interactivo de Carteles y Etiquetas HD para Canecas (Res. 2184).
   100 % local en Canvas HTML5, compatible con CSP estricta y listo para imprimir. */
(function () {
  'use strict';

  var box = document.getElementById('eco-cartel-gen');
  if (!box) return;

  var canvas = document.getElementById('cartel-canvas');
  var ctx = canvas ? canvas.getContext('2d') : null;
  var inpTitulo = document.getElementById('cartel-titulo');
  var selTipo = document.getElementById('cartel-tipo');
  var btnDesc = document.getElementById('cartel-descargar');
  var logoSrc = box.getAttribute('data-logo') || '';
  if (!ctx) return;

  var logoImg = null;
  if (logoSrc) {
    var img = new Image();
    img.onload = function () { logoImg = img; dibujar(); };
    img.src = logoSrc;
  }

  var PLANTILLAS = {
    BLANCA: {
      titulo: 'BOLSA BLANCA',
      sub: 'RESIDUOS APROVECHABLES',
      bg1: '#F8FAFC', bg2: '#E2E8F0', borde: '#16A34A', txt: '#0F172A', subTxt: '#15803D',
      si: ['Botellas PET limpias y secas', 'Cartón y papel sin grasa', 'Vidrio intacto y frascos', 'Latas y cajas Tetra Pak enjuagadas'],
      no: 'NO poner servilletas usadas, comida ni cartón con grasa.'
    },
    NEGRA: {
      titulo: 'BOLSA NEGRA',
      sub: 'RESIDUOS NO APROVECHABLES',
      bg1: '#1E293B', bg2: '#0F172A', borde: '#94A3B8', txt: '#FFFFFF', subTxt: '#CBD5E1',
      si: ['Servilletas y papel higiénico', 'Cajas de pizza o cartón con grasa', 'Icopor sucio y empaques metalizados', 'Vidrio roto envuelto y marcado'],
      no: 'NO mezclar reciclables limpios ni pilas o aceite.'
    },
    VERDE: {
      titulo: 'BOLSA VERDE',
      sub: 'ORGÁNICOS APROVECHABLES',
      bg1: '#166534', bg2: '#14532D', borde: '#4ADE80', txt: '#FFFFFF', subTxt: '#BBF7D0',
      si: ['Cáscaras de frutas y verduras', 'Restos de comida cruda', 'Cuncho de café y bolsas de té', 'Hojas secas y restos de poda'],
      no: 'NO mezclar plásticos, vidrio ni aceite de cocina.'
    }
  };

  function rr(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  function dibujarCompleto(lugar) {
    var W = 900, H = 1200;
    canvas.width = W;
    canvas.height = H;

    var bg = ctx.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, '#05160E');
    bg.addColorStop(0.5, '#092B1B');
    bg.addColorStop(1, '#04120B');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = '#34D399';
    ctx.lineWidth = 8;
    rr(ctx, 24, 24, W - 48, H - 48, 28);
    ctx.stroke();

    if (logoImg) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(104, 108, 42, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(logoImg, 62, 66, 84, 84);
      ctx.restore();
    }

    ctx.fillStyle = '#86EFAC';
    ctx.font = '800 18px Nunito, system-ui, sans-serif';
    ctx.fillText('ECOPARCE · RESOLUCIÓN 2184 DE 2019 (COLOMBIA)', 166, 92);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '800 36px Nunito, system-ui, sans-serif';
    ctx.fillText('Punto Ecológico · ' + lugar, 166, 136);

    var bloques = [
      { k: 'BLANCA', y: 186, bg: '#F8FAFC', b: '#CBD5E1', t: '#0F172A', s: '#15803D',
        tit: 'BOLSA BLANCA · Aprovechables',
        desc: 'Plástico, vidrio intacto, cartón, papel, latas y Tetra Pak — LIMPIOS Y SECOS.' },
      { k: 'NEGRA', y: 406, bg: '#1E293B', b: '#64748B', t: '#FFFFFF', s: '#CBD5E1',
        tit: 'BOLSA NEGRA · No aprovechables',
        desc: 'Servilletas usadas, papel higiénico, cartón con grasa, icopor sucio y vidrio roto envuelto.' },
      { k: 'VERDE', y: 626, bg: '#15803D', b: '#4ADE80', t: '#FFFFFF', s: '#DCFCE7',
        tit: 'BOLSA VERDE · Orgánicos aprovechables',
        desc: 'Cáscaras de frutas y verduras, restos de comida cruda, cuncho de café y restos de poda.' },
      { k: 'POS', y: 846, bg: '#991B1B', b: '#F87171', t: '#FFFFFF', s: '#FEE2E2',
        tit: 'PUNTOS POSCONSUMO · Residuos especiales',
        desc: 'Pilas, aceite usado en botella cerrada, bombillos, medicamentos vencidos y RAEE.' }
    ];

    bloques.forEach(function (bl) {
      rr(ctx, 56, bl.y, W - 112, 192, 22);
      ctx.fillStyle = bl.bg;
      ctx.fill();
      ctx.lineWidth = 4;
      ctx.strokeStyle = bl.b;
      ctx.stroke();

      ctx.fillStyle = bl.t;
      ctx.font = '800 30px Nunito, system-ui, sans-serif';
      ctx.fillText(bl.tit, 90, bl.y + 66);

      ctx.fillStyle = bl.s;
      ctx.font = '700 21px Nunito, system-ui, sans-serif';
      var palabras = bl.desc.split(' ');
      var linea = '', ly = bl.y + 114;
      for (var i = 0; i < palabras.length; i++) {
        var prueba = linea + palabras[i] + ' ';
        if (ctx.measureText(prueba).width > W - 180 && i > 0) {
          ctx.fillText(linea.trim(), 90, ly);
          linea = palabras[i] + ' ';
          ly += 30;
        } else {
          linea = prueba;
        }
      }
      ctx.fillText(linea.trim(), 90, ly);
    });

    ctx.textAlign = 'center';
    ctx.fillStyle = '#A7F3D0';
    ctx.font = '700 20px Nunito, system-ui, sans-serif';
    ctx.fillText('¿Dudas con algún residuo? Consulta gratis en https://ecoparce.onrender.com', W / 2, 1112);
    ctx.fillStyle = '#94A3B8';
    ctx.font = '600 16px Nunito, system-ui, sans-serif';
    ctx.fillText('EcoParce · Francisco Navarro, Danixa Herrera y Darien García', W / 2, 1146);
    ctx.textAlign = 'left';
  }

  function dibujarEtiqueta(tipo, lugar) {
    var p = PLANTILLAS[tipo];
    var W = 900, H = 900;
    canvas.width = W;
    canvas.height = H;

    var bg = ctx.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, p.bg1);
    bg.addColorStop(1, p.bg2);
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = p.borde;
    ctx.lineWidth = 14;
    rr(ctx, 26, 26, W - 52, H - 52, 34);
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.fillStyle = p.subTxt;
    ctx.font = '800 24px Nunito, system-ui, sans-serif';
    ctx.fillText(lugar.toUpperCase() + ' · ECOPARCE', W / 2, 108);

    ctx.fillStyle = p.txt;
    ctx.font = '900 72px Nunito, system-ui, sans-serif';
    ctx.fillText(p.titulo, W / 2, 206);

    ctx.fillStyle = p.subTxt;
    ctx.font = '800 28px Nunito, system-ui, sans-serif';
    ctx.fillText(p.sub, W / 2, 258);

    ctx.textAlign = 'left';
    p.si.forEach(function (item, idx) {
      var y = 328 + idx * 84;
      rr(ctx, 84, y, W - 168, 66, 18);
      ctx.fillStyle = tipo === 'BLANCA' ? 'rgba(22,163,74,0.12)' : 'rgba(255,255,255,0.12)';
      ctx.fill();
      ctx.fillStyle = p.txt;
      ctx.font = '800 26px Nunito, system-ui, sans-serif';
      ctx.fillText('✓  ' + item, 114, y + 42);
    });

    ctx.textAlign = 'center';
    rr(ctx, 84, 686, W - 168, 76, 18);
    ctx.fillStyle = 'rgba(220,38,38,0.16)';
    ctx.fill();
    ctx.fillStyle = tipo === 'BLANCA' ? '#991B1B' : '#FECACA';
    ctx.font = '800 22px Nunito, system-ui, sans-serif';
    ctx.fillText('✕  ' + p.no, W / 2, 732);

    ctx.fillStyle = p.subTxt;
    ctx.font = '700 18px Nunito, system-ui, sans-serif';
    ctx.fillText('Resolución 2184 de 2019 · https://ecoparce.onrender.com', W / 2, 828);
    ctx.textAlign = 'left';
  }

  function dibujar() {
    var lugar = (inpTitulo && inpTitulo.value.trim()) ? inpTitulo.value.trim().slice(0, 32) : 'Nuestro Hogar';
    var tipo = selTipo ? selTipo.value : 'COMPLETO';
    if (tipo === 'COMPLETO') dibujarCompleto(lugar);
    else dibujarEtiqueta(tipo, lugar);
  }

  if (inpTitulo) inpTitulo.addEventListener('input', dibujar);
  if (selTipo) selTipo.addEventListener('change', dibujar);
  if (btnDesc) {
    btnDesc.addEventListener('click', function () {
      var tipo = (selTipo ? selTipo.value : 'COMPLETO').toLowerCase();
      var a = document.createElement('a');
      a.download = 'ecoparce-caneca-' + tipo + '.png';
      a.href = canvas.toDataURL('image/png');
      a.click();
    });
  }

  dibujar();
})();
