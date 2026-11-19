# Pruebas de automatización de correo

Aplicación básica en Flask con dos módulos:

- **Correo personalizado:** permite indicar destinatario, asunto y cuerpo.
- **Formulario de contacto:** recoge nombre, correo, teléfono opcional y mensaje; los envía a un destinatario configurado.

## Ejecutar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

La aplicación estará disponible en <http://localhost:5000>. Por defecto, SMTP apunta a `localhost:1025`, útil para probar con un servidor local de correo de desarrollo como Mailpit. Si no hay un servidor SMTP disponible, el formulario mostrará un error y la aplicación registrará el detalle en la consola.

## Configuración SMTP

Configura estas variables de entorno antes de iniciar la aplicación:

| Variable | Descripción | Valor predeterminado |
| --- | --- | --- |
| `SECRET_KEY` | Clave de sesión de Flask; usa un valor secreto en producción. | Clave local de desarrollo |
| `MAIL_SERVER` | Host SMTP. | `localhost` |
| `MAIL_PORT` | Puerto SMTP. | `1025` |
| `MAIL_USE_TLS` | Usa STARTTLS (`true`/`false`). | `false` |
| `MAIL_USE_SSL` | Usa SSL/TLS directo (`true`/`false`). No se combina con STARTTLS. | `false` |
| `MAIL_USERNAME` | Usuario SMTP; también se usa como remitente si no se define `MAIL_DEFAULT_SENDER`. | Vacío |
| `MAIL_PASSWORD` | Contraseña SMTP. | Vacío |
| `MAIL_DEFAULT_SENDER` | Dirección remitente. | Vacío |
| `MAIL_FORM_RECIPIENT` | Dirección que recibe los envíos del formulario de contacto. | Vacío |
| `PORT` | Puerto HTTP de la aplicación. | `5000` |

En un despliegue (por ejemplo Render), agrega estas variables en la configuración del servicio y usa `python app.py` como comando de inicio. No guardes contraseñas ni claves SMTP en el repositorio.

## Pruebas

```bash
python -m unittest
```

Las pruebas validan los dos flujos sin conectarse a un servidor SMTP real.