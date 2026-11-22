from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.qr.models import CodigoQR

from .models import (
    ModoTrivia, OpcionTrivia, PartidaTrivia, PreguntaTrivia, RespuestaPartida,
    evaluar_insignias, info_nivel, obtener_insignias, progreso_niveles,
)

MENSAJES = [(5, '¡Vuelas alto, parce!'), (4, '¡Vuelas alto, parce!'), (3, '¡Muy bien, vas volando!'),
            (2, '¡Buen intento, sigue practicando!'), (0, '¡A repasar juntos, parce!')]

RETOS_DIARIOS = [
    {'titulo': 'Enjuaga y seca un envase hoy', 'detalle': 'Antes de llevar una botella PET o caja de leche a la bolsa blanca, enjuágala con poca agua y déjala escurrir.', 'bolsa': 'Bolsa Blanca'},
    {'titulo': 'Caza de pilas en casa', 'detalle': 'Revisa controles y cajones; guarda las pilas gastadas en un frasco seco para llevarlas a un punto Posconsumo.', 'bolsa': 'Posconsumo'},
    {'titulo': 'Aceite de cocina a la botella', 'detalle': 'Nunca viertas aceite usado al lavaplatos: déjalo enfriar y guárdalo en una botella plástica bien tapada.', 'bolsa': 'Posconsumo'},
    {'titulo': 'Aplasta el cartón y las botellas', 'detalle': 'Compacta cajas limpias y botellas PET secas para reducir espacio y facilitar el trabajo del reciclador.', 'bolsa': 'Bolsa Blanca'},
    {'titulo': 'Separa las cáscaras de hoy', 'detalle': 'Guarda cáscaras de frutas, verduras y cuncho de café en tu recipiente de orgánicos (bolsa verde).', 'bolsa': 'Bolsa Verde'},
    {'titulo': 'Revisa la caja de pizza', 'detalle': 'Si la tapa está limpia y sin grasa, recíclala en blanca; la parte manchada de grasa va en bolsa negra.', 'bolsa': 'Blanca / Negra'},
    {'titulo': 'Un vidrio seguro para todos', 'detalle': 'Si se rompe un vaso o frasco, envuélvelo en cartón o periódico marcado antes de botarlo en bolsa negra.', 'bolsa': 'Bolsa Negra'},
    {'titulo': 'Medicamentos vencidos al Punto Azul', 'detalle': 'Revisa tu botiquín y separa los medicamentos vencidos con sus empaques para llevarlos a un Punto Azul.', 'bolsa': 'Posconsumo'},
    {'titulo': 'Escanea 2 empaques de tu cocina', 'detalle': 'Usa el Escáner de EcoParce para identificar el número de resina (1 al 7) de dos productos de tu alacena.', 'bolsa': 'Escáner EcoParce'},
    {'titulo': 'Bolsa reutilizable lista', 'detalle': 'Deja una bolsa de tela cerca de la puerta o en tu morral para evitar bolsas plásticas de un solo uso hoy.', 'bolsa': 'Reducción'},
    {'titulo': 'Comparte un dato ambiental', 'detalle': 'Cuéntale a un familiar o amigo la diferencia entre la bolsa blanca, la negra y la verde en Colombia.', 'bolsa': 'Comunidad'},
    {'titulo': 'Cables y cargadores dañados aparte', 'detalle': 'Guarda audífonos, cables o celulares viejos en una caja seca para entregarlos como RAEE.', 'bolsa': 'Posconsumo'},
]


def _reto_del_dia():
    hoy = date.today()
    reto = RETOS_DIARIOS[hoy.toordinal() % len(RETOS_DIARIOS)]
    return {**reto, 'fecha': hoy.isoformat()}


def _partida(request):
    pid = request.session.get('partida_id')
    return PartidaTrivia.objects.filter(pk=pid).first() if pid else None


def _rango_jugador(puntos):
    if puntos >= 30:
        return {'nombre': 'Maestro Guacamaya', 'siguiente': None, 'pct': 100}
    if puntos >= 15:
        return {'nombre': 'Guardián del Bosque', 'siguiente': 30, 'pct': round(100 * (puntos - 15) / 15)}
    if puntos >= 6:
        return {'nombre': 'Brote Verde', 'siguiente': 15, 'pct': round(100 * (puntos - 6) / 9)}
    return {'nombre': 'Semilla Inicial', 'siguiente': 6, 'pct': round(100 * puntos / 6)}


def _ranking_top():
    from django.db.models import Count, Sum
    from apps.cuentas.models import Usuario
    filas = (
        Usuario.objects.filter(partidas__finalizada_en__isnull=False)
        .annotate(
            puntos=Sum('partidas__puntaje'),
            medallas=Count('insignias', distinct=True),
        )
        .filter(puntos__gt=0)
        .order_by('-puntos', '-medallas', 'nombre')[:8]
    )
    return [{'posicion': i + 1, 'nombre': u.nombre_corto, 'puntos': u.puntos or 0, 'medallas': u.medallas or 0, 'pk': u.pk}
            for i, u in enumerate(filas)]


def inicio(request):
    usuario = request.user if request.user.is_authenticated else None
    progreso = progreso_niveles(usuario=usuario, sesion=request.session)
    insignias = obtener_insignias(usuario=usuario, sesion=request.session)
    return render(request, 'trivia/inicio.html', {
        'hay_preguntas': PreguntaTrivia.objects.filter(activa=True).exists(),
        'partida': _partida(request),
        'niveles': progreso['niveles'],
        'partidas_totales': progreso['partidas_totales'],
        'puntos_totales': progreso['puntos_totales'],
        'rango': _rango_jugador(progreso['puntos_totales']),
        'ranking': _ranking_top() if usuario else [],
        'insignias': insignias,
        'total_obtenidas': sum(1 for i in insignias if i['obtenida']),
        'reto_diario': _reto_del_dia(),
    })


@require_POST
def nueva(request):
    qr = None
    if request.session.get('qr_origen'):
        qr = CodigoQR.objects.filter(pk=request.session.pop('qr_origen')).first()
    usuario = request.user if request.user.is_authenticated else None
    modo = request.POST.get('modo', ModoTrivia.NIVELES)
    if modo not in ModoTrivia.values:
        modo = ModoTrivia.NIVELES
    progreso = progreso_niveles(usuario=usuario, sesion=request.session)
    try:
        nivel = int(request.POST.get('nivel', '1'))
    except (TypeError, ValueError):
        nivel = 1
    if modo == ModoTrivia.NIVELES and (nivel not in (1, 2, 3) or not progreso['desbloqueados'].get(nivel, False)):
        messages.info(request, info_nivel(nivel)['requisito'] + '.')
        nivel = max(nv for nv, ok in progreso['desbloqueados'].items() if ok)
    try:
        partida = PartidaTrivia.nueva(codigo_qr=qr, usuario=usuario, nivel=nivel, modo=modo)
    except ValidationError:
        return redirect('trivia:inicio')
    request.session['partida_id'] = partida.pk
    return redirect('trivia:jugar')


def jugar(request):
    """RF-08: una pregunta a la vez; al responder se muestra la retroalimentación de Escarlata."""
    partida = _partida(request)
    if partida is None or partida.terminada:
        return redirect('trivia:inicio')
    if request.method == 'POST':
        pregunta = get_object_or_404(PreguntaTrivia, pk=request.POST.get('pregunta'))
        opcion = get_object_or_404(OpcionTrivia, pk=request.POST.get('opcion'), pregunta=pregunta)
        try:
            respuesta = partida.responder(pregunta, opcion)
        except ValidationError:
            return redirect('trivia:jugar')
        return redirect(f"{request.path}?r={respuesta.pk}")
    respuesta = None
    if request.GET.get('r', '').isdigit():
        respuesta = RespuestaPartida.objects.filter(pk=request.GET['r'], partida=partida).select_related('pregunta', 'opcion').first()
    if respuesta:
        pregunta = respuesta.pregunta
    else:
        pregunta = partida.siguiente_pregunta()
        if pregunta is None:
            return redirect('trivia:resultado')
    numero = partida.ids.index(pregunta.pk) + 1
    mapa_resp = {r.pregunta_id: r.es_correcta for r in partida.respuestas.all()}
    puntos_estado = []
    for pid in partida.ids:
        if pid in mapa_resp:
            puntos_estado.append('bien' if mapa_resp[pid] else 'mal')
        elif pid == pregunta.pk:
            puntos_estado.append('actual')
        else:
            puntos_estado.append('pendiente')
    return render(request, 'trivia/jugar.html', {
        'partida': partida, 'pregunta': pregunta, 'opciones': pregunta.opciones.all(), 'respuesta': respuesta,
        'numero': numero, 'avance': round(100 * (partida.respondidas if respuesta else numero - 1) / partida.total_preguntas),
        'ultima': partida.respondidas >= partida.total_preguntas,
        'nivel_info': info_nivel(partida.nivel),
        'racha': partida.racha_actual,
        'puntos_estado': puntos_estado,
    })


def resultado(request):
    partida = _partida(request)
    if partida is None:
        return redirect('trivia:inicio')
    if partida.respondidas < partida.total_preguntas:
        return redirect('trivia:jugar')
    puntaje = partida.finalizar()
    nuevas_insignias = evaluar_insignias(partida, sesion=request.session)
    usuario = request.user if request.user.is_authenticated else None
    progreso = progreso_niveles(usuario=usuario, sesion=request.session)
    nivel_info = info_nivel(partida.nivel)
    paso_de_nivel = (partida.modo == ModoTrivia.NIVELES) and (puntaje >= nivel_info['meta'])
    siguiente_nivel = None
    if partida.modo == ModoTrivia.NIVELES and partida.nivel < 3 and progreso['desbloqueados'].get(partida.nivel + 1):
        siguiente_nivel = info_nivel(partida.nivel + 1)
    mensaje = next(m for minimo, m in MENSAJES if puntaje >= minimo)
    falladas = partida.respuestas.filter(es_correcta=False).select_related('pregunta')
    insignias = obtener_insignias(usuario=usuario, sesion=request.session)
    return render(request, 'trivia/resultado.html', {
        'partida': partida,
        'mensaje': mensaje,
        'falladas': falladas,
        'nivel_info': nivel_info,
        'paso_de_nivel': paso_de_nivel,
        'nuevas_insignias': nuevas_insignias,
        'siguiente_nivel': siguiente_nivel,
        'rango': _rango_jugador(progreso['puntos_totales']),
        'puntos_totales': progreso['puntos_totales'],
        'total_obtenidas': sum(1 for i in insignias if i['obtenida']),
    })
