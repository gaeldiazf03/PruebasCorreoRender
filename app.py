import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr

from flask import Flask, current_app, flash, redirect, render_template, request, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "local-development-key"),
        MAIL_SERVER=os.getenv("MAIL_SERVER", "localhost"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "1025")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "false").lower() in {"1", "true", "yes"},
        MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes"},
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", ""),
        MAIL_FORM_RECIPIENT=os.getenv("MAIL_FORM_RECIPIENT", ""),
    )
    if test_config:
        app.config.update(test_config)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/send-email")
    def send_manual_email():
        recipient = request.form.get("recipient", "").strip()
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not _is_valid_email(recipient) or not subject or not body:
            flash("Ingresa un correo válido, un asunto y un cuerpo.", "error")
            return redirect(url_for("index", _anchor="manual"))

        return _send_and_redirect(
            recipient,
            subject,
            body,
            "Correo enviado correctamente.",
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
            flash("Completa tu nombre, un correo válido y el mensaje.", "error")
            return redirect(url_for("index", _anchor="contact"))
        if not _is_valid_email(recipient):
            current_app.logger.error("MAIL_FORM_RECIPIENT no está configurado correctamente.")
            flash("No se pudo enviar el formulario: falta configurar el destinatario.", "error")
            return redirect(url_for("index", _anchor="contact"))

        body = (
            f"Información recibida desde el formulario web:\n\n"
            f"Nombre: {name}\n"
            f"Correo: {email}\n"
            f"Teléfono: {phone or 'No proporcionado'}\n\n"
            f"Mensaje:\n{message}"
        )
        return _send_and_redirect(
            recipient,
            "Nuevo mensaje desde el formulario web",
            body,
            "Formulario enviado correctamente.",
            "contact",
            reply_to=email,
        )

    return app


def _is_valid_email(value):
    if not value or any(character.isspace() for character in value):
        return False
    display_name, address = parseaddr(value)
    return not display_name and address == value and "@" in address and "\r" not in value and "\n" not in value


def send_email(recipient, subject, body, reply_to=None):
    sender = current_app.config["MAIL_DEFAULT_SENDER"] or current_app.config["MAIL_USERNAME"]
    if not sender:
        raise ValueError("Configura MAIL_DEFAULT_SENDER o MAIL_USERNAME.")
    if current_app.config["MAIL_USE_TLS"] and current_app.config["MAIL_USE_SSL"]:
        raise ValueError("MAIL_USE_TLS y MAIL_USE_SSL no pueden estar habilitados al mismo tiempo.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    server = current_app.config["MAIL_SERVER"]
    port = current_app.config["MAIL_PORT"]
    timeout = 10
    if current_app.config["MAIL_USE_SSL"]:
        with smtplib.SMTP_SSL(server, port, timeout=timeout) as smtp:
            _authenticate(smtp)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(server, port, timeout=timeout) as smtp:
            if current_app.config["MAIL_USE_TLS"]:
                smtp.starttls()
            _authenticate(smtp)
            smtp.send_message(message)


def _authenticate(smtp):
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    if username:
        smtp.login(username, password)


def _send_and_redirect(recipient, subject, body, success_message, anchor, reply_to=None):
    try:
        send_email(recipient, subject, body, reply_to=reply_to)
    except (smtplib.SMTPException, OSError, ValueError):
        current_app.logger.exception("No se pudo enviar el correo.")
        flash("No se pudo enviar el correo. Verifica la configuración SMTP.", "error")
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
