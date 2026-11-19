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
# Completa el resto de .env con los datos de Resend (ver abajo).
python app.py
```

La aplicación estará disponible en <http://localhost:5000>.

Ambos módulos envían a la API de Resend mediante HTTPS (puerto 443), sin usar SMTP. La página muestra la preparación, el envío y el resultado de la solicitud. Que Resend acepte el mensaje no confirma su entrega.

## Configuración de Resend

Verifica tu [dominio remitente en Resend](https://resend.com/docs/dashboard/domains/introduction) y crea una [clave de API](https://resend.com/api-keys) con permiso de envío. Configura estas variables en `.env` para desarrollo o en el servicio para producción:

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de sesión de Flask. Obligatoria para iniciar. |
| `RESEND_API_KEY` | Clave privada de Resend con permiso de envío. |
| `MAIL_DEFAULT_SENDER` | Remitente de un dominio verificado, por ejemplo `Web <hola@tudominio.com>`. |
| `MAIL_FORM_RECIPIENT` | Dirección que recibe los envíos del formulario de contacto. El correo del visitante se usa en `Reply-To`, no como remitente. |
| `PORT` | Puerto HTTP local de la aplicación; por defecto, `5000`. |

Para una prueba sin dominio verificado, usa `onboarding@resend.dev` como remitente y la dirección de tu cuenta de Resend como destinatario en cualquiera de los dos módulos. No compartas la clave ni subas `.env` al repositorio.

### Desplegar en Render

No necesitas crear un archivo `wsgi.py`: `app.py` ya expone la aplicación Flask como `app`, por lo que Gunicorn puede cargarla directamente.

1. Confirma que `gunicorn` esté en `requirements.txt` y sube los cambios a GitHub. No subas `.env`; está excluido por `.gitignore`.
2. En Render, crea un **Web Service** conectado al repositorio y configura:

   | Ajuste | Valor |
   | --- | --- |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app` |

3. En **Environment Variables**, guarda `RESEND_API_KEY` y configura `MAIL_DEFAULT_SENDER` con el remitente autorizado por Resend. Mantén `SECRET_KEY` y `MAIL_FORM_RECIPIENT`. Las variables SMTP anteriores ya no se usan y se pueden quitar.

Render volverá a desplegar cuando subas cambios a la rama conectada. Revisa los logs del servicio si el build o el arranque fallan. No uses `python app.py` como servidor de producción.

Si el sitio es público, restringe el acceso al módulo de correo personalizado antes de desplegar: permite elegir cualquier destinatario y puede consumir tu cuota de Resend.

## Pruebas

```bash
SECRET_KEY=pruebas-locales python -m unittest
```

Las pruebas validan los dos flujos sin contactar a Resend ni enviar correos reales.