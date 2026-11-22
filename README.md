# EcoParce · Sistema de reciclaje y manejo de residuos

Aplicación web educativa, pensada para teléfono y tablet, que enseña a separar en la fuente con el código de colores de la **Resolución 2184 de 2019** (bolsa blanca, negra y verde) y a entregar los residuos especiales en puntos posconsumo. Se accede escaneando códigos QR y la guía a los visitantes Escarlata, una guacamaya roja (*Ara macao*).

Proyecto del curso **Calidad de Software** (docente: Camilo Ramírez), Politécnico Internacional.
Equipo: Francisco Jesús Navarro Vicent · Danixa Alexandra Herrera Nimisaca · Darien García Morales.

---

## 1. Tecnología

| Capa | Elección |
|---|---|
| Lenguaje | Python 3.12 o superior |
| Framework | Django 5.2 LTS (soporte hasta abril de 2028), patrón MVT, monolito modular |
| Base de datos | MySQL 8.0 en producción · SQLite para desarrollo y pruebas |
| Cuentas | django-allauth 65: correo + contraseña con **verificación por código**, **ingreso con Google** (OpenID Connect + PKCE) y **verificación en dos pasos (TOTP)** obligatoria para administradores |
| Seguridad | Argon2id, secretos TOTP cifrados, CSP, HSTS, cookies `__Host-`, límites de intentos, auditoría. Detalle en `docs/SEGURIDAD.md` |
| QR | qrcode + Pillow (PNG y SVG) |
| Hosting | PythonAnywhere Developer + dominio `ecoparce.com.co` en GoDaddy |

No usa frameworks de JavaScript ni CDN: las fuentes (Nunito, Baloo 2) y los iconos se sirven desde el propio sitio, y la página funciona aunque JavaScript esté apagado.

## 2. Estructura

```
ecoparce/
├── config/                 configuración (settings base/local/produccion, urls, wsgi)
├── apps/
│   ├── core/               inicio, páginas legales, errores, middleware de seguridad, iconos
│   ├── cuentas/            Usuario (VISITANTE/CONTENIDO/SISTEMA), Google, 2FA, autorización de datos, Mi cuenta
│   ├── auditoria/          RegistroAuditoria inmutable
│   ├── contenidos/         Contenedor, Guia, Residuo, PuntoEntrega + flujo de revisión
│   ├── buscador/           Busqueda (anónima), Sugerencia
│   ├── qr/                 Institucion, CodigoQR, Escaneo + redirección /q/<código>
│   ├── trivia/             PreguntaTrivia, OpcionTrivia, PartidaTrivia, RespuestaPartida
│   └── estadisticas/       resumen del panel, estadísticas y exportación CSV
├── templates/              plantillas base del sitio y del panel
├── static/                 css, js, fuentes e imágenes
├── .github/workflows/      pruebas, Bandit, pip-audit y check --deploy en cada cambio
└── docs/                   SEGURIDAD.md, GOOGLE_Y_CORREO.md, WSGI de PythonAnywhere, respaldo y capturas
```

## 3. Instalación local (5 minutos, con SQLite)

```bash
python -m venv venv
source venv/bin/activate            # En Windows: venv\Scripts\activate
pip install -r requirements.txt     # en Windows, si mysqlclient falla, quítelo: con SQLite no se necesita
cp .env.ejemplo .env                # deja DB_ENGINE=sqlite

python manage.py migrate
python manage.py createsuperuser    # crea el administrador del sistema (pide correo, nombre y contraseña)
python manage.py runserver
```

**En Windows, lo más fácil:** copie `INICIAR_ECOPARCE.bat` junto a la carpeta `ecoparce` y dele doble clic. Instala todo, crea datos de demostración, descarga los puntos oficiales y abre el servidor en http://127.0.0.1:8000/.

En local, los correos con códigos de verificación se imprimen en la consola donde corre `runserver`. Para probar Google en local, cree un cliente de desarrollo (ver `docs/GOOGLE_Y_CORREO.md`) y ponga `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en el `.env`.

La primera vez que el administrador abre `/panel/`, el sistema le pide aceptar el aviso de privacidad y **activar la verificación en dos pasos** con una app como Google Authenticator. Sin eso no entra al panel.

Para cargar el contenido inicial se necesitan dos administradores distintos (autor y revisor, RN-03). Cree el segundo desde **Panel → Administradores → Nuevo administrador** o con `createsuperuser`, y luego:

```bash
python manage.py cargar_contenido_inicial --autor correo1@ejemplo.com --revisor correo2@ejemplo.com
python manage.py cargar_contenido_inicial --autor ... --revisor ... --demo   # además, puntos e institución de ejemplo
```

Carga 10 guías, 36 residuos con sinónimos y 15 preguntas de trivia, todo publicado y con su fuente oficial. Es idempotente.

- Sitio público: http://127.0.0.1:8000/
- Panel: http://127.0.0.1:8000/panel/

## 4. Pruebas automatizadas

```bash
python manage.py test
```

91 pruebas cubren las reglas de negocio (RN-01 a RN-10), el flujo de revisión, el buscador, el QR, la trivia, los permisos por rol y la seguridad de las cuentas: registro con código, Google (token de otra app, correo no verificado, `state` falso, PKCE), 2FA del panel, reautenticación, bloqueo por intentos, redirecciones abiertas, exportación y eliminación de datos; además la sincronización de puntos oficiales y el escáner (con respuestas simuladas de las APIs). Se ejecutaron con éxito en SQLite y en MySQL 8.0.

Análisis de seguridad: `bandit -r apps config` (0 hallazgos) y `pip-audit -r requirements.lock` (sin vulnerabilidades conocidas). Instale las herramientas con `pip install -r requirements-dev.txt`.

## 5. Módulos y requisitos

| Requisito | Dónde está |
|---|---|
| RF-01 Acceso por QR | `apps/qr/views.py` → `/q/<código>` |
| RF-02 Guía de colores | `apps/contenidos/views.py` → `/guias/` |
| RF-03 Buscador (nombre o sinónimo, sin tildes) | `apps/buscador/views.py`, `apps/core/texto.py` |
| RF-04 Residuos especiales | `/manejo/` |
| RF-05 Inicio de sesión | django-allauth: correo con código, Google, 2FA; `apps/cuentas/adaptadores.py` y `middleware.py` |
| RF-06 Contenidos con revisión | `apps/contenidos/views_panel.py`, `ContenidoRevisable` |
| RF-07 Generar QR PNG/SVG | `apps/qr/views_panel.py`, `CodigoQR.generar_imagen()` |
| RF-08 Trivia de 5 preguntas | `apps/trivia/views.py` |
| RF-09 Gestionar preguntas | `apps/trivia/views_panel.py` |
| RF-10 Registro anónimo de uso | modelos `Escaneo` y `Busqueda` |
| RF-11 Estadísticas | `apps/estadisticas/` (+ exportación CSV) |
| RF-12 Puntos de entrega | `/manejo/` y panel de puntos |
| RF-13 Sugerir residuo | `/sugerencias/` (límite por sesión y campo trampa contra robots) |
| RF-14 Compartir guía | botón Compartir (hoja nativa del teléfono) y WhatsApp |
| RF-15 Gestionar administradores | `/panel/usuarios/` (autorizar correos de Google, roles, desactivar, restablecer 2FA) |
| Cuenta del visitante | `/cuenta/`: progreso, sugerencias, descargar datos, eliminar cuenta |
| RF-16 Escanear producto | `/escanear/`: cámara (BarcodeDetector o ZXing) + Open Food Facts → bolsa por cada parte del empaque |
| RF-17 Mapa de puntos oficiales | `/puntos/`: 1.804 puntos de la Secretaría Distrital de Ambiente, filtros y «más cercanos a mí» |

Los cambios de la versión 1.2 frente al documento técnico (requisitos nuevos, APIs externas, privacidad y modelo de datos) están en **`docs/CAMBIOS_V1.2.md`**.

| Regla | Implementación |
|---|---|
| RN-01 El público solo ve lo publicado | `Guia.publicadas`, filtros por `PUBLICADO` en vistas y buscador |
| RN-02 Fuente oficial obligatoria | `enviar_a_revision()` |
| RN-03 Revisor distinto del autor | `Usuario.puede_publicar()` + restricción CHECK en la base de datos |
| RN-04 Código de colores fijo | migración `contenidos/0002_contenedores` |
| RN-05 Especial → punto posconsumo | `ResiduoForm.clean()` |
| RN-06 QR desactivado se conserva | activar/desactivar, sin borrado; muestra «código no disponible» |
| RN-07 2 a 4 opciones, una correcta | `PreguntaTrivia.errores()` y `OpcionesForm` |
| RN-08 Registros anónimos | `Escaneo` y `Busqueda` sin IP ni datos personales |
| RN-09 Funciones exclusivas del admin del sistema | decorador `sistema_requerido` |
| RN-10 Guía con QR no se elimina | `on_delete=RESTRICT` en `CodigoQR.guia` |

## 6. Despliegue en PythonAnywhere + GoDaddy

1. **Código**: en una consola Bash de PythonAnywhere, suba el proyecto (git clone o subir el ZIP y `unzip`) en `/home/usuario/ecoparce`.
2. **Entorno virtual**:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.12 ecoparce
   pip install -r ~/ecoparce/requirements.lock
   ```
3. **Base de datos**: pestaña *Databases* → defina la contraseña de MySQL y cree la base `ecoparce` (queda como `usuario$ecoparce`). En la consola MySQL:
   `ALTER DATABASE \`usuario$ecoparce\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;`
4. **Variables de entorno**: cree `~/ecoparce/.env` a partir de `.env.ejemplo`. Genere las claves con `python manage.py generar_claves` y complete MySQL, Google y el correo (guía paso a paso en `docs/GOOGLE_Y_CORREO.md`). Permisos: `chmod 600 .env`. Si falta una variable obligatoria, la aplicación no arranca y dice cuál.
5. **Preparar**:
   ```bash
   cd ~/ecoparce
   python manage.py migrate
   python manage.py createcachetable      # caché compartida para los límites de intentos
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   python manage.py sincronizar_puntos_sda   # carga los puntos posconsumo oficiales de Bogotá
   python manage.py check --deploy
   ```
6. **Web app**: pestaña *Web* → *Add a new web app* → dominio `www.ecoparce.com.co` → *Manual configuration* → Python 3.12.
   - *Virtualenv*: `/home/usuario/.virtualenvs/ecoparce`
   - *WSGI configuration file*: reemplace su contenido por `docs/pythonanywhere_wsgi.py` (cambiando `usuario`).
   - *Static files*: URL `/static/` → directorio `/home/usuario/ecoparce/staticfiles`
   - *Reload*.
7. **GoDaddy (DNS)**: registro **CNAME** `www` → el valor `webapp-XXXX.pythonanywhere.com` que muestra la pestaña Web. Configure el reenvío (*forwarding*) del dominio raíz `ecoparce.com.co` a `https://www.ecoparce.com.co` (301 permanente).
8. **HTTPS**: en la pestaña Web, active el certificado *Let's Encrypt* con renovación automática y luego *Force HTTPS*.
9. **Tareas programadas** (*Tasks*):
   - semanal: `bash ~/ecoparce/docs/respaldo_semanal.sh` (respaldo con mysqldump; credenciales en `~/.my.cnf`)
   - semanal: `cd ~/ecoparce && ~/.virtualenvs/ecoparce/bin/python manage.py sincronizar_puntos_sda` (puntos oficiales de la SDA)
   - mensual: `cd ~/ecoparce && ~/.virtualenvs/ecoparce/bin/python manage.py depurar_registros_uso` (retención de 24 meses)

Después de cada cambio de código: `git pull`, `migrate`, `collectstatic` y *Reload*.

## 7. Seguridad aplicada

Resumen (el análisis completo, con modelo de amenazas, OWASP Top 10:2025 y resultados de pruebas, está en **`docs/SEGURIDAD.md`**):

- Dos formas de entrar, como en CiudadReporta: **correo + contraseña con código de verificación** enviado al correo (y comprobación MX del dominio), o **Google** validando emisor, audiencia, vencimiento y correo verificado del token, con `state` y PKCE.
- Toda cuenta nueva es **visitante**. Solo el administrador del sistema autoriza administradores.
- **Verificación en dos pasos obligatoria** para el panel; secreto TOTP cifrado en la base de datos; códigos de recuperación.
- Reautenticación para acciones sensibles; cierre de sesiones al desactivar o cambiar de rol; 30 minutos de inactividad en el panel.
- Argon2id; bloqueo tras 5 intentos fallidos; recuperación de contraseña por código; alertas por correo.
- Cookies `__Host-` seguras, HSTS, CSP estricta, `X-Frame-Options: DENY`, `security.txt`.
- Autorización de datos con fecha y versión (Ley 1581), descarga de datos y eliminación de la cuenta.
- CI con pruebas, Bandit, pip-audit, `check --deploy` y búsqueda de secretos filtrados.

## 8. Diferencias con el documento de diseño

- `partida_trivia.preguntas_ids`: columna adicional que guarda el orden de las 5 preguntas sorteadas, para que la partida no cambie si el visitante recarga la página.
- `residuo_punto.id`: Django usa una clave primaria propia en la tabla intermedia; la unicidad (`residuo`, `punto`) se mantiene con `uq_residuo_punto`.
- El buscador normaliza en Python (sin tildes, sin mayúsculas, por sinónimos) en lugar de un índice FULLTEXT: con menos de mil residuos responde en milisegundos y se comporta igual en SQLite y MySQL.
- **Cuentas de visitante (versión 1.1):** el diseño original no tenía cuentas para visitantes. Ahora son opcionales: navegar, buscar y jugar sigue sin cuenta, y los registros de uso siguen anónimos (RN-08). Se agregan la tabla `consentimiento`, el rol `VISITANTE`, `partida_trivia.usuario` y `sugerencia.usuario`, más las tablas de django-allauth (`account_emailaddress`, `socialaccount_socialaccount`, `mfa_authenticator`) y la caché `cache_ecoparce`.
- El bloqueo por intentos lo hace django-allauth (por cuenta y por IP), en lugar de django-axes.
- MySQL 8.0 llegó al fin de soporte en abril de 2026 (riesgo R-09). El código funciona igual en MySQL 8.4 LTS cuando PythonAnywhere lo ofrezca.
