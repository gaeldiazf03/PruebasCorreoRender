import json
import os
import queue
import threading
from contextlib import closing
from email.utils import parseaddr
from http.client import HTTPException, HTTPSConnection

from dotenv import load_dotenv
from flask import Flask, Response, current_app, flash, redirect, render_template, request, url_for


load_dotenv()


SEND_ERROR_MESSAGE = "No se pudo enviar el correo. Revisa la configuración y los registros del servicio."


class ResendError(Exception):
    pass


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        RESEND_API_KEY=os.getenv("RESEND_API_KEY", ""),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", ""),
        MAIL_FORM_RECIPIENT=os.getenv("MAIL_FORM_RECIPIENT", ""),
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Configura SECRET_KEY en el archivo .env o en las variables de entorno.")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/send-email")
    def send_manual_email():
        recipient = request.form.get("recipient", "").strip()
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not _is_valid_email(recipient) or not subject or not body:
            if _wants_progress():
                return _progress_error("Ingresa un correo válido, un asunto y un cuerpo.")
            flash("Ingresa un correo válido, un asunto y un cuerpo.", "error")
            return redirect(url_for("index", _anchor="manual"))

        if _wants_progress():
            return _send_with_progress(recipient, subject, body, anchor="manual")

        return _send_and_redirect(
            recipient,
            subject,
            body,
            "Resend aceptó el correo para envío.",
            "manual",
        )

    @app.post("/send-form")
    def send_contact_form():
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        recipient = current_app.config["MAIL_FORM_RECIPIENT"].strip()

        if not name or not _is_valid_email(email) or not message:
            if _wants_progress():
                return _progress_error("Completa tu nombre, un correo válido y el mensaje.")
            flash("Completa tu nombre, un correo válido y el mensaje.", "error")
            return redirect(url_for("index", _anchor="contact"))
        if not _is_valid_email(recipient):
            current_app.logger.error("MAIL_FORM_RECIPIENT no está configurado correctamente.")
            if _wants_progress():
                return _progress_error("Falta configurar un destinatario válido para el formulario.")
            flash("No se pudo enviar el formulario: falta configurar el destinatario.", "error")
            return redirect(url_for("index", _anchor="contact"))

        body = (
            f"Información recibida desde el formulario web:\n\n"
            f"Nombre: {name}\n"
            f"Correo: {email}\n"
            f"Teléfono: {phone or 'No proporcionado'}\n\n"
            f"Mensaje:\n{message}"
        )
        if _wants_progress():
            return _send_with_progress(
                recipient,
                "Nuevo mensaje desde el formulario web",
                body,
                anchor="contact",
                reply_to=email,
            )
        return _send_and_redirect(
            recipient,
            "Nuevo mensaje desde el formulario web",
            body,
            "Resend aceptó el mensaje del formulario para envío.",
            "contact",
            reply_to=email,
        )

    return app


def _is_valid_email(value):
    if not value or any(character.isspace() for character in value):
        return False
    display_name, address = parseaddr(value)
    return not display_name and address == value and "@" in address and "\r" not in value and "\n" not in value


def send_email(recipient, subject, body, reply_to=None, on_progress=None):
    _report_progress(on_progress, "preparing", "Preparando el mensaje.")
    api_key = current_app.config["RESEND_API_KEY"].strip()
    sender = current_app.config["MAIL_DEFAULT_SENDER"].strip()
    if not api_key:
        raise ResendError("Configura RESEND_API_KEY.")
    if not sender:
        raise ResendError("Configura MAIL_DEFAULT_SENDER.")

    message = {"from": sender, "to": [recipient], "subject": subject, "text": body}
    if reply_to:
        message["reply_to"] = reply_to

    _report_progress(on_progress, "sending", "Enviando el mensaje a Resend por HTTPS.")
    try:
        with closing(HTTPSConnection("api.resend.com", timeout=10)) as connection:
            connection.request(
                "POST",
                "/emails",
                body=json.dumps(message).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "PruebasCorreoRender/1.0",
                },
            )
            with connection.getresponse() as response:
                status = response.status
    except (OSError, HTTPException, ValueError) as error:
        raise ResendError(f"Falló la comunicación con Resend ({type(error).__name__}).") from None
    if not 200 <= status < 300:
        raise ResendError(f"Resend rechazó la solicitud (HTTP {status}).")

    _report_progress(
        on_progress,
        "accepted",
        "Resend aceptó el mensaje; esto no confirma su entrega en la bandeja del destinatario.",
    )


def _report_progress(callback, status, message):
    if callback:
        callback(status, message)


def _wants_progress():
    return request.headers.get("Accept") == "text/event-stream"


def _format_event(event):
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _progress_error(message):
    response = Response(
        _format_event({"type": "error", "message": message}),
        mimetype="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    return response


def _send_with_progress(recipient, subject, body, anchor, reply_to=None):
    app = current_app._get_current_object()
    events = queue.Queue()

    def report(status, message):
        events.put({"type": "progress", "status": status, "message": message})

    def send():
        with app.app_context():
            try:
                send_email(recipient, subject, body, reply_to=reply_to, on_progress=report)
            except ResendError as error:
                current_app.logger.error("No se pudo enviar el correo: %s", error)
                events.put(
                    {
                        "type": "error",
                        "message": SEND_ERROR_MESSAGE,
                    }
                )
            else:
                events.put(
                    {
                        "type": "complete",
                        "message": f"Proceso terminado. Resend aceptó el correo dirigido a {recipient}.",
                        "anchor": anchor,
                    }
                )
            finally:
                events.put(None)

    def stream():
        yield _format_event({"type": "progress", "status": "starting", "message": "Iniciando el proceso de envío."})
        threading.Thread(target=send, daemon=True).start()
        while True:
            event = events.get()
            if event is None:
                break
            yield _format_event(event)

    response = Response(stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


def _send_and_redirect(recipient, subject, body, success_message, anchor, reply_to=None):
    try:
        send_email(recipient, subject, body, reply_to=reply_to)
    except ResendError as error:
        current_app.logger.error("No se pudo enviar el correo: %s", error)
        flash(SEND_ERROR_MESSAGE, "error")
    else:
        flash(success_message, "success")
    return redirect(url_for("index", _anchor=anchor))


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"},
    )
