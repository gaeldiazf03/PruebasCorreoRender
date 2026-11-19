# Pruebas de automatización de correo

Aplicación básica en Flask con dos módulos:

- **Correo personalizado:** permite indicar destinatario, asunto y cuerpo.
- **Formulario de contacto:** recoge nombre, correo, teléfono opcional y mensaje; los envía a un destinatario configurado.

## Ejecutar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Genera una clave y asígnala a SECRET_KEY en .env:
python -c "import secrets; print(secrets.token_hex(32))"
python app.py
```

La aplicación estará disponible en <http://localhost:5000>. Por defecto, SMTP apunta a `localhost:1025`, útil para probar con un servidor local de correo de desarrollo como Mailpit. Si no hay un servidor SMTP disponible, el formulario mostrará un error y la aplicación registrará el detalle en la consola.

Al enviar un correo, la página muestra el progreso real de conexión, autenticación y envío al servidor SMTP. El estado de éxito significa que el servidor SMTP aceptó el mensaje; no confirma que haya llegado a la bandeja de entrada ni que se haya leído.

## Configuración SMTP

La aplicación carga la configuración del archivo `.env` al iniciar. Completa allí las credenciales SMTP y el destinatario del formulario; `SECRET_KEY` es obligatoria. El archivo `.env` está excluido de Git. En producción (por ejemplo Render), configura estas variables en el servicio:

| Variable | Descripción | Valor predeterminado |
| --- | --- | --- |
| `SECRET_KEY` | Clave secreta de sesión de Flask. | Obligatoria |
| `MAIL_SERVER` | Host SMTP. | `localhost` |
| `MAIL_PORT` | Puerto SMTP. | `1025` |
| `MAIL_USE_TLS` | Usa STARTTLS (`true`/`false`). | `false` |
| `MAIL_USE_SSL` | Usa SSL/TLS directo (`true`/`false`). No se combina con STARTTLS. | `false` |
| `MAIL_USERNAME` | Usuario SMTP; también se usa como remitente si no se define `MAIL_DEFAULT_SENDER`. | Vacío |
| `MAIL_PASSWORD` | Contraseña SMTP. | Vacío |
| `MAIL_DEFAULT_SENDER` | Dirección remitente. | Vacío |
| `MAIL_FORM_RECIPIENT` | Dirección que recibe los envíos del formulario de contacto. | Vacío |
| `PORT` | Puerto HTTP de la aplicación. | `5000` |

### Desplegar en Render

No necesitas crear un archivo `wsgi.py`: `app.py` ya expone la aplicación Flask como `app`, por lo que Gunicorn puede cargarla directamente.

1. Confirma que `gunicorn` esté en `requirements.txt` y sube los cambios a GitHub. No subas `.env`; está excluido por `.gitignore`.
2. En Render, crea un **Web Service** conectado al repositorio y configura:

   | Ajuste | Valor |
   | --- | --- |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app` |

3. En **Environment Variables** del servicio, agrega `SECRET_KEY`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` y `MAIL_FORM_RECIPIENT` con los valores de tu proveedor SMTP. Genera un valor secreto nuevo para `SECRET_KEY`; no copies credenciales al repositorio.

Render volverá a desplegar cuando subas cambios a la rama conectada. Revisa los logs del servicio si el build o el arranque fallan. No uses `python app.py` como servidor de producción.

## Pruebas

```bash
python -m unittest
```

Las pruebas validan los dos flujos sin conectarse a un servidor SMTP real.