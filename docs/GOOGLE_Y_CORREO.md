# Configurar el ingreso con Google y el correo de verificación

## A. Credenciales de Google (Google Auth Platform)

Hágalo con la cuenta de Google del proyecto, no con una personal que pueda perderse.

1. Entre a **console.cloud.google.com** y cree un proyecto llamado `EcoParce`.
2. Menú **Google Auth Platform → Get started** (Comenzar):
   - Nombre de la app: `EcoParce`
   - Correo de asistencia: el correo del equipo
   - Público (*Audience*): **Externo**
   - Correo de contacto del desarrollador y aceptar la política de datos de usuario.
3. **Branding** (Desarrollo de la marca):
   - Logo: `static/img/logo-256.png`
   - Página principal: `https://www.ecoparce.com.co`
   - Política de privacidad: `https://www.ecoparce.com.co/privacidad/`
   - Términos: `https://www.ecoparce.com.co/terminos/`
   - Dominio autorizado: `ecoparce.com.co`
4. **Data access** (Acceso a datos): agregue solo `openid`, `.../auth/userinfo.email` y `.../auth/userinfo.profile`. Son permisos **no sensibles**: no requieren la revisión de seguridad de Google.
5. **Audience**: presione **Publish app** (Publicar). Mientras siga en «Testing», solo entran los usuarios de prueba que usted agregue.
6. **Clients → Create client** (Crear cliente):
   - Tipo: **Aplicación web**, nombre `EcoParce producción`
   - **URI de redireccionamiento autorizados**: `https://www.ecoparce.com.co/accounts/google/login/callback/`
   - No hace falta «Orígenes de JavaScript»: EcoParce no usa el SDK de Google en el navegador.
7. Copie el **ID de cliente** y el **secreto** al `.env` del servidor (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). El secreto se muestra una sola vez.
8. Para desarrollo, cree **otro cliente** (`EcoParce local`) con la URI `http://127.0.0.1:8000/accounts/google/login/callback/` y póngalo en el `.env` de su computador. Así el secreto de producción nunca sale del servidor.

> Los cambios en Google pueden tardar de 5 minutos a unas horas en aplicarse.

**Botón de Google:** el botón actual dice «Continuar con Google» con un icono neutro. Si quieren usar el logotipo oficial de la «G», descárguenlo de las *Sign in with Google branding guidelines* de Google y respeten sus reglas de uso.

## B. Correo para los códigos de verificación

Igual que en CiudadReporta, hay dos opciones. Ambas funcionan desde PythonAnywhere con la cuenta paga.

**Opción A · Resend (recomendada)**
1. Cree una cuenta en resend.com y agregue el dominio `ecoparce.com.co`.
2. En GoDaddy → DNS agregue los registros **SPF**, **DKIM** y (opcional) **DMARC** que muestra Resend. Sin ellos los correos llegan a spam.
3. Cree una API key con permiso solo de envío.
4. En el `.env`: `SMTP_HOST=smtp.resend.com`, `SMTP_PORT=465`, `SMTP_SSL=1`, `SMTP_USER=resend`, `SMTP_PASSWORD=re_...`, `CORREO_REMITENTE=EcoParce <no-responder@ecoparce.com.co>`.

**Opción B · Gmail**
1. En la cuenta de Gmail del proyecto active la verificación en dos pasos y cree una **contraseña de aplicación**.
2. En el `.env`: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=465`, `SMTP_SSL=1`, `SMTP_USER=correo@gmail.com`, `SMTP_PASSWORD=<contraseña de aplicación>`, `CORREO_REMITENTE=EcoParce <correo@gmail.com>`.

**Prueba:** `python manage.py sendtestemail su-correo@ejemplo.com`

## C. Primer administrador en producción

```bash
python manage.py createsuperuser        # su correo de Google, nombre y una contraseña larga
```
1. Entre a `https://www.ecoparce.com.co/panel/` con Google (mismo correo) o con esa contraseña.
2. Acepte el aviso de privacidad y **active la verificación en dos pasos** escaneando el QR con Google Authenticator.
3. Guarde los **códigos de recuperación** en un lugar seguro (no en el mismo teléfono).
4. Desde **Panel → Administradores → Nuevo administrador**, autorice a Danixa y Darien con sus correos de Google. Ellos entran con Google y activan su propia 2FA.
