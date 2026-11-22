# Registro de cambios (CHANGELOG) · EcoParce

Este proyecto sigue el [Versionado Semántico (SemVer 2.0.0)](https://semver.org/lang/es/) y control de versiones en Git.

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
