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


def _partida(request):
    pid = request.session.get('partida_id')
    return PartidaTrivia.objects.filter(pk=pid).first() if pid else None


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
        'insignias': insignias,
        'total_obtenidas': sum(1 for i in insignias if i['obtenida']),
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
    return render(request, 'trivia/jugar.html', {
        'partida': partida, 'pregunta': pregunta, 'opciones': pregunta.opciones.all(), 'respuesta': respuesta,
        'numero': numero, 'avance': round(100 * (partida.respondidas if respuesta else numero - 1) / partida.total_preguntas),
        'ultima': partida.respondidas >= partida.total_preguntas,
        'nivel_info': info_nivel(partida.nivel),
        'racha': partida.racha_actual,
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
    return render(request, 'trivia/resultado.html', {
        'partida': partida,
        'mensaje': mensaje,
        'falladas': falladas,
        'nivel_info': nivel_info,
        'paso_de_nivel': paso_de_nivel,
        'nuevas_insignias': nuevas_insignias,
        'siguiente_nivel': siguiente_nivel,
    })
