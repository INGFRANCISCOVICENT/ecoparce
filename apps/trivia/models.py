import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

NIVELES = [
    {
        'numero': 1,
        'nombre': 'Semilla Verde',
        'dificultad_etiqueta': 'Fácil',
        'meta': 3,
        'subtitulo': 'Básico · Las 3 bolsas de Colombia (superas con 3/5 pts)',
        'icono': 'leaf',
        'requisito': 'Disponible desde el inicio',
    },
    {
        'numero': 2,
        'nombre': 'Guardián del Reciclaje',
        'dificultad_etiqueta': 'Media',
        'meta': 4,
        'subtitulo': 'Intermedio · Preparación y normativa (superas con 4/5 pts)',
        'icono': 'shield',
        'requisito': 'Logra al menos 3 puntos en el Nivel 1',
    },
    {
        'numero': 3,
        'nombre': 'Maestro Guacamaya',
        'dificultad_etiqueta': 'Difícil',
        'meta': 5,
        'subtitulo': 'Avanzado · Residuos especiales y casos complejos (dominas con 5/5 pts)',
        'icono': 'star',
        'requisito': 'Logra al menos 4 puntos en el Nivel 2',
    },
]

NIVELES_CHOICES = [(n['numero'], f"Nivel {n['numero']} · {n['nombre']}") for n in NIVELES]

INSIGNIAS = [
    {
        'codigo': 'primera_semilla',
        'nombre': 'Semilla Verde',
        'descripcion': 'Alcanza 3 puntos acumulados en la trivia.',
        'icono': 'leaf',
        'color': '#1E7A46',
        'fondo': '#E8F3EC',
    },
    {
        'codigo': 'explorador_bolsas',
        'nombre': 'Explorador de Bolsas',
        'descripcion': 'Consigue 3 o más puntos en el Nivel 1 (Fácil).',
        'icono': 'check',
        'color': '#14532D',
        'fondo': '#DDF0E4',
    },
    {
        'codigo': 'guardian_reciclaje',
        'nombre': 'Guardián del Reciclaje',
        'descripcion': 'Consigue 4 o más puntos en el Nivel 2 (Media).',
        'icono': 'shield',
        'color': '#1F4FA3',
        'fondo': '#E6EEF9',
    },
    {
        'codigo': 'maestro_guacamaya',
        'nombre': 'Maestro Guacamaya',
        'descripcion': 'Consigue 5 de 5 puntos en el Nivel 3 (Difícil).',
        'icono': 'star',
        'color': '#8A6200',
        'fondo': '#FFF6D6',
    },
    {
        'codigo': 'vuelo_perfecto',
        'nombre': 'Vuelo Perfecto',
        'descripcion': 'Logra 5 de 5 puntos en cualquier nivel.',
        'icono': 'game',
        'color': '#8E1414',
        'fondo': '#FBE9E7',
    },
    {
        'codigo': 'constancia_verde',
        'nombre': 'Parce Constante',
        'descripcion': 'Acumula 12 o más puntos totales en tus partidas.',
        'icono': 'refresh',
        'color': '#1E7A46',
        'fondo': '#E8F3EC',
    },
]

INSIGNIAS_POR_CODIGO = {i['codigo']: i for i in INSIGNIAS}
INSIGNIAS_CHOICES = [(i['codigo'], i['nombre']) for i in INSIGNIAS]


def info_nivel(numero):
    return next((n for n in NIVELES if n['numero'] == numero), NIVELES[0])


class CategoriaTrivia(models.TextChoices):
    GENERAL = 'GENERAL', 'General'
    BOLSAS = 'BOLSAS', '¿En qué bolsa va?'
    MITOS = 'MITOS', 'Mitos vs. Realidad'


class ModoTrivia(models.TextChoices):
    NIVELES = 'NIVELES', 'Por niveles'
    BOLSAS = 'BOLSAS', '¿En qué bolsa va?'
    MITOS = 'MITOS', 'Mitos vs. Realidad'


class PreguntaTrivia(models.Model):
    enunciado = models.CharField(max_length=300)
    explicacion = models.CharField('explicación', max_length=500, help_text='Retroalimentación que muestra Escarlata.')
    dificultad = models.PositiveSmallIntegerField(default=1, choices=[(1, 'Fácil'), (2, 'Media'), (3, 'Difícil')])
    categoria = models.CharField('categoría', max_length=12, choices=CategoriaTrivia.choices, default=CategoriaTrivia.GENERAL)
    activa = models.BooleanField(default=False)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='+')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pregunta_trivia'
        ordering = ['-creado_en']
        indexes = [models.Index(fields=['activa'], name='ix_pregunta_activa')]
        constraints = [models.CheckConstraint(condition=models.Q(dificultad__gte=1, dificultad__lte=3),
                                              name='ck_pregunta_dificultad')]

    def __str__(self):
        return self.enunciado

    def errores(self):
        """RN-07: entre 2 y 4 opciones y exactamente una correcta."""
        opciones = list(self.opciones.all())
        errores = []
        if not 2 <= len(opciones) <= 4:
            errores.append('Debe tener entre 2 y 4 opciones.')
        if sum(1 for o in opciones if o.es_correcta) != 1:
            errores.append('Debe tener exactamente una opción correcta.')
        return errores

    def validar(self):
        return not self.errores()

    def opcion_correcta(self):
        return self.opciones.filter(es_correcta=True).first()


class OpcionTrivia(models.Model):
    pregunta = models.ForeignKey(PreguntaTrivia, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=200)
    es_correcta = models.BooleanField('es la correcta', default=False)
    orden = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'opcion_trivia'
        ordering = ['orden']
        constraints = [models.UniqueConstraint(fields=['pregunta', 'orden'], name='uq_opcion_orden'),
                       models.CheckConstraint(condition=models.Q(orden__gte=1, orden__lte=4), name='ck_opcion_orden')]

    def __str__(self):
        return self.texto

    @property
    def letra(self):
        return 'ABCD'[self.orden - 1]


class PartidaTrivia(models.Model):
    """Partida anónima o ligada a la cuenta del visitante si inició sesión."""
    codigo_qr = models.ForeignKey('qr.CodigoQR', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='partidas', help_text='Solo si el visitante inició sesión y autorizó guardar su progreso.')
    nivel = models.PositiveSmallIntegerField('nivel', default=1, choices=NIVELES_CHOICES)
    modo = models.CharField('modo de juego', max_length=12, choices=ModoTrivia.choices, default=ModoTrivia.NIVELES)
    iniciada_en = models.DateTimeField(auto_now_add=True)
    finalizada_en = models.DateTimeField(null=True, blank=True)
    puntaje = models.PositiveSmallIntegerField(default=0)
    total_preguntas = models.PositiveSmallIntegerField(default=5)
    preguntas_ids = models.CharField(max_length=60, default='', editable=False,
                                     help_text='Orden de las preguntas de la partida (ids separados por coma).')

    class Meta:
        db_table = 'partida_trivia'
        ordering = ['-iniciada_en']
        indexes = [models.Index(fields=['iniciada_en'], name='ix_partida_fecha')]
        constraints = [
            models.CheckConstraint(condition=models.Q(puntaje__lte=models.F('total_preguntas')), name='ck_partida_puntaje'),
            models.CheckConstraint(condition=models.Q(nivel__gte=1, nivel__lte=3), name='ck_partida_nivel'),
        ]

    @classmethod
    def nueva(cls, codigo_qr=None, usuario=None, nivel=1, modo=ModoTrivia.NIVELES):
        nivel = nivel if nivel in (1, 2, 3) else 1
        modo = modo if modo in ModoTrivia.values else ModoTrivia.NIVELES
        todas = [p for p in PreguntaTrivia.objects.filter(activa=True).prefetch_related('opciones') if p.validar()]
        n = min(settings.TRIVIA_PREGUNTAS_POR_PARTIDA, len(todas))
        if n == 0:
            raise ValidationError('No hay preguntas activas.')
        rng = secrets.SystemRandom()
        if modo in (ModoTrivia.BOLSAS, ModoTrivia.MITOS):
            prioritarias = [p for p in todas if p.categoria == modo]
            otras = [p for p in todas if p.categoria != modo]
        else:
            prioritarias = [p for p in todas if p.dificultad == nivel]
            otras = [p for p in todas if p.dificultad != nivel]
        if len(prioritarias) >= n:
            elegidas = rng.sample(prioritarias, n)
        else:
            faltan = n - len(prioritarias)
            elegidas = prioritarias + rng.sample(otras, min(faltan, len(otras)))
            rng.shuffle(elegidas)
        return cls.objects.create(codigo_qr=codigo_qr, usuario=usuario, nivel=nivel, modo=modo,
                                  total_preguntas=len(elegidas),
                                  preguntas_ids=','.join(str(p.pk) for p in elegidas))

    @property
    def racha_actual(self):
        racha = 0
        for ok in self.respuestas.order_by('-respondida_en').values_list('es_correcta', flat=True):
            if ok:
                racha += 1
            else:
                break
        return racha

    @property
    def ids(self):
        return [int(x) for x in self.preguntas_ids.split(',') if x]

    @property
    def respondidas(self):
        return self.respuestas.count()

    @property
    def terminada(self):
        return self.finalizada_en is not None

    @property
    def info_nivel(self):
        return info_nivel(self.nivel)

    def siguiente_pregunta(self):
        hechas = set(self.respuestas.values_list('pregunta_id', flat=True))
        for pid in self.ids:
            if pid not in hechas:
                return PreguntaTrivia.objects.prefetch_related('opciones').get(pk=pid)
        return None

    @transaction.atomic
    def responder(self, pregunta, opcion):
        if pregunta.pk not in self.ids or opcion.pregunta_id != pregunta.pk:
            raise ValidationError('La respuesta no corresponde a esta partida.')
        respuesta, creada = RespuestaPartida.objects.get_or_create(
            partida=self, pregunta=pregunta, defaults={'opcion': opcion, 'es_correcta': opcion.es_correcta})
        if creada and respuesta.es_correcta:
            self.puntaje += 1
            self.save(update_fields=['puntaje'])
        return respuesta

    def finalizar(self):
        if not self.finalizada_en:
            self.finalizada_en = timezone.now()
            self.save(update_fields=['finalizada_en'])
        return self.puntaje


class RespuestaPartida(models.Model):
    partida = models.ForeignKey(PartidaTrivia, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(PreguntaTrivia, on_delete=models.RESTRICT, related_name='+')
    opcion = models.ForeignKey(OpcionTrivia, on_delete=models.RESTRICT, related_name='+')
    es_correcta = models.BooleanField()
    respondida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'respuesta_partida'
        ordering = ['respondida_en']
        constraints = [models.UniqueConstraint(fields=['partida', 'pregunta'], name='uq_respuesta')]


class InsigniaUsuario(models.Model):
    """Insignias ecológicas obtenidas por un usuario registrado al avanzar en los niveles de la trivia."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='insignias')
    codigo = models.CharField('insignia', max_length=32, choices=INSIGNIAS_CHOICES)
    obtenida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insignia_usuario'
        ordering = ['obtenida_en']
        constraints = [models.UniqueConstraint(fields=['usuario', 'codigo'], name='uq_usuario_insignia')]

    def __str__(self):
        return f'{self.usuario} · {self.get_codigo_display()}'

    @property
    def datos(self):
        return INSIGNIAS_POR_CODIGO.get(self.codigo, INSIGNIAS[0])


def progreso_niveles(usuario=None, sesion=None):
    """Devuelve el estado de los 3 niveles (dificultad progresiva: 3/5, 4/5 y 5/5) y puntos acumulados."""
    mejores = {1: None, 2: None, 3: None}
    partidas_totales = 0
    puntos_totales = 0
    if usuario is not None and usuario.is_authenticated:
        terminadas = PartidaTrivia.objects.filter(usuario=usuario, finalizada_en__isnull=False)
        partidas_totales = terminadas.count()
        for p in terminadas.values('nivel', 'puntaje'):
            nv = p['nivel']
            puntos_totales += p['puntaje']
            if nv in mejores and (mejores[nv] is None or p['puntaje'] > mejores[nv]):
                mejores[nv] = p['puntaje']
    elif sesion is not None:
        guardado = sesion.get('trivia_mejores', {})
        for nv in (1, 2, 3):
            val = guardado.get(str(nv))
            if isinstance(val, int):
                mejores[nv] = val
        partidas_totales = int(sesion.get('trivia_partidas', 0))
        puntos_totales = int(sesion.get('trivia_puntos', 0))

    superado_1 = (mejores[1] or 0) >= 3
    superado_2 = (mejores[2] or 0) >= 4
    desbloqueados = {1: True, 2: superado_1, 3: superado_1 and superado_2}
    niveles = []
    for n in NIVELES:
        num = n['numero']
        mejor = mejores[num]
        niveles.append({
            **n,
            'desbloqueado': desbloqueados[num],
            'superado': (mejor or 0) >= n['meta'],
            'mejor': mejor,
        })
    return {
        'niveles': niveles,
        'partidas_totales': partidas_totales,
        'puntos_totales': puntos_totales,
        'desbloqueados': desbloqueados,
    }


def evaluar_insignias(partida, sesion=None):
    """Otorga insignias EXCLUSIVAMENTE según los puntos obtenidos en el nivel o acumulados."""
    codigos = []
    if partida.nivel == 1 and partida.puntaje >= 3:
        codigos.append('explorador_bolsas')
    elif partida.nivel == 2 and partida.puntaje >= 4:
        codigos.append('guardian_reciclaje')
    elif partida.nivel == 3 and partida.puntaje >= 5:
        codigos.append('maestro_guacamaya')
    if partida.total_preguntas > 0 and partida.puntaje >= partida.total_preguntas:
        codigos.append('vuelo_perfecto')

    # Actualizar progreso y puntos acumulados en sesión para visitantes sin cuenta
    puntos_acumulados = partida.puntaje
    if sesion is not None:
        mejores = dict(sesion.get('trivia_mejores', {}))
        clave = str(partida.nivel)
        if mejores.get(clave) is None or partida.puntaje > mejores[clave]:
            mejores[clave] = partida.puntaje
        sesion['trivia_mejores'] = mejores
        contadas = list(sesion.get('trivia_contadas', []))
        if partida.pk not in contadas:
            contadas.append(partida.pk)
            sesion['trivia_contadas'] = contadas[-50:]
            sesion['trivia_partidas'] = int(sesion.get('trivia_partidas', 0)) + 1
            sesion['trivia_puntos'] = int(sesion.get('trivia_puntos', 0)) + partida.puntaje
        puntos_acumulados = int(sesion.get('trivia_puntos', 0))

    if partida.usuario_id:
        puntos_acumulados = (
            PartidaTrivia.objects.filter(usuario_id=partida.usuario_id, finalizada_en__isnull=False)
            .aggregate(total=models.Sum('puntaje'))['total'] or 0
        )

    if puntos_acumulados >= 3:
        codigos.append('primera_semilla')
    if puntos_acumulados >= 12:
        codigos.append('constancia_verde')

    nuevas = []
    if partida.usuario_id:
        for cod in codigos:
            _, creada = InsigniaUsuario.objects.get_or_create(usuario_id=partida.usuario_id, codigo=cod)
            if creada:
                nuevas.append(INSIGNIAS_POR_CODIGO[cod])
    elif sesion is not None:
        actuales = list(sesion.get('trivia_insignias', []))
        for cod in codigos:
            if cod not in actuales:
                actuales.append(cod)
                nuevas.append(INSIGNIAS_POR_CODIGO[cod])
        sesion['trivia_insignias'] = actuales
    return nuevas


def obtener_insignias(usuario=None, sesion=None):
    """Devuelve el catálogo completo de insignias marcando cuáles ya tiene la persona."""
    fechas = {}
    if usuario is not None and usuario.is_authenticated:
        fechas = {i.codigo: i.obtenida_en for i in InsigniaUsuario.objects.filter(usuario=usuario)}
    elif sesion is not None:
        fechas = {cod: True for cod in sesion.get('trivia_insignias', [])}
    resultado = []
    for ins in INSIGNIAS:
        obtenida = ins['codigo'] in fechas
        resultado.append({
            **ins,
            'obtenida': obtenida,
            'obtenida_en': fechas.get(ins['codigo']) if not isinstance(fechas.get(ins['codigo']), bool) else None,
        })
    return resultado
