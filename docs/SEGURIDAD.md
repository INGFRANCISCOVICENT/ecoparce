# EcoParce · Auditoría de ciberseguridad, autenticación y protección de datos

**Versión:** 1.1 (21 de noviembre de 2026) · **Alcance:** aplicación web Django 5.2 LTS, despliegue en PythonAnywhere con dominio `www.ecoparce.com.co`
**Marco de referencia:** OWASP Top 10:2025, OWASP ASVS 4.0 (niveles 1 y 2), NIST SP 800-63B (autenticadores), Ley 1581 de 2012 y Decreto 1074 de 2015.

La lógica de autenticación sigue la de **CiudadReporta v1.1**: dos formas de entrar —correo y contraseña con verificación real del correo por código, o Google con verificación del token— y cuentas nuevas siempre con el rol de menor privilegio. La diferencia es de arquitectura: CiudadReporta es una API (NestJS) con tokens JWT para la app Android; EcoParce es una aplicación web renderizada en el servidor, así que usa **sesiones del lado del servidor** y el flujo OAuth 2.0 *Authorization Code* con **PKCE**, que es la opción que recomienda Google y la IETF para aplicaciones web con servidor propio.

---

## 1. Modelo de amenazas (STRIDE)

| Activo | Amenaza | Categoría | Control en EcoParce |
|---|---|---|---|
| Panel de administración | Robo de contraseña o phishing del administrador | Suplantación | Verificación en dos pasos (TOTP) **obligatoria** para entrar al panel; la sesión debe haber pasado el código; opcional `PANEL_SOLO_GOOGLE=1` |
| Cuentas de visitantes | Fuerza bruta, relleno de credenciales | Suplantación | 5 intentos fallidos por cuenta en 15 min y por IP en 5 min; Argon2id; contraseñas de 10+ caracteres y no comunes |
| Ingreso con Google | Token de otra app, CSRF de login, código interceptado | Suplantación | Se valida emisor, audiencia (client_id), vencimiento y `email_verified`; `state` + PKCE S256; el flujo solo arranca por POST con token CSRF |
| Correo del registro | Registrar el correo de otra persona (pre-secuestro de cuenta) | Suplantación | Verificación obligatoria por código; si el dueño real entra con Google, se borra la contraseña de la cuenta no verificada |
| Contenido publicado | Que un autor publique sin revisión | Manipulación | RN-03 en código y en restricción CHECK de la base de datos |
| Estadísticas | Inflar lecturas de QR o búsquedas | Manipulación | Una lectura por persona y QR cada 10 min; tope de 120 búsquedas registradas por hora; sin guardar IP |
| Acciones administrativas | Negar haber hecho un cambio | Repudio | Auditoría inmutable (no se puede editar ni borrar desde la aplicación) y eventos de seguridad en el log |
| Datos personales | Fuga de la base de datos | Divulgación | Contraseñas con Argon2id; secretos TOTP cifrados con Fernet (AES-128-CBC + HMAC-SHA256); no se guardan tokens de Google; minimización de datos |
| Sesión | Robo de cookie, fijación de sesión | Divulgación | Cookies `__Host-`, `Secure`, `HttpOnly`, `SameSite=Lax`; rotación del identificador al ingresar; cierre al cerrar el navegador; 30 min de inactividad en el panel |
| Sitio público | Spam de sugerencias, abuso automatizado | Denegación | Límite por sesión y por huella temporal de red; campo trampa; límites de allauth en todos los formularios de cuenta |
| Roles | Visitante que llega al panel; admin de contenido que gestiona QR o usuarios | Elevación | Control centralizado en middleware + decoradores por vista (`panel_requerido`, `sistema_requerido`); 403 probado |

---

## 2. Controles por categoría del OWASP Top 10:2025

| Categoría | Controles implementados | Dónde |
|---|---|---|
| **A01 Control de acceso roto** | Middleware `ControlAccesoMiddleware` (consentimiento, rol, 2FA, inactividad) + decoradores por vista; acciones de estado solo por POST; protección de redirecciones abiertas con `url_has_allowed_host_and_scheme`; cierre forzado de sesiones al desactivar o cambiar de rol | `apps/cuentas/middleware.py`, `apps/core/permisos.py`, `apps/cuentas/sesiones.py` |
| **A02 Configuración incorrecta** | `DEBUG=False`, `ALLOWED_HOSTS` explícito, HSTS 1 año, `SECURE_SSL_REDIRECT`, CSP sin `unsafe-inline` en scripts, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `COOP`, `CORP`; `check --deploy` sin advertencias; flujos de allauth que no se usan devuelven 404 | `config/settings/produccion.py`, `apps/core/middleware.py`, `config/urls.py` |
| **A03 Cadena de suministro** | Dependencias con versión exacta (`requirements.lock`); `pip-audit` sin vulnerabilidades conocidas; revisión semanal automática en GitHub Actions; sin CDN ni scripts de terceros (fuentes e iconos propios) | `requirements*.txt`, `.github/workflows/` |
| **A04 Fallas criptográficas** | Argon2id para contraseñas; Fernet para secretos TOTP con rotación (`MultiFernet`); `SECRET_KEY_FALLBACKS` para rotar sin cerrar sesiones; HTTPS obligatorio; códigos aleatorios con `secrets` | `config/settings/base.py`, `apps/cuentas/mfa_adapter.py` |
| **A05 Inyección** | ORM de Django (consultas parametrizadas); escape automático de plantillas; los iconos SVG validan tamaño y color; CSP como segunda barrera contra XSS | `apps/core/templatetags/eco.py` |
| **A06 Diseño inseguro** | Mínimo privilegio (toda cuenta nueva es VISITANTE; solo el admin del sistema autoriza administradores); reautenticación para acciones sensibles; RN-03 en dos capas | `apps/cuentas/adaptadores.py`, `apps/cuentas/views.py` |
| **A07 Fallas de autenticación** | Ver sección 3 | `apps/cuentas/` |
| **A08 Integridad de software y datos** | Auditoría inmutable; migraciones versionadas y verificadas en CI (`makemigrations --check`); estados del contenido con transiciones validadas | `apps/auditoria/models.py` |
| **A09 Fallas de registro y alertas** | Logger `ecoparce.seguridad` con eventos (`login_ok`, `login_fallido`, `mfa_codigo_incorrecto`, `mfa_restablecida_por_admin`, `cuenta_eliminada`...); alerta por correo al usuario cuando cambia su contraseña o su 2FA | `apps/cuentas/signals.py`, `apps/core/seguridad.py` |
| **A10 Manejo de condiciones excepcionales** | Páginas 403/404/500 propias sin trazas; fallos de DNS no bloquean el registro; errores de Google se muestran sin detalles internos; límites de tiempo en llamadas externas (10 s Google, 15 s SMTP) | `apps/core/views.py`, `apps/cuentas/forms.py` |

---

## 3. Autenticación en detalle

### 3.1 Registro con correo (igual que CiudadReporta)
1. Nombre, correo, contraseña (dos veces) y **dos casillas sin marcar**: autorización de datos y declaración de edad o permiso del acudiente.
2. Se comprueba que el dominio del correo tenga registros **MX** reales.
3. Se envía un **código de 8 caracteres** al correo. Vence en 15 minutos y admite 5 intentos; sin él no hay sesión.
4. La cuenta nace como **VISITANTE**.

### 3.2 Ingreso con Google
1. El botón hace un **POST con token CSRF** (no se puede iniciar con un enlace GET desde otro sitio).
2. EcoParce redirige a Google con `state` aleatorio y **PKCE S256** (`code_challenge`).
3. Google devuelve un código; el servidor lo cambia por el `id_token` enviando el `code_verifier` y el secreto del cliente.
4. Se valida el `id_token`: emisor `https://accounts.google.com`, audiencia = `GOOGLE_CLIENT_ID`, vencimiento y **`email_verified = true`**.
5. Se guarda solo el identificador `sub` de Google. **No se guardan tokens** de acceso ni de actualización.
6. Si el correo pertenece a un administrador autorizado, se enlaza a esa cuenta sin cambiarle el rol. Si pertenecía a un registro **no verificado**, se le borra la contraseña (protección contra pre-secuestro de cuenta).

### 3.3 Verificación en dos pasos (administradores)
- TOTP compatible con Google Authenticator, Microsoft Authenticator o Authy, más 10 códigos de recuperación.
- **Obligatoria** para entrar al panel: sin TOTP configurado, el panel redirige a activarlo; con TOTP, la sesión debe haber completado el código.
- Un administrador no puede apagar su 2FA. Si pierde el teléfono y los códigos, el administrador del sistema la restablece; la acción exige reautenticación y queda en la auditoría.
- El secreto TOTP se guarda **cifrado** (prefijo `f1:`). La clave `MFA_CLAVE_CIFRADO` vive solo en el `.env` del servidor.
- Límite de intentos por usuario en el código.

### 3.4 Sesiones
| Parámetro | Valor |
|---|---|
| Cookie de sesión | `__Host-sessionid`, Secure, HttpOnly, SameSite=Lax |
| Duración máxima | 8 horas, y termina al cerrar el navegador |
| Inactividad en el panel | 30 minutos |
| Reautenticación | Acciones sensibles exigen identidad confirmada hace menos de 5 minutos (código TOTP o contraseña) |
| Cierre forzado | Al desactivar una cuenta, cambiarle el rol, restablecer su 2FA o eliminarla |

### 3.5 Recuperación de contraseña
Por **código** enviado al correo (15 minutos, 5 intentos). La respuesta es la misma exista o no la cuenta (anti-enumeración). Al cambiar la contraseña llega una alerta por correo.

---

### 3.6 Funciones con APIs externas (v1.2)
- Las consultas a la SDA y a Open Food Facts las hace **el servidor**, no el navegador: el visitante no se expone a terceros y la CSP sigue sin permitir scripts externos.
- El código escaneado se valida (solo 8 a 14 dígitos) antes de consultar afuera, con tiempo máximo de 6 s, caché y límite de 60 consultas cada 10 minutos por persona.
- Coordenadas fuera de Bogotá o registros incompletos de la SDA se descartan; si la sincronización falla, no se borra nada.
- Cámara y ubicación: `Permissions-Policy` las limita al propio sitio y ninguna de las dos sale del teléfono.

## 4. Protección de datos personales (Ley 1581 de 2012)

| Requisito | Evidencia |
|---|---|
| Autorización previa, expresa e informada | Casillas sin marcar en el registro; pantalla de autorización para quien entra con Google; se guarda **fecha y versión** del aviso (`Consentimiento`) |
| Finalidad y minimización | Solo nombre, correo, identificador de Google y progreso. Navegar no requiere cuenta. Las búsquedas y lecturas de QR siguen siendo anónimas (RN-08) |
| Derecho de acceso | «Mi cuenta → Descargar mis datos» (JSON completo) |
| Derecho de supresión | «Eliminar mi cuenta» con confirmación escrita e ingreso reciente; partidas y sugerencias quedan anónimas |
| Rechazo de la autorización | Si no acepta, la cuenta recién creada se borra de inmediato |
| Menores de edad | Declaración de mayoría de 14 años o permiso del acudiente; uso sin cuenta libre |
| Conservación | Datos de uso anónimos: 24 meses (`depurar_registros_uso`) |
| Seguridad | Este documento |

---

## 5. Pruebas realizadas (resultados reales del 21 de noviembre de 2026)

### Caja blanca
| Análisis | Resultado |
|---|---|
| Pruebas automatizadas de Django (SQLite y MySQL 8.0) | **91 pruebas, 0 fallas** |
| Bandit (análisis estático de seguridad) | **0 hallazgos** (2 excepciones justificadas en el código: iconos SVG fijos y nombres de límites de frecuencia) |
| pip-audit sobre `requirements.lock` | **Sin vulnerabilidades conocidas** |
| `manage.py check --deploy` con la configuración de producción | **0 advertencias** (precarga HSTS desactivada a propósito: es irreversible) |
| `makemigrations --check` | Sin cambios pendientes |

### Caja gris (pruebas que simulan atacantes con conocimiento parcial)
| Escenario | Resultado esperado | Estado |
|---|---|---|
| Token de Google emitido para otra aplicación | Rechazado, no se crea cuenta | Aprobado |
| Cuenta de Google con correo no verificado | Rechazada | Aprobado |
| Parámetro `state` inventado en el retorno de Google | Rechazado | Aprobado |
| Iniciar el flujo de Google por GET (login CSRF) | No redirige a Google | Aprobado |
| Pre-registro malicioso del correo de la víctima | La contraseña del atacante se anula | Aprobado |
| 5 contraseñas erradas y luego la correcta | Bloqueado: «Demasiados intentos fallidos» | Aprobado |
| Código de verificación del correo incorrecto | No inicia sesión | Aprobado |
| Código TOTP incorrecto | No inicia sesión | Aprobado |
| Sesión de admin sin el paso de 2FA | Expulsada del panel | Aprobado |
| Visitante que abre `/panel/` | 403 | Aprobado |
| Admin de contenido que abre QR, estadísticas, usuarios o auditoría | 403 | Aprobado |
| Admin desactivado con sesión abierta en otro navegador | Sesión cerrada al instante | Aprobado |
| Redirección abierta con `next=https://sitio-malicioso.com/` | Se ignora | Aprobado |
| Autor que intenta publicar su propia guía | Rechazado (RN-03) | Aprobado |
| Eliminar la cuenta con un ingreso de hace 1 hora | Pide volver a ingresar | Aprobado |
| Secreto TOTP leído directo de la base de datos | Solo se ve el texto cifrado | Aprobado |

### Caja negra (para repetir en producción después de publicar)
| Prueba | Comando o acción | Esperado |
|---|---|---|
| Cabeceras de seguridad | `curl -sI https://www.ecoparce.com.co/` | HSTS, CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy |
| HTTP redirige a HTTPS | `curl -sI http://www.ecoparce.com.co/` | 301 a https |
| Panel sin sesión | `curl -sI https://www.ecoparce.com.co/panel/` | 302 a `/accounts/login/` |
| Calificación TLS | ssllabs.com/ssltest | A o superior |
| Cabeceras | securityheaders.com | A o superior |
| security.txt | `https://www.ecoparce.com.co/.well-known/security.txt` | 200 con contacto |
| Registro de prueba | Crear cuenta con un correo real | Llega el código; sin él no entra |

---

## 6. Gestión de secretos

| Secreto | Dónde vive | Rotación |
|---|---|---|
| `DJANGO_SECRET_KEY` | `.env` del servidor (chmod 600) | Mover la actual a `DJANGO_SECRET_KEY_ANTERIOR` y poner una nueva |
| `MFA_CLAVE_CIFRADO` | `.env` del servidor | Igual, con `MFA_CLAVE_CIFRADO_ANTERIOR` |
| `GOOGLE_CLIENT_SECRET` | `.env` del servidor | Google Auth Platform → Clientes → agregar secreto nuevo y borrar el viejo |
| `SMTP_PASSWORD` | `.env` del servidor | En Resend o Gmail |
| Contraseña de MySQL | `.env` y `~/.my.cnf` (chmod 600) | Pestaña Databases de PythonAnywhere |

Nada de esto está en el código ni en el ZIP. El flujo de CI falla si alguien sube un `.env` o una clave con formato de Google o Resend.

---

## 7. Riesgos residuales y recomendaciones

1. **El correo es un punto crítico:** si el proveedor SMTP falla, nadie puede registrarse con correo (Google sigue funcionando). Conviene monitorear el envío desde el panel del proveedor.
2. **MySQL 8.0 está fuera de soporte desde abril de 2026** (riesgo R-09). Migrar a 8.4 LTS cuando PythonAnywhere lo ofrezca.
3. **Llaves de seguridad (WebAuthn/passkeys):** allauth las soporta; activarlas para administradores elevaría la protección contra phishing por encima de TOTP.
4. **Pruebas de penetración externas:** antes de una adopción masiva, una revisión con OWASP ZAP sobre el dominio publicado.
5. **Restricciones parciales en MySQL:** MySQL no crea las restricciones únicas condicionales de allauth (un correo verificado por persona, un TOTP por usuario). La unicidad la garantizan `usuario.correo UNIQUE` y las validaciones de allauth; con MySQL 8.4 o PostgreSQL se crearían también en la base de datos.
6. **Respaldo cifrado:** el script semanal genera `.sql.gz`; si se copia fuera de PythonAnywhere, cifrarlo con `gpg --symmetric`.
