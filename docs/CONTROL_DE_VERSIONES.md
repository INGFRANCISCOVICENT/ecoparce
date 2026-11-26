# Documento de Control de Versiones y Gestión de Configuración — EcoParce

| Campo | Valor |
|---|---|
| **Proyecto** | EcoParce · Sistema Web Educativo de Reciclaje y Manejo de Residuos |
| **Institución / Curso** | Politécnico Internacional · Calidad de Software (Docente: Camilo Ramírez) |
| **Equipo responsable** | Francisco Jesús Navarro Vicent · Danixa Alexandra Herrera Nimisaca · Darien García Morales |
| **Versión vigente** | **2.9.5** (`VERSION` = `2.9.5`) |
| **Fecha de actualización** | 2026-11-26 |
| **Estándar aplicado** | SemVer 2.0.0 · Keep a Changelog · CMMI Nivel 2 (Área de Proceso: Gestión de Configuración — CM) · ISO/IEC 25010 |

---

## 1. Propósito y Alcance

Este documento establece el control formal de versiones, la trazabilidad de cambios funcionales, de seguridad, de base de datos y de arquitectura de **EcoParce**, desde su línea base inicial (`v1.0.0`) hasta la versión actual (`v2.9.0`).

Los artefactos bajo control de configuración son:
- Código fuente Python/Django (`apps/`, `config/`, `templates/`, `static/`).
- Esquema de base de datos y migraciones (`apps/*/migrations/`) + script RLS (`docs/rls_postgresql.sql`).
- Dependencias congeladas (`requirements.txt`, `requirements-render.txt`, `requirements-dev.txt`, `requirements.lock`).
- Configuración de despliegue e integración continua (`render.yaml`, `build.sh`, `.github/workflows/seguridad-y-pruebas.yml`).
- Archivo de versión única (`VERSION`), historial (`CHANGELOG.md`) y vista en vivo `/panel/versiones/`.

---

## 2. Política de Versionado (SemVer 2.0.0)

Cada lanzamiento sigue el formato **`MAYOR.MENOR.PARCHE`** (ej. `2.9.0`):

| Segmento | Cuándo se incrementa | Ejemplo en EcoParce |
|---|---|---|
| **MAYOR (`X.0.0`)** | Cambios de arquitectura, plataforma o evolución mayor de producto | `1.0.0` → `2.2.0` (experiencias interactivas Canvas/Arcade/Voz) |
| **MENOR (`X.Y.0`)** | Nuevas funcionalidades, módulos o controles de seguridad retrocompatibles | `2.8.0` → `2.9.0` (API Gateway, OAuth 2.0 JWT, RLS, E2E AES-256-GCM, PWA) |
| **PARCHE (`X.Y.Z`)** | Corrección de errores, parches de seguridad o ajustes menores de UI | `2.6.0` → `2.6.1` (ajuste de altura EcoBot en móviles) |

### Reglas de Control de Cambios (CMMI Nivel 2 — CM)
1. **Repositorio privado en GitHub** con rama principal `main` protegida; `.env` y secretos excluidos por `.gitignore`.
2. **Versionado sincronizado:** al liberar una versión se actualiza `VERSION`, `CHANGELOG.md` y se ejecuta `collectstatic`, lo que invalida automáticamente caché del navegador (`?v=X.Y.Z`), endpoint `/version.json` y caché del Service Worker (`/sw.js`).
3. **Compuertas de calidad obligatorias antes de liberar:**
   - `python manage.py test` (100 % pruebas aprobadas).
   - `python manage.py makemigrations --check --dry-run` (sin migraciones pendientes).
   - `python manage.py check --deploy` (0 errores / 0 advertencias críticas).
   - `bandit -r apps config` y `pip-audit -r requirements.lock` (CI en `.github/workflows/seguridad-y-pruebas.yml`).

---

## 3. Historial Consolidado de Versiones

| Versión | Fecha | Tipo | Resumen de cambios principales | Impacto en BD / Seguridad | Estado |
|---|---|---|---|---|---|
| **1.0.0** | 2026-10-28 | Mayor | Línea base: guías de separación (Res. 2184 de 2019), buscador de residuos, códigos QR, trivia básica, panel editorial con revisión (RN-01..RN-10) y estadísticas anónimas. | Migraciones iniciales (`0001_initial`) y contenedores fijos (`0002_contenedores`). | Liberada |
| **1.1.0** | 2026-11-10 | Menor | Cuentas opcionales de visitante, ingreso con Google (OIDC + PKCE), verificación en dos pasos (2FA TOTP) obligatoria en `/panel/`, consentimiento Ley 1581, exportación JSON y supresión de cuenta. | `cuentas/0002`, `cuentas/0003`, Argon2id y cifrado MultiFernet para secretos TOTP. | Liberada |
| **1.2.0** | 2026-11-18 | Menor | Escáner de códigos de barras (BarcodeDetector / ZXing + Open Food Facts, RF-16) y mapa de puntos posconsumo oficiales de la SDA Bogotá (RF-17). | `contenidos/0003_puntos_oficiales`. Consultas remotas únicamente desde servidor. | Liberada |
| **1.3.0** | 2026-11-21 | Menor | Trivia por niveles e insignias por puntos (`InsigniaUsuario`), política de privacidad ampliada, `/licencias/`, `/cuenta/comunicaciones/`, banner de cookies, Alto Contraste WCAG AAA, `manifest.webmanifest`, SEO y repositorio Git. | `cuentas/0004`, `trivia/0003`. Bloqueo previo de teselas OpenStreetMap sin consentimiento. | Liberada |
| **1.3.1** | 2026-11-21 | Parche | Centro de Sugerencias Ciudadanas (`/sugerencias/`) y botones para compartir EcoParce (hoja nativa y WhatsApp). | Sin cambio de esquema. Límite por sesión y campo trampa anti-bots. | Liberada |
| **1.4.0** | 2026-11-21 | Menor | Portada interactiva nocturna con Escarlata volando, ubicación privada en navegador (`watchPosition`), 3 modos de trivia, racha y medallas 3D. | `trivia/0004_partidatrivia_modo_preguntatrivia_categoria`. | Liberada |
| **2.2.0** | 2026-11-22 | Mayor | Video educativo interactivo HTML5 Canvas con pausas de reto, simulador Arcade «Atrapa y Separa 30 s», Reto Diario con racha, Certificado Digital PNG HD y búsqueda por voz (`es-CO`). | 100 % compatible con CSP estricta (sin scripts inline ni CDN). | Liberada |
| **2.3.0** | 2026-11-22 | Menor | Infografía de Economía Circular, tarjetas 3D «Mitos vs. Realidad», checklist de cocina y comparativa visual «Sí va vs. No va». | Sin cambio de esquema. | Liberada |
| **2.3.1** | 2026-11-22 | Parche | Política estricta de contraseñas (`ClaveSeguraValidator`, mínimo 9 caracteres, mayúscula, minúscula, número y símbolo) con medidor visual en tiempo real. | Refuerzo de validación en servidor y cliente. | Liberada |
| **2.4.0** | 2026-11-22 | Menor | Endpoint `/version.json`, banner automático «Actualizar ahora», panel `/panel/versiones/` y crédito oficial de marca del equipo. | Control de versiones visible para administradores. | Liberada |
| **2.4.1** | 2026-11-22 | Parche | Rediseño del medidor de contraseña y limpieza de etiquetas en portada. | Sin cambio de esquema. | Liberada |
| **2.4.2** | 2026-11-22 | Parche | Limpieza de jerarquía visual en página de inicio. | Sin cambio de esquema. | Liberada |
| **2.5.0** | 2026-11-22 | Menor | Asistente experto flotante «Escarlata · Consultor EcoParce» y `Cache-Control: no-cache` en HTML público. | Permiso `microphone=(self)` para búsqueda por voz. | Liberada |
| **2.6.0** | 2026-11-22 | Menor | EcoBot conectado en tiempo real a BD oficial (`/asistente/consultar/`), healthcheck `/health/`, `render.yaml` y endurecimiento de despliegue. | Rate-limiting 45 req/min, renderizado DOM seguro contra XSS, límite POST 2.5 MB. | Liberada |
| **2.6.1** | 2026-11-22 | Parche | Ajuste de altura adaptable del chat EcoBot en pantallas móviles (`100dvh`). | Sin cambio de esquema. | Liberada |
| **2.7.0** | 2026-11-22 | Menor | Autocompletado instantáneo `/buscar/autocompletar/`, soporte progresivo de instalación PWA y sanitización contra CSV Formula Injection. | Protección OWASP CSV Injection en exportación de estadísticas. | Liberada |
| **2.8.0** | 2026-11-23 | Menor | Generador interactivo de Carteles y Etiquetas HD para Canecas en Canvas HTML5 (`/guias/`). | 100 % local en navegador, compatible con CSP estricta. | Liberada |
| **2.9.0** | 2026-11-26 | Menor | **API Gateway (`GET`/`POST`, WAF, API Keys SHA-256, bitácora inmutable)**, **OAuth 2.0 JWT endurecido (RFC 6749/7519/7009/7662/8414/8725/9700)** con rotación y detección de reutilización, **cifrado de cuentas MultiFernet + `correo_hash` + E2E AES-256-GCM**, **32 políticas RLS granulares sin reglas abiertas**, tablero `/panel/calidad/`, **OpenAPI 3.0.3**, **PWA E2E** (`/sw.js`, `/offline/`, iconos `192×192` y `512×512`) y fondo animado **Aurora Boreal verde**. | `api/0001_initial`, `cuentas/0006`, `docs/rls_postgresql.sql`. **120/120 pruebas OK**, `check --deploy` 0 advertencias. | Liberada |
| **2.9.1** | 2026-11-26 | Parche | **Corrección del escáner QR y códigos de barras (`/escanear/`)**: soporte multi-dominio para QR de EcoParce (`/q/XXXXXXXX`), extracción automática de GTIN en QR GS1 Digital Link, consulta automática al catálogo para QR de texto, tarjeta informativa con enlace seguro para QR externos y detención limpia de cámara. | Sin cambio de esquema. Versionado `?v=` de `escaner.js` y `collectstatic` actualizado. | Liberada |
| **2.9.5** | 2026-11-26 | Parche (Vigente) | **Escaneo de productos por foto (`/escanear/foto/`)** sin depender de códigos en BD (análisis visual local con Pillow en memoria + soporte opcional **Gemini Vision**), **corrección de contraste** en `/privacidad/`, `/terminos/`, `/licencias/` y banner de cookies (contraste normal y alto contraste WCAG AAA), corrección de redirección de registro para visitantes y estabilización de despliegue en Render (`build.sh` y `requirements-render.txt`). | Sin cambio de esquema. CSP ampliada con `blob:` para vista previa local, **122 pruebas automatizadas OK**. | **Activa** |

---

## 4. Trazabilidad de Esquema y Migraciones Vigentes

| Aplicación | Última migración | Propósito principal |
|---|---|---|
| `cuentas` | `0006_usuario_correo_hash_alter_solicitudadmin_motivo_and_more` | Cifrado MultiFernet en `Usuario.nombre` y `SolicitudAdmin.motivo` + huella ciega `correo_hash` |
| `api` | `0001_initial` | Tablas `api_clave` (hash SHA-256) y `api_gateway_log` (bitácora inmutable del Gateway) |
| `auditoria` | `0001_initial` | Tabla `registro_auditoria` inmutable |
| `contenidos` | `0003_puntos_oficiales` | Contenedores Res. 2184, guías revisables, residuos y puntos oficiales SDA |
| `buscador` | `0002_cuentas_google_y_visitantes` | Búsquedas anónimas (RN-08) y sugerencias ciudadanas |
| `qr` | `0001_initial` | Instituciones, códigos QR con `RESTRICT` (RN-10) y escaneos anónimos |
| `trivia` | `0004_partidatrivia_modo_preguntatrivia_categoria` | Banco de preguntas, modos, niveles e insignias 3D |

---

## 5. Verificación de Calidad de la Línea Base Vigente (`v2.9.5`)

| Control de calidad | Herramienta / Comando | Resultado |
|---|---|---|
| Pruebas unitarias, de integración y seguridad E2E | `python manage.py test` | **122 / 122 OK** (`0` fallos, `0` errores) |
| Integridad de migraciones | `python manage.py makemigrations --check --dry-run` | **0 migraciones pendientes** |
| Auditoría de despliegue Django | `python manage.py check --deploy` | **0 errores / 0 advertencias** |
| Diagnóstico integral y APIs remotas | `python manage.py verificar_sistema --probar-remoto` | **5/5 cuentas cifradas · Open Food Facts 200 OK · SDA Bogotá 200 OK** |
| Complejidad ciclomática promedio (McCabe) | Análisis AST (452+ funciones) | **2.85** (umbral recomendado ≤ 10) |
| Políticas RLS PostgreSQL | `docs/rls_postgresql.sql` | **32 políticas granulares** (`0` reglas abiertas `true`) |

---

## 6. Control de Aprobación

| Rol | Responsable | Versión revisada | Estado |
|---|---|---|---|
| Líder de Desarrollo y Seguridad | Francisco Jesús Navarro Vicent | `2.9.5` | Aprobado |
| Gestión de Contenidos y Calidad | Danixa Alexandra Herrera Nimisaca | `2.9.5` | Aprobado |
| Arquitectura y Pruebas | Darien García Morales | `2.9.5` | Aprobado |
| Evaluación Académica (Calidad de Software) | Prof. Camilo Ramírez | `2.9.5` | En revisión |
