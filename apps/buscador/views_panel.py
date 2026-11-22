from django.contrib import messages
from urllib.parse import urlencode

from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.permisos import panel_requerido

from .models import EstadoSugerencia, Sugerencia


@panel_requerido
def sugerencias(request):
    estado = request.GET.get('estado', EstadoSugerencia.PENDIENTE)
    lista = Sugerencia.objects.select_related('atendida_por')
    if estado in EstadoSugerencia.values:
        lista = lista.filter(estado=estado)
    return render(request, 'buscador/panel/sugerencias.html', {
        'sugerencias': lista[:200], 'estado': estado, 'estados': EstadoSugerencia.choices})


@require_POST
@panel_requerido
def atender(request, pk):
    s = get_object_or_404(Sugerencia, pk=pk, estado=EstadoSugerencia.PENDIENTE)
    estado = EstadoSugerencia.DESCARTADA if request.POST.get('accion') == 'descartar' else EstadoSugerencia.ATENDIDA
    s.atender(request.user, estado)
    if request.POST.get('accion') == 'crear':
        return redirect(reverse('panel_contenidos:nuevo', args=['residuos']) + '?' + urlencode({'nombre': s.termino}))
    messages.success(request, f'Sugerencia «{s.termino}» marcada como {s.get_estado_display().lower()}.')
    return redirect('panel_buscador:sugerencias')
