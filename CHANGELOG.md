# Registro de cambios (CHANGELOG) · EcoParce

Este proyecto sigue el [Versionado Semántico (SemVer 2.0.0)](https://semver.org/lang/es/) y control de versiones en Git.

## [2.9.1] - 2026-11-26
### Corregido
- **Escáner QR y códigos de barras (`/escanear/`)**: corregida la lectura de códigos QR de EcoParce (`/q/XXXXXXXX`) independientemente del dominio/puerto, extracción automática de GTIN en QR GS1 Digital Link, consulta automática al catálogo de EcoParce para QR de texto/residuos, tarjeta informativa para enlaces externos, detención correcta de la cámara al leer y versionado `?v=` del script.

## [2.9.0] - 2026-11-26
### Seguridad, Arquitectura, OAuth 2.0 y Calidad de Software
- **Cifrado de cuentas en base de datos y cifrado E2E (AES-256-GCM)**:
  - Cifrado transparente a nivel de campo con **MultiFernet (AES-128-CBC + HMAC-SHA256)** y rotación de claves (`apps/core/cifrado.py`) para `Usuario.nombre` y `SolicitudAdmin.motivo`, más huella ciega **HMAC-SHA256** (`Usuario.correo_hash`) y comando `cifrar_datos_cuentas`.
  - Nuevo módulo de cifrado autenticado de extremo a extremo **AES-256-GCM + HKDF-SHA256 + AAD** (`apps/core/cifrado_e2e.py`), disponible en `/api/v1/cuenta/resumen/?e2e=1`.
- **Row-Level Security (RLS) de mínimo privilegio (32 políticas, cero reglas abiertas)**:
  - Políticas granulares separadas por operación (`FOR SELECT`, `FOR INSERT`, `FOR UPDATE`, `FOR DELETE`) sobre las 8 tablas sensibles en `apps/core/rls.py` y `docs/rls_postgresql.sql`, con inmutabilidad forzada en BD (`USING (false)`) para auditoría y gateway, más capa ORM `RLSContextMiddleware` / `filtrar_por_rls()`.
- **API Gateway REST (`GET`/`POST`), WAF y Bitácora Inmutable (`apps/api/`)**:
  - Endpoints `/api/v1/estado/`, `/guias/`, `/buscar/`, `/puntos/`, `/escanear/`, `/sugerencias/`, `/cuenta/resumen/`, `/gateway/logs/` y especificación **OpenAPI 3.0.3** (`/api/v1/openapi.json`).
  - Filtros WAF contra SQLi, XSS, Path Traversal y Null Bytes, gestión de **API Keys (SHA-256)**, *rate limiting* y bitácora inmutable `RegistroGateway`.
- **Servidor OAuth 2.0 endurecido (RFC 6749, 7519, 7009, 7662, 8414, 8725, 9700)**:
  - Emisión de tokens **Bearer JWT HS256** + **Refresh Tokens rotativos** con detección de reutilización (`/api/v1/oauth/token/`), revocación (`/oauth/revoke/`), introspección (`/oauth/introspect/`), UserInfo (`/oauth/userinfo/`), metadatos (`/.well-known/oauth-authorization-server`) y validación estricta de `scopes` (`read`/`write`).
- **Tablero en vivo de Calidad de Software (`/panel/calidad/`)**:
  - Métricas ISO/IEC 25010 en tiempo real, estado de cifrado, RLS, amenazas WAF bloqueadas, bitácora del Gateway y gestión visual de API Keys para `SISTEMA`.
- **PWA verificada de extremo a extremo y diseño Aurora Boreal**:
  - Service Worker seguro (`/sw.js`), guía sin conexión (`/offline/`), iconos PWA obligatorios `192×192` y `512×512` en `manifest.webmanifest`, verificación de correo por código (`VERIFICAR_CORREO_POR_CODIGO=1`) y fondo animado **Aurora Boreal verde** visible en todo el sitio.
  - Suite ampliada a **120 pruebas automatizadas** aprobadas (`0` fallos) y `check --deploy` sin advertencias.

## [2.8.0] - 2026-11-23
### Innovación
- **Generador interactivo de Carteles y Etiquetas HD para Canecas (`/guias/`)**: permite personalizar en vivo con el nombre de tu hogar, colegio u oficina y descargar en PNG listo para imprimir el cartel completo de la Resolución 2184 o las etiquetas individuales de Bolsa Blanca, Bolsa Negra y Bolsa Verde (100 % local en Canvas HTML5 y compatible con CSP estricta).

## [2.7.0] - 2026-11-22
### Agregado y Seguridad
- **Buscador con autocompletado instantáneo en vivo (`/buscar/autocompletar/`)**: al escribir desde 2 caracteres muestra en tiempo real los residuos coincidentes con su etiqueta de color de bolsa (`Blanca`, `Negra`, `Verde`, `Posconsumo`), con rate-limiting y renderizado DOM seguro.
- **Instalación como App PWA en 1 toque**: soporte progresivo de `beforeinstallprompt` («Instalar app») para agregar EcoParce a la pantalla de inicio del celular.
- **Protección OWASP contra CSV Formula Injection**: sanitización de celdas en `/panel/estadisticas/exportar.csv` para impedir la ejecución de fórmulas maliciosas en Excel/Calc.

## [2.6.1] - 2026-11-22
### Corregido
- **Altura adaptable del chat EcoBot en pantallas móviles**: ajuste `max-height: calc(100dvh - 148px)` con desplazamiento interno para que el encabezado del chat (botón «Limpiar» y «✕») permanezca siempre visible incluso en pantallas pequeñas.

## [2.6.0] - 2026-11-22
### Seguridad, Arquitectura y Chat Profesional
- **Asistente EcoBot conectado en tiempo real a la base oficial (`/asistente/consultar/`)**: consulta el catálogo real de residuos y guías con rate-limiting (45 req/min), tarjetas estructuradas por color de bolsa, pasos de preparación, chips relacionados, botón «Limpiar», memoria de sesión (`sessionStorage`) y renderizado DOM 100 % seguro contra XSS.
- **Endurecimiento de producción y despliegue**: nuevo healthcheck real de base de datos (`/health/`) configurado en `render.yaml`, `conn_health_checks=True` para PostgreSQL en Render, límite de payload POST (`2.5 MB`) y auditoría completa de seguridad y calidad aprobada.

## [2.5.0] - 2026-11-22
### Agregado y Mejorado
- **Asistente Experto flotante «Escarlata · Consultor EcoParce»**: disponible en todo el sitio público para responder al instante en qué bolsa o punto posconsumo va cualquier residuo, con chips rápidos y enlace directo a guías, buscador o mapa.
- **Actualización garantizada sin caché vieja**: cabecera `Cache-Control: no-cache, must-revalidate` en páginas HTML públicas (para que un simple refresh en celular siempre cargue la última versión desplegada) y permiso `microphone=(self)` habilitado para la búsqueda por voz en `/buscar/`.

## [2.4.2] - 2026-11-22
### Mejorado
- **Inicio más limpio y profesional**: se retiró el bloque promocional «Nuevo en EcoParce» con emojis de la pantalla de inicio para evitar redundancia visual y mantener una jerarquía limpia hacia las bolsas, impacto, economía circular y tarjetas 3D.

## [2.4.1] - 2026-11-22
### Mejorado
- **Medidor de contraseña rediseñado**: tarjeta esmeralda luminosa con barra animada y chips interactivos que se iluminan al cumplir cada requisito; se retiró la mención técnica de Argon2id de la vista del usuario (manteniendo el cifrado real Argon2id en el servidor).
- **Portada más limpia**: se eliminó la etiqueta visible «Ilustración IA» de la pantalla de inicio.

## [2.4.0] - 2026-11-22
### Agregado
- **Aviso automático de nueva versión y botón «Actualizar ahora»**: nuevo endpoint `/version.json` sin caché, versionado `?v=` en CSS/JS y banner emergente que detecta cuando hay una versión más reciente en el servidor para limpiar caché y recargar con un toque en celular o PC.
- **Control de versiones en el panel de administrador (`/panel/versiones/`)**: vista exclusiva para administradores con el historial completo de cada lanzamiento y qué se implementó en cada versión.
- **Identidad de marca oficial**: crédito de marca visible para **Francisco Navarro, Danixa Herrera y Darien García** en el pie de página y en el panel de versiones.

## [2.3.1] - 2026-11-22
### Seguridad y UX
- **Política estricta de contraseñas seguras + Medidor visual en tiempo real (`/accounts/signup/`)**:
  - Validador en servidor (`apps.cuentas.validadores.ClaveSeguraValidator`) y en `RegistroForm.clean()`: exige más de 8 caracteres (mínimo 9), letra minúscula, mayúscula, número, carácter especial y prohíbe incluir el correo o el nombre.
  - Barra de avance de seguridad en vivo (`0 %` a `100 %`), lista interactiva de los 6 requisitos, indicador de coincidencia de confirmación y botón **Ver / Ocultar** en todos los campos de contraseña.
  - Cifrado (hash) verificado con **Argon2id** en base de datos.

## [2.3.0] - 2026-11-22
### Agregado
- **Contenido visual interactivo enriquecido en `/` y `/guias/`**:
  - **Banner de experiencias interactivas** en el inicio con accesos directos al Video Interactivo 60 s, Arcade Atrapa y Separa y Diploma HD.
  - **Infografía interactiva «¿En qué se transforma lo que separas?»** (Economía Circular en 4 pasos para Botella PET, Lata aluminio, Cartón/Papel, Orgánicos y Aceite usado).
  - **Tarjetas volteables 3D «Mitos vs. Realidad»** en el inicio con giro suave al tocar o hacer clic.
  - **Checklist interactivo «Prepara tu cocina EcoParce en 5 minutos»** (persistido en el navegador con barra de progreso) y comparativa visual **«Sí va vs. No va»** en `/guias/`.

## [2.2.0] - 2026-11-22
### Agregado
- **Video educativo interactivo en `/trivia/`**: reproductor cinematográfico HTML5 Canvas 100 % local y compatible con CSP estricta, con Escarlata animada, 4 capítulos (Blanca, Negra, Verde y Posconsumo), subtítulos sincronizados, narración opcional en voz en español (`es-CO`) y **4 pausas interactivas con retos en vivo** dentro del video.
- **Simulador Arcade «Atrapa y Separa 30 s»** en `/trivia/`: mini-juego contrarreloj con multiplicador de combo (hasta x4), récord personal guardado en el navegador, atajos de teclado (`1`-`4`) y retroalimentación educativa instantánea.
- **Reto Diario Ecológico con racha**: misión práctica diaria que rota automáticamente cada día calendario con seguimiento de racha consecutiva.
- **Certificado Digital Ambiental descargable (PNG HD)** para usuarios registrados en `/trivia/` y `/trivia/resultado/`, personalizado con nombre, rango, puntaje y medallas 3D.
- **Búsqueda por voz progresiva (`🎙️`)** en `/buscar/` (Web Speech API `es-CO`).

## [1.4.0] - 2026-11-21
### Agregado
- **Portada interactiva estilo ciudad ecológica (inspirada en CiudadReporta)**:
  - Fondo isométrico nocturno en tonos esmeralda, píldoras interactivas de las 4 rutas de separación (`Bolsa Blanca`, `Bolsa Negra`, `Bolsa Verde`, `Posconsumo`), acceso directo **«Explorar sin cuenta»**, y **Escarlata volando** con mensajes dinámicos de sensibilización ambiental.
  - **Ubicación en vivo privada** en la portada (`watchPosition` solo en el navegador, sin enviar coordenadas al servidor) que muestra en tiempo real el punto posconsumo oficial más cercano.
- **Trivia educativa y adictiva con 3 modos + Medallas 3D**:
  - Modos **Carrera por Niveles**, **¿En qué bolsa va?** (reto rápido) y **Mitos vs. Realidad** (12 preguntas nuevas; total 32 preguntas en base de datos).
  - Indicador de **Racha** en vivo durante la partida y **medallas ecológicas reales en 3D** con giro y celebración **«¡Felicidades, pasaste de nivel!»** al superar un nivel o desbloquear insignias por puntos.

## [1.3.1] - 2026-11-21
### Agregado
- **Centro de Sugerencias Ciudadanas (`/sugerencias/`)** estilo CiudadReporta: página dedicada para proponer residuos nuevos, reportar puntos o sugerir mejoras, con tablero transparente de aportes recientes (anónimo, RN-08) y seguimiento de estado (`Pendiente` / `Atendida` / `Descartada`) en «Mi cuenta».
- **Compartir la app EcoParce**: botones para compartir el enlace de la aplicación (hoja nativa del dispositivo / copiar enlace + WhatsApp) en la pantalla de inicio (`/`) y en los resultados de la trivia (`/trivia/resultado/`).

## [1.3.0] - 2026-11-21
### Agregado
- **Trivia con dificultad progresiva e insignias estrictamente por puntos**:
  - Nivel 1 (*Semilla Verde*, dificultad Fácil, meta 3/5), Nivel 2 (*Guardián del Reciclaje*, dificultad Media, meta 4/5) y Nivel 3 (*Maestro Guacamaya*, dificultad Difícil, meta 5/5).
  - Ampliado el banco inicial de preguntas a 20 preguntas (8 Fácil, 6 Media, 6 Difícil) para cubrir todos los niveles sin repeticiones forzadas.
  - Modelo `InsigniaUsuario` en base de datos con 6 insignias ecológicas otorgadas exclusivamente según puntos obtenidos/acumulados.
- **Privacidad, cumplimiento legal y transparencia**:
  - Política de privacidad ampliada (tabla de tiempos de conservación, proveedores/subencargados con acuerdos DPA, permiso parental, transparencia de IA, declaración honesta sin SOC 2).
  - Términos y condiciones completos (sin cargos ocultos ni renovaciones automáticas, disponibilidad realista, canal de derechos de autor `derechos@ecoparce.com.co`, soporte `soporte@ecoparce.com.co`).
  - Nueva página `/licencias/` con licencias open source, atribuciones de datos/fuentes y auditoría de SDKs y rastreadores.
  - Permiso independiente opcional para novedades por correo (`Consentimiento.acepta_marketing`), enlace de baja en correos y vista `/cuenta/comunicaciones/`.
  - Banner de consentimiento de cookies sin patrones engañosos con bloqueo previo de teselas externas de OpenStreetMap hasta aceptación.
- **Accesibilidad, SEO y PWA**:
  - Modo de Alto Contraste (WCAG AAA), `aria-current="page"`, textos alternativos descriptivos, etiqueta visible de ilustración asistida con IA y navegación con teclado.
  - `manifest.webmanifest`, `/robots.txt`, `/sitemap.xml` (respetando RN-01) y hoja de impresión `@media print`.
- **Control de versiones**: repositorio Git inicializado con rama `main`, archivo `VERSION`, `CHANGELOG.md` y etiqueta `v1.3.0`.

### Corregido
- Corrección de bug de *bfcache* en `ecoparce.js` (botones de envío que quedaban deshabilitados al navegar hacia atrás).
- Manejo de errores de red en `puntos.js` y `escaner.js`, y reemplazo de emojis por iconos SVG consistentes en el mapa.
- Eliminación de carpeta residual `_to_delete/`.

## [1.2.0] - 2026-11-18
- Escáner de códigos de barras (BarcodeDetector / ZXing + Open Food Facts) en `/escanear/` (RF-16).
- Mapa de puntos posconsumo oficiales de la Secretaría Distrital de Ambiente en `/puntos/` (RF-17).

## [1.1.0] - 2026-11-10
- Cuentas opcionales de visitante (correo con código de verificación y Google OIDC con PKCE), verificación en dos pasos (TOTP) obligatoria para el panel, consentimiento Ley 1581, descarga JSON y supresión de cuenta.

## [1.0.0] - 2026-10-28
- Versión inicial: guías de separación (Resolución 2184 de 2019), buscador de residuos, códigos QR, trivia básica, panel editorial con revisión (RN-01 a RN-10) y estadísticas anónimas.
