"""Row-Level Security (RLS) de mínimo privilegio para EcoParce (defensa en profundidad).

Principios aplicados (cero políticas abiertas):
- NINGUNA regla usa ``USING (true)`` ni ``WITH CHECK (true)``.
- Políticas granulares separadas por operación SQL: ``FOR SELECT``, ``FOR INSERT``, ``FOR UPDATE``, ``FOR DELETE``.
- Denegación explícita (``USING (false)``) sobre ``UPDATE`` y ``DELETE`` en tablas de auditoría inmutables.
- Doble capa: PostgreSQL nativo (``ENABLE`` + ``FORCE ROW LEVEL SECURITY``) y capa ORM
  (``RLSContextMiddleware`` + ``filtrar_por_rls``) para SQLite/MySQL/PostgreSQL.
"""
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import connection

_rls_contexto = ContextVar('ecoparce_rls_contexto', default={'user_id': '', 'role': 'ANON', 'bypass': '0'})

_BYPASS = "current_setting('app.rls_bypass', true) = '1'"
_ES_SISTEMA = "current_setting('app.current_user_role', true) = 'SISTEMA'"
_ES_PERSONAL = "current_setting('app.current_user_role', true) IN ('SISTEMA', 'CONTENIDO')"
_ES_ACTOR_VALIDO = "current_setting('app.current_user_role', true) IN ('VISITANTE', 'CONTENIDO', 'SISTEMA', 'API_GATEWAY')"
_ES_PROPIO_ID = "id::text = NULLIF(current_setting('app.current_user_id', true), '')"
_ES_PROPIO_USUARIO = "usuario_id::text = NULLIF(current_setting('app.current_user_id', true), '')"
_ES_PROPIO_PROP = "propietario_id::text = NULLIF(current_setting('app.current_user_id', true), '')"

# Políticas RLS granulares por operación SQL (cero reglas abiertas).
POLITICAS_RLS_POSTGRES = [
    {
        'tabla': 'usuario',
        'reglas': [
            ('rls_usuario_select', 'SELECT', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_ID}', None),
            ('rls_usuario_insert', 'INSERT', None, f'{_BYPASS} OR {_ES_SISTEMA}'),
            ('rls_usuario_update', 'UPDATE', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_ID}', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_ID}'),
            ('rls_usuario_delete', 'DELETE', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_ID}', None),
        ],
    },
    {
        'tabla': 'consentimiento',
        'reglas': [
            ('rls_consentimiento_select', 'SELECT', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}', None),
            ('rls_consentimiento_insert', 'INSERT', None, f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}'),
            ('rls_consentimiento_update', 'UPDATE', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}'),
            ('rls_consentimiento_delete', 'DELETE', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}', None),
        ],
    },
    {
        'tabla': 'solicitud_admin',
        'reglas': [
            ('rls_solicitud_select', 'SELECT', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}', None),
            ('rls_solicitud_insert', 'INSERT', None, f'{_BYPASS} OR {_ES_PROPIO_USUARIO}'),
            ('rls_solicitud_update', 'UPDATE', f'{_BYPASS} OR {_ES_SISTEMA}', f'{_BYPASS} OR {_ES_SISTEMA}'),
            ('rls_solicitud_delete', 'DELETE', f'{_BYPASS} OR {_ES_SISTEMA}', None),
        ],
    },
    {
        'tabla': 'partida_trivia',
        'reglas': [
            ('rls_trivia_select', 'SELECT', f'{_BYPASS} OR {_ES_PERSONAL} OR usuario_id IS NULL OR {_ES_PROPIO_USUARIO}', None),
            ('rls_trivia_insert', 'INSERT', None, f'{_BYPASS} OR usuario_id IS NULL OR {_ES_PROPIO_USUARIO}'),
            ('rls_trivia_update', 'UPDATE', f'{_BYPASS} OR usuario_id IS NULL OR {_ES_PROPIO_USUARIO}', f'{_BYPASS} OR usuario_id IS NULL OR {_ES_PROPIO_USUARIO}'),
            ('rls_trivia_delete', 'DELETE', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_USUARIO}', None),
        ],
    },
    {
        'tabla': 'sugerencia',
        'reglas': [
            ('rls_sugerencia_select', 'SELECT', f'{_BYPASS} OR {_ES_PERSONAL} OR {_ES_PROPIO_USUARIO}', None),
            ('rls_sugerencia_insert', 'INSERT', None, f'{_BYPASS} OR usuario_id IS NULL OR {_ES_PROPIO_USUARIO}'),
            ('rls_sugerencia_update', 'UPDATE', f'{_BYPASS} OR {_ES_PERSONAL}', f'{_BYPASS} OR {_ES_PERSONAL}'),
            ('rls_sugerencia_delete', 'DELETE', f'{_BYPASS} OR {_ES_SISTEMA}', None),
        ],
    },
    {
        'tabla': 'registro_auditoria',
        'reglas': [
            ('rls_auditoria_select', 'SELECT', f'{_BYPASS} OR {_ES_SISTEMA}', None),
            ('rls_auditoria_insert', 'INSERT', None, f'{_BYPASS} OR {_ES_ACTOR_VALIDO}'),
            ('rls_auditoria_no_update', 'UPDATE', 'false', 'false'),
            ('rls_auditoria_no_delete', 'DELETE', 'false', None),
        ],
    },
    {
        'tabla': 'api_clave',
        'reglas': [
            ('rls_api_clave_select', 'SELECT', f'{_BYPASS} OR {_ES_SISTEMA} OR {_ES_PROPIO_PROP}', None),
            ('rls_api_clave_insert', 'INSERT', None, f'{_BYPASS} OR {_ES_SISTEMA}'),
            ('rls_api_clave_update', 'UPDATE', f'{_BYPASS} OR {_ES_SISTEMA}', f'{_BYPASS} OR {_ES_SISTEMA}'),
            ('rls_api_clave_delete', 'DELETE', f'{_BYPASS} OR {_ES_SISTEMA}', None),
        ],
    },
    {
        'tabla': 'api_gateway_log',
        'reglas': [
            ('rls_gw_log_select', 'SELECT', f'{_BYPASS} OR {_ES_SISTEMA}', None),
            ('rls_gw_log_insert', 'INSERT', None, f'{_BYPASS} OR {_ES_ACTOR_VALIDO}'),
            ('rls_gw_log_no_update', 'UPDATE', 'false', 'false'),
            ('rls_gw_log_no_delete', 'DELETE', 'false', None),
        ],
    },
]


def _construir_sentencia_politica(tabla, nombre, operacion, using_expr, check_expr):
    """Construye una sentencia CREATE POLICY SQL específica para una operación (SELECT/INSERT/UPDATE/DELETE)."""
    partes = [f'CREATE POLICY "{nombre}" ON "{tabla}" FOR {operacion}']
    if using_expr is not None:
        partes.append(f'    USING ({using_expr})')
    if check_expr is not None:
        partes.append(f'    WITH CHECK ({check_expr})')
    return '\n'.join(partes) + ';'


def generar_sql_rls():
    """Genera el script SQL idempotente con políticas RLS granulares de mínimo privilegio."""
    bloques = [
        '-- EcoParce: Políticas de Row-Level Security (RLS) de mínimo privilegio para PostgreSQL',
        '-- Sin reglas abiertas (cero USING(true) / WITH CHECK(true)). Separadas por SELECT/INSERT/UPDATE/DELETE.',
        '-- Inmutabilidad garantizada a nivel BD (UPDATE/DELETE denegados con false en auditoría y gateway).',
        '',
    ]
    for item in POLITICAS_RLS_POSTGRES:
        tabla = item['tabla']
        bloques.append(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY;')
        bloques.append(f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY;')
        for nombre, operacion, using_expr, check_expr in item['reglas']:
            bloques.append(f'DROP POLICY IF EXISTS "{nombre}" ON "{tabla}";')
            bloques.append(_construir_sentencia_politica(tabla, nombre, operacion, using_expr, check_expr))
        bloques.append('')
    return '\n'.join(bloques)


def aplicar_contexto_db(user_id='', role='ANON', bypass=False):
    """Propaga el contexto RLS a la sesión actual (ContextVar + set_config en PostgreSQL)."""
    estado = {'user_id': str(user_id or ''), 'role': str(role or 'ANON'), 'bypass': '1' if bypass else '0'}
    _rls_contexto.set(estado)
    if connection.vendor == 'postgresql':
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_id', %s, false)", [estado['user_id']])
            cur.execute("SELECT set_config('app.current_user_role', %s, false)", [estado['role']])
            cur.execute("SELECT set_config('app.rls_bypass', %s, false)", [estado['bypass']])
    return estado


def obtener_contexto_rls():
    """Devuelve una copia del contexto RLS vigente para la petición actual."""
    return dict(_rls_contexto.get())


@contextmanager
def contexto_rls_sistema():
    """Context manager temporal para tareas internas del sistema (autenticación, migraciones, jobs)."""
    anterior = obtener_contexto_rls()
    aplicar_contexto_db(user_id=anterior['user_id'], role='SISTEMA', bypass=True)
    try:
        yield
    finally:
        aplicar_contexto_db(user_id=anterior['user_id'], role=anterior['role'], bypass=anterior['bypass'] == '1')


def filtrar_por_rls(queryset, usuario, campo_usuario='usuario', permitir_personal=False):
    """Aplica aislamiento Row-Level Security a nivel ORM (garantizado en SQLite, MySQL y PostgreSQL)."""
    if usuario is None or not getattr(usuario, 'is_authenticated', False):
        return queryset.none()
    if getattr(usuario, 'rol', None) == 'SISTEMA' and getattr(usuario, 'is_active', False):
        return queryset
    if permitir_personal and getattr(usuario, 'es_personal', False):
        return queryset
    if campo_usuario == 'pk':
        return queryset.filter(pk=usuario.pk)
    return queryset.filter(**{campo_usuario: usuario})


def aplicar_politicas_postgresql():
    """Aplica las políticas RLS en PostgreSQL. Devuelve lista de tablas configuradas o None si no es PostgreSQL."""
    if connection.vendor != 'postgresql':
        return None
    tablas_existentes = set(connection.introspection.table_names())
    aplicadas = []
    with connection.cursor() as cur:
        for item in POLITICAS_RLS_POSTGRES:
            tabla = item['tabla']
            if tabla not in tablas_existentes:
                continue
            cur.execute(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY;')  # nosec B608: identificador fijo interno
            cur.execute(f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY;')  # nosec B608
            for nombre, operacion, using_expr, check_expr in item['reglas']:
                cur.execute(f'DROP POLICY IF EXISTS "{nombre}" ON "{tabla}";')  # nosec B608
                cur.execute(_construir_sentencia_politica(tabla, nombre, operacion, using_expr, check_expr))  # nosec B608
            aplicadas.append(tabla)
    return aplicadas


class RLSContextMiddleware:
    """Middleware que sincroniza el usuario autenticado con el contexto RLS en cada petición."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        if usuario is not None and getattr(usuario, 'is_authenticated', False):
            aplicar_contexto_db(user_id=usuario.pk, role=getattr(usuario, 'rol', 'VISITANTE'), bypass=False)
        else:
            aplicar_contexto_db(user_id='', role='ANON', bypass=False)
        try:
            return self.get_response(request)
        finally:
            aplicar_contexto_db(user_id='', role='ANON', bypass=False)
