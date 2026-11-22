from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.permisos import panel_requerido

from .forms import OpcionesForm, PreguntaForm
from .models import PreguntaTrivia


@panel_requerido
def lista(request):
    return render(request, 'trivia/panel/lista.html', {
        'preguntas': PreguntaTrivia.objects.select_related('autor').prefetch_related('opciones'),
        'activas': PreguntaTrivia.objects.filter(activa=True).count(),
    })


@panel_requerido
def editar(request, pk=None):
    """RF-09: crear o editar una pregunta con sus opciones."""
    pregunta = get_object_or_404(PreguntaTrivia, pk=pk) if pk else None
    form = PreguntaForm(request.POST or None, instance=pregunta)
    opciones = OpcionesForm(request.POST or None, pregunta=pregunta)
    if request.method == 'POST' and form.is_valid() and opciones.is_valid():
        with transaction.atomic():
            p = form.save(commit=False)
            if pregunta is None:
                p.autor = request.user
            p.save()
            opciones.guardar(p)
            if request.POST.get('activar'):
                p.activa = p.validar()
                p.save(update_fields=['activa'])
        RegistroAuditoria.registrar(request.user, Accion.CREAR if pregunta is None else Accion.EDITAR, p, p.enunciado[:120])
        messages.success(request, 'Se guardó la pregunta' + (' y quedó activa en la trivia.' if p.activa else '.'))
        return redirect('panel_trivia:lista')
    return render(request, 'trivia/panel/editar.html', {'form': form, 'opciones': opciones, 'pregunta': pregunta})


@require_POST
@panel_requerido
def activar(request, pk):
    p = get_object_or_404(PreguntaTrivia, pk=pk)
    if not p.activa and not p.validar():
        messages.error(request, 'No se puede activar: ' + ' '.join(p.errores()))
    else:
        p.activa = not p.activa
        p.save(update_fields=['activa'])
        RegistroAuditoria.registrar(request.user, Accion.ACTIVAR if p.activa else Accion.DESACTIVAR, p, p.enunciado[:120])
        messages.success(request, 'Pregunta activada.' if p.activa else 'Pregunta desactivada: ya no saldrá en la trivia.')
    return redirect('panel_trivia:lista')
