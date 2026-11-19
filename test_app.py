import json
import unittest
from unittest.mock import patch

from app import create_app


class EmailFormTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "RESEND_API_KEY": "test-api-key",
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

    @patch("app.HTTPSConnection")
    def test_manual_email_reports_live_progress(self, https_connection):
        connection = https_connection.return_value
        connection.getresponse.return_value.__enter__.return_value.status = 200
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
        self.assertIn(b"Enviando el mensaje a Resend por HTTPS.", response.data)
        self.assertIn(b'"status": "accepted"', response.data)
        self.assertIn(b'"type": "complete"', response.data)
        https_connection.assert_called_once_with("api.resend.com", timeout=10)
        connection.request.assert_called_once()
        self.assertEqual(connection.request.call_args.args, ("POST", "/emails"))
        request = connection.request.call_args.kwargs
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-api-key")
        self.assertEqual(request["headers"]["Content-Type"], "application/json")
        self.assertEqual(
            json.loads(request["body"]),
            {
                "from": "website@example.com",
                "to": ["person@example.com"],
                "subject": "Prueba",
                "text": "Contenido del correo",
            },
        )

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

    @patch("app.HTTPSConnection")
    def test_contact_form_reports_live_progress(self, https_connection):
        connection = https_connection.return_value
        connection.getresponse.return_value.__enter__.return_value.status = 200
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
        payload = json.loads(connection.request.call_args.kwargs["body"])
        self.assertEqual(payload["from"], "website@example.com")
        self.assertEqual(payload["to"], ["inbox@example.com"])
        self.assertEqual(payload["reply_to"], "ana@example.com")
        self.assertIn("Hola", payload["text"])

    @patch("app.HTTPSConnection")
    def test_resend_rejection_reports_stream_error(self, https_connection):
        connection = https_connection.return_value
        connection.getresponse.return_value.__enter__.return_value.status = 403
        with self.assertLogs(self.app.logger, level="ERROR") as logs:
            response = self.client.post(
                "/send-email",
                data={"recipient": "person@example.com", "subject": "Prueba", "body": "Texto"},
                headers={"Accept": "text/event-stream"},
                buffered=True,
            )

        self.assertIn(b'"type": "error"', response.data)
        self.assertNotIn(b'"type": "complete"', response.data)
        self.assertNotIn(b"test-api-key", response.data)
        self.assertIn("HTTP 403", logs.output[0])

    @patch("app.HTTPSConnection")
    def test_resend_timeout_displays_error_after_redirect(self, https_connection):
        https_connection.return_value.request.side_effect = TimeoutError()
        with self.assertLogs(self.app.logger, level="ERROR") as logs:
            response = self.client.post(
                "/send-email",
                data={"recipient": "person@example.com", "subject": "Prueba", "body": "Texto"},
                follow_redirects=True,
            )

        self.assertIn(b"No se pudo enviar el correo.", response.data)
        self.assertIn("TimeoutError", logs.output[0])

    @patch("app.HTTPSConnection")
    def test_missing_api_key_does_not_make_request(self, https_connection):
        self.app.config["RESEND_API_KEY"] = ""
        with self.assertLogs(self.app.logger, level="ERROR") as logs:
            response = self.client.post(
                "/send-email",
                data={"recipient": "person@example.com", "subject": "Prueba", "body": "Texto"},
                follow_redirects=True,
            )

        https_connection.assert_not_called()
        self.assertIn(b"No se pudo enviar el correo.", response.data)
        self.assertIn("RESEND_API_KEY", logs.output[0])

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
