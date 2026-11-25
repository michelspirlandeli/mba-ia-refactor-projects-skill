"""Notificações por email.

Configuração injetada (sem credenciais no código), desligada por padrão e enviada em background:
o SMTP nunca bloqueia a requisição.
"""
import logging
import smtplib
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, enabled, host, port, user, password, timeout, executor=None):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout
        self._executor = executor or ThreadPoolExecutor(max_workers=2, thread_name_prefix="notifications")

    @classmethod
    def from_config(cls, config):
        return cls(
            enabled=config['NOTIFICATIONS_ENABLED'],
            host=config['SMTP_HOST'],
            port=config['SMTP_PORT'],
            user=config['SMTP_USER'],
            password=config['SMTP_PASSWORD'],
            timeout=config['SMTP_TIMEOUT_SECONDS'],
        )

    def _send_email(self, to, subject, body):
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to, f"Subject: {subject}\n\n{body}")
            logger.info('Email enviado: %s', subject)
        except (smtplib.SMTPException, OSError):
            logger.exception('Erro ao enviar email: %s', subject)

    def send_email(self, to, subject, body):
        """Agenda o envio e retorna imediatamente (True se agendado)."""
        if not self.enabled:
            logger.info('Notificação desativada: %s', subject)
            return False
        self._executor.submit(self._send_email, to, subject, body)
        return True

    def notify_task_assigned(self, user, task):
        # Os textos são montados aqui (thread da requisição): objetos ORM não vão para a thread de envio.
        subject = f"Nova task atribuída: {task.title}"
        body = (f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
                f"Prioridade: {task.priority}\nStatus: {task.status}")
        return self.send_email(user.email, subject, body)
