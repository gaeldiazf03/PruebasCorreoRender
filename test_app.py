import unittest
from unittest.mock import patch

from app import create_app


class EmailFormTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "MAIL_FORM_RECIPIENT": "inbox@example.com",
                "MAIL_DEFAULT_SENDER": "website@example.com",
            }
        )
        self.client = self.app.test_client()

    def test_homepage_contains_both_email_modules(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Correo personalizado", response.data)
        self.assertIn(b"Formulario de contacto", response.data)

    @patch("app.send_email")
    def test_manual_email_sends_submitted_fields(self, send_email):
        response = self.client.post(
            "/send-email",
            data={
                "recipient": "person@example.com",
                "subject": "Prueba",
                "body": "Contenido del correo",
            },
        )

        self.assertEqual(response.status_code, 302)
        send_email.assert_called_once_with(
            "person@example.com", "Prueba", "Contenido del correo", reply_to=None
        )

    @patch("app.send_email")
    def test_manual_email_reports_live_progress(self, send_email):
        def send_with_progress(recipient, subject, body, reply_to=None, on_progress=None):
            on_progress("connecting", "Conectando al servidor SMTP.")
            on_progress("sending", "Enviando el mensaje.")
            on_progress("accepted", "El servidor SMTP aceptó el mensaje.")

        send_email.side_effect = send_with_progress
        response = self.client.post(
            "/send-email",
            data={
                "recipient": "person@example.com",
                "subject": "Prueba",
                "body": "Contenido del correo",
            },
            headers={"Accept": "text/event-stream"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Conectando al servidor SMTP.", response.data)
        self.assertIn(b"Enviando el mensaje.", response.data)
        self.assertIn(b"El servidor SMTP acept\xc3\xb3 el mensaje.", response.data)

    @patch("app.send_email")
    def test_progress_endpoint_reports_validation_errors(self, send_email):
        response = self.client.post(
            "/send-email",
            data={"recipient": "invalid", "subject": "Prueba", "body": "Texto"},
            headers={"Accept": "text/event-stream"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Ingresa un correo v\xc3\xa1lido", response.data)
        send_email.assert_not_called()

    @patch("app.send_email")
    def test_contact_form_sends_all_fields_and_reply_to(self, send_email):
        response = self.client.post(
            "/send-form",
            data={
                "name": "Ana",
                "email": "ana@example.com",
                "phone": "555-0101",
                "message": "Hola, necesito información.",
            },
        )

        self.assertEqual(response.status_code, 302)
        send_email.assert_called_once()
        recipient, subject, body = send_email.call_args.args
        self.assertEqual(recipient, "inbox@example.com")
        self.assertEqual(subject, "Nuevo mensaje desde el formulario web")
        self.assertIn("Nombre: Ana", body)
        self.assertIn("Correo: ana@example.com", body)
        self.assertIn("Teléfono: 555-0101", body)
        self.assertIn("Hola, necesito información.", body)
        self.assertEqual(send_email.call_args.kwargs["reply_to"], "ana@example.com")

    @patch("app.send_email")
    def test_contact_form_reports_live_progress(self, send_email):
        response = self.client.post(
            "/send-form",
            data={
                "name": "Ana",
                "email": "ana@example.com",
                "message": "Hola",
            },
            headers={"Accept": "text/event-stream"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Proceso terminado.", response.data)
        self.assertIn("on_progress", send_email.call_args.kwargs)

    @patch("app.send_email")
    def test_invalid_manual_email_is_rejected(self, send_email):
        response = self.client.post(
            "/send-email",
            data={"recipient": "no-es-correo", "subject": "Prueba", "body": "Texto"},
        )

        self.assertEqual(response.status_code, 302)
        send_email.assert_not_called()

    @patch("app.send_email")
    def test_contact_form_requires_configured_recipient(self, send_email):
        app = create_app({"TESTING": True, "MAIL_FORM_RECIPIENT": ""})
        response = app.test_client().post(
            "/send-form",
            data={"name": "Ana", "email": "ana@example.com", "message": "Hola"},
        )

        self.assertEqual(response.status_code, 302)
        send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
