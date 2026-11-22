# EcoParce v1.2 · Cambios respecto al documento técnico

Este documento complementa el *Documento técnico de análisis y diseño* (entrega 2). Registra los requisitos nuevos, las decisiones y lo que cambió en el modelo de datos, para mantener la trazabilidad que exige el plan CMMI.

## 1. Requisitos nuevos

| ID | Requisito | Prioridad | Módulo | Pruebas |
|---|---|---|---|---|
| RF-16 | Escanear el código de barras de un producto (o un QR de EcoParce) con la cámara y mostrar en qué bolsa va cada parte del empaque | Alta | `buscador` (`escaner.py`, `/escanear/`) | `apps/buscador/tests_escaner.py` |
| RF-17 | Mostrar en un mapa los puntos de recolección **oficiales** de Bogotá, filtrarlos por residuo y localidad y ordenarlos por cercanía | Alta | `contenidos` (`/puntos/`, `sincronizar_puntos_sda`) | `apps/contenidos/tests_puntos.py` |
| RF-18 | Cuenta opcional del visitante (correo verificado o Google) para guardar su progreso; descarga y eliminación de sus datos | Media | `cuentas` | `apps/cuentas/tests.py` |
| RNF-07 | Verificación en dos pasos obligatoria para el panel | Alta | `cuentas` | `apps/cuentas/tests.py` |

RF-12 («Puntos de entrega») pasa de puntos digitados a mano a **datos oficiales con coordenadas**.

## 2. Fuentes externas (APIs)

| Fuente | Uso | Cómo se consulta | Licencia | Si falla |
|---|---|---|---|---|
| Secretaría Distrital de Ambiente, Visor Geográfico Ambiental, servicio `api/v1/posconsumo_vista` | 1.804 puntos posconsumo con coordenadas, horario, teléfono, localidad y residuos que reciben | El comando `sincronizar_puntos_sda` los copia a la base de datos (tarea semanal). El visitante nunca consulta el servicio | Datos abiertos SDA, CC BY 4.0 (se cita en cada página) | Se conservan los puntos de la última sincronización |
| Open Food Facts, Open Beauty Facts, Open Products Facts (`/api/v2/product/{código}`) | Materiales y partes del empaque de un producto | Desde el servidor, con caché de 7 días y límite de consultas | ODbL (se cita en cada resultado) | Se ofrece buscar el residuo por nombre |
| OpenStreetMap (teselas del mapa) | Fondo del mapa | El navegador carga solo imágenes (CSP: `img-src` acotado a `tile.openstreetmap.org`) | ODbL, con atribución en el mapa | El listado de puntos funciona sin el mapa |
| Google (OpenID Connect) | Ingreso con Google | Flujo con PKCE desde el servidor | — | Se ingresa con correo y contraseña |

Correspondencia de los tipos de residuo de la SDA con los residuos de EcoParce: `apps/contenidos/datos_iniciales.py` (`SDA_A_ECOPARCE`). Se agregaron 7 residuos especiales que reciben los puntos oficiales: baterías de carro, electrodomésticos grandes, llantas, medicamentos veterinarios, envases de plaguicidas, CD/DVD y ropa.

## 3. Privacidad de las funciones nuevas

- **Cámara:** se activa solo al pulsar «Abrir cámara». La imagen se procesa en el teléfono (BarcodeDetector del navegador o ZXing, incluido en el sitio); al servidor solo llega el número del código.
- **Ubicación:** se usa solo en el navegador para ordenar los puntos. No se envía al servidor, no queda en registros ni en URLs. El documento técnico decía que el visitante no entrega su ubicación, y esto se mantiene.
- `Permissions-Policy` permite cámara y ubicación solo al propio sitio (`self`).

## 4. Cambios en el modelo de datos

| Tabla | Cambio |
|---|---|
| `punto_entrega` | Nuevas columnas `latitud`, `longitud`, `barrio`, `recibe`, `fuente` (SDA o MANUAL), `id_externo`, `verificado_en`; nombre y horario más largos; índice `ix_punto_fuente_externo` |
| `residuo` | 7 registros nuevos de residuos especiales (datos, no estructura) |
| v1.1 | `consentimiento`, rol VISITANTE, `partida_trivia.usuario`, `sugerencia.usuario` y tablas de django-allauth (ver README) |

Migraciones: `contenidos/0003_puntos_oficiales`, `cuentas/0002` y `0003`, `trivia/0002`, `buscador/0002`.

## 5. Interfaz

- Pestaña **Escanear** destacada en la barra inferior y accesos en el inicio («Escanear producto», «Puntos cercanos»).
- Página **Puntos** con mapa, filtros, «Ver los más cercanos a mí» y botón «Cómo llegar» en cada punto.
- Fondo con un patrón muy tenue de hojas y flechas de reciclaje (7 % de opacidad) que no compite con el contenido.
- El botón de Google se desactiva con una explicación mientras el servidor no tenga credenciales, en vez de mostrar el error 400 de Google.

## 6. Operación

| Tarea programada | Frecuencia | Comando |
|---|---|---|
| Actualizar puntos oficiales | Semanal | `python manage.py sincronizar_puntos_sda` |
| Respaldo de la base de datos | Semanal | `bash docs/respaldo_semanal.sh` |
| Borrar registros de uso de más de 24 meses | Mensual | `python manage.py depurar_registros_uso` |
