from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, RestrictedError, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.permisos import panel_requerido

from .forms import GuiaForm, PuntoForm, ResiduoForm
from .models import EstadoContenido, FuentePunto, Guia, PuntoEntrega, Residuo

MODELOS = {'guias': (Guia, GuiaForm, 'guía'), 'residuos': (Residuo, ResiduoForm, 'residuo')}


def _modelo(tipo):
    if tipo not in MODELOS:
        raise PermissionDenied
    return MODELOS[tipo]


@panel_requerido
def lista(request):
    tipo = request.GET.get('tipo', 'guias')
    modelo, _, _ = _modelo(tipo)
    objetos = modelo.objects.select_related('autor', 'revisor', 'contenedor')
    estado = request.GET.get('estado', '')
    if estado in EstadoContenido.values:
        objetos = objetos.filter(estado=estado)
    q = request.GET.get('q', '').strip()
    if q:
        objetos = objetos.filter(Q(titulo__icontains=q) if modelo is Guia else (Q(nombre__icontains=q) | Q(sinonimos__icontains=q)))
    conteo = {e: modelo.objects.filter(estado=e).count() for e in EstadoContenido.values}
    return render(request, 'contenidos/panel/lista.html', {
        'tipo': tipo, 'objetos': objetos.order_by('-actualizado_en'), 'estado': estado, 'q': q,
        'estados': EstadoContenido.choices, 'conteo': conteo,
    })


@panel_requerido
def editar(request, tipo, pk=None):
    """Crear o editar. Solo se edita en Borrador; en los demás estados se muestran las acciones del flujo."""
    modelo, form_class, nombre = _modelo(tipo)
    obj = get_object_or_404(modelo, pk=pk) if pk else None
    editable = obj is None or obj.estado == EstadoContenido.BORRADOR
    inicial = {}
    if obj is None and tipo == 'residuos' and request.GET.get('nombre'):
        inicial['nombre'] = request.GET['nombre'][:100]
    form = form_class(request.POST or None, instance=obj, initial=inicial) if editable else None
    if request.method == 'POST' and editable and form.is_valid():
        nuevo = form.save(commit=False)
        if obj is None:
            nuevo.autor = request.user
        nuevo.save()
        form.save_m2m()
        if hasattr(form, 'cleaned_data') and 'puntos_entrega' in form.cleaned_data:
            nuevo.puntos.set(form.cleaned_data['puntos_entrega'] or [])
        RegistroAuditoria.registrar(request.user, Accion.CREAR if obj is None else Accion.EDITAR, nuevo, str(nuevo))
        if request.POST.get('enviar'):
            try:
                nuevo.enviar_a_revision(request.user)
                messages.success(request, 'Se guardó y se envió a revisión. Otro administrador debe aprobarla.')
            except ValidationError as e:
                messages.error(request, e.messages[0])
        else:
            messages.success(request, f'Se guardó el borrador de la {nombre}.' if tipo == 'guias' else 'Se guardó el borrador del residuo.')
        return redirect('panel_contenidos:editar', tipo=tipo, pk=nuevo.pk)
    historial = []
    if obj:
        historial = RegistroAuditoria.objects.filter(entidad=modelo._meta.db_table, entidad_id=obj.pk).select_related('usuario')[:20]
    ultima_devolucion = next((h for h in historial if h.accion == Accion.DEVOLVER), None) if obj and obj.estado == EstadoContenido.BORRADOR else None
    return render(request, 'contenidos/panel/editar.html', {
        'tipo': tipo, 'nombre': nombre, 'obj': obj, 'form': form, 'editable': editable,
        'historial': historial, 'devolucion': ultima_devolucion,
        'puede_revisar': obj is not None and request.user.puede_publicar(obj),
    })


@require_POST
@panel_requerido
def accion(request, tipo, pk, accion):
    """Transiciones del diagrama de estados, con auditoría en el modelo."""
    modelo, _, nombre = _modelo(tipo)
    obj = get_object_or_404(modelo, pk=pk)
    try:
        if accion == 'enviar':
            obj.enviar_a_revision(request.user)
            messages.success(request, 'Enviado a revisión.')
        elif accion == 'publicar':
            obj.publicar(request.user)
            messages.success(request, 'Publicado: ya es visible para el público.')
        elif accion == 'devolver':
            obj.devolver(request.user, request.POST.get('observaciones', ''))
            messages.success(request, 'Devuelto al autor con observaciones.')
        elif accion == 'retirar':
            obj.retirar(request.user)
            messages.success(request, 'Retirado: ya no es visible para el público.')
        elif accion == 'reabrir':
            obj.reabrir(request.user)
            messages.success(request, 'Reabierto como borrador para corregirlo.')
        elif accion == 'eliminar':
            if not request.user.es_admin_sistema():
                raise PermissionDenied('Solo el administrador del sistema elimina contenido (RN-09).')
            if obj.estado != EstadoContenido.RETIRADO:
                raise ValidationError('Solo se elimina contenido retirado.')
            texto = str(obj)
            RegistroAuditoria.registrar(request.user, Accion.ELIMINAR, obj, texto)
            obj.delete()
            messages.success(request, f'Se eliminó «{texto}».')
            return redirect(f"{_url_lista()}?tipo={tipo}")
        else:
            raise PermissionDenied
    except (ValidationError, PermissionDenied) as e:
        messages.error(request, e.messages[0] if isinstance(e, ValidationError) else (str(e) or 'Acción no permitida.'))
    except (RestrictedError, ProtectedError):
        messages.error(request, 'No se puede eliminar: hay códigos QR que apuntan a esta guía (RN-10). Desactívalos o cámbialos primero.')
    if accion == 'publicar' or accion == 'devolver':
        return redirect('panel_contenidos:revision')
    return redirect('panel_contenidos:editar', tipo=tipo, pk=pk)


def _url_lista():
    from django.urls import reverse
    return reverse('panel_contenidos:lista')


@panel_requerido
def revision(request):
    en_rev = EstadoContenido.EN_REVISION
    items = ([('guias', g) for g in Guia.objects.filter(estado=en_rev).select_related('autor')]
             + [('residuos', r) for r in Residuo.objects.filter(estado=en_rev).select_related('autor', 'contenedor')])
    items.sort(key=lambda x: x[1].actualizado_en)
    return render(request, 'contenidos/panel/revision.html', {
        'para_mi': [x for x in items if x[1].autor_id != request.user.pk],
        'mios': [x for x in items if x[1].autor_id == request.user.pk],
    })


@panel_requerido
def puntos(request):
    from django.core.paginator import Paginator
    lista = PuntoEntrega.objects.all()
    fuente = request.GET.get('fuente', '')
    if fuente in FuentePunto.values:
        lista = lista.filter(fuente=fuente)
    q = request.GET.get('q', '').strip()
    if q:
        lista = lista.filter(Q(nombre__icontains=q) | Q(direccion__icontains=q) | Q(localidad__icontains=q) | Q(recibe__icontains=q))
    pagina = Paginator(lista, 50).get_page(request.GET.get('p'))
    return render(request, 'contenidos/panel/puntos.html', {
        'pagina': pagina, 'fuente': fuente, 'q': q, 'fuentes': FuentePunto.choices,
        'oficiales': PuntoEntrega.objects.filter(fuente=FuentePunto.SDA, activo=True).count()})


@panel_requerido
def punto_editar(request, pk=None):
    obj = get_object_or_404(PuntoEntrega, pk=pk) if pk else None
    form = PuntoForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        p = form.save()
        RegistroAuditoria.registrar(request.user, Accion.CREAR if obj is None else Accion.EDITAR, p, str(p))
        messages.success(request, 'Se guardó el punto de entrega.')
        return redirect('panel_contenidos:puntos')
    return render(request, 'contenidos/panel/punto_form.html', {'form': form, 'obj': obj})
