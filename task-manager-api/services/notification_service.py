"""Notificações por email. Configuração injetada (sem credenciais no código) e desligada por padrão."""
import logging
import smtplib

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, enabled, host, port, user, password):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    @classmethod
    def from_config(cls, config):
        return cls(
            enabled=config['NOTIFICATIONS_ENABLED'],
            host=config['SMTP_HOST'],
            port=config['SMTP_PORT'],
            user=config['SMTP_USER'],
            password=config['SMTP_PASSWORD'],
        )

    def send_email(self, to, subject, body):
        if not self.enabled:
            logger.info('Notificação (desativada) para %s: %s', to, subject)
            return False
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to, f"Subject: {subject}\n\n{body}")
            logger.info('Email enviado para %s', to)
            return True
        except (smtplib.SMTPException, OSError):
            logger.exception('Erro ao enviar email para %s', to)
            return False

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
                f"Prioridade: {task.priority}\nStatus: {task.status}")
        return self.send_email(user.email, subject, body)

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        return self.send_email(user.email, subject, body)
