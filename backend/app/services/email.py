import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import settings
from app.models.models import Tenant, User

logger = logging.getLogger(__name__)


def email_is_enabled() -> bool:
    return bool(settings.email_enabled and settings.smtp_host and settings.email_from_address)


def platform_name(tenant: Tenant | None = None) -> str:
    if tenant and tenant.name:
        return f"{tenant.name} Vision Platform"
    return "Plataforma de Monitoramento Inteligente"


def build_reset_password_url(token: str) -> str:
    base_url = settings.frontend_public_url.rstrip("/")
    return f"{base_url}/reset-password?token={quote(token)}"


def build_login_url() -> str:
    return f"{settings.frontend_public_url.rstrip('/')}/login"


def _compose_message(*, to_address: str, subject: str, text_body: str) -> EmailMessage:
    message = EmailMessage()
    from_name = settings.email_from_name.strip()
    from_address = settings.email_from_address.strip()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_address}>"
    message["To"] = to_address
    if settings.email_reply_to:
        message["Reply-To"] = settings.email_reply_to
    message.set_content(text_body)
    return message


def send_email(*, to_address: str, subject: str, text_body: str) -> bool:
    if not email_is_enabled():
        logger.info("Email disabled; skipping delivery to %s with subject %s", to_address, subject)
        return False

    message = _compose_message(
        to_address=to_address,
        subject=subject,
        text_body=text_body,
    )

    try:
        if settings.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=context,
            ) as smtp:
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as smtp:
                if settings.smtp_use_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
    except Exception:
        logger.exception("Failed to send email to %s", to_address)
        return False

    return True


def send_password_reset_email(user: User, token: str, tenant: Tenant | None = None) -> bool:
    reset_url = build_reset_password_url(token)
    subject = "Redefinicao de senha - SensX Vision Platform"
    text_body = (
        f"Olá, {user.name}.\n\n"
        f"Recebemos uma solicitacao para redefinir sua senha na {platform_name(tenant)}.\n\n"
        f"Use o link abaixo para cadastrar uma nova senha:\n"
        f"{reset_url}\n\n"
        f"Se voce nao solicitou esta alteracao, ignore este e-mail.\n"
        f"O link expira em {settings.password_reset_token_expire_minutes} minutos.\n"
    )
    return send_email(to_address=user.email, subject=subject, text_body=text_body)


def send_pending_approval_email(user: User, tenant: Tenant | None = None) -> bool:
    subject = "Cadastro recebido - aguardando aprovacao"
    text_body = (
        f"Olá, {user.name}.\n\n"
        f"Seu cadastro na {platform_name(tenant)} foi recebido com sucesso.\n"
        f"A conta esta aguardando aprovacao administrativa antes do primeiro acesso.\n\n"
        f"Assim que a aprovacao acontecer, voce podera entrar por:\n"
        f"{build_login_url()}\n"
    )
    return send_email(to_address=user.email, subject=subject, text_body=text_body)


def send_approval_request_email(
    *,
    approver_email: str,
    pending_user: User,
    tenant: Tenant | None = None,
) -> bool:
    tenant_label = tenant.name if tenant else "SensX"
    subject = f"Aprovacao de usuario pendente - {tenant_label}"
    text_body = (
        f"Olá.\n\n"
        f"Um novo usuario esta aguardando aprovacao na {platform_name(tenant)}.\n\n"
        f"Nome: {pending_user.name}\n"
        f"E-mail: {pending_user.email}\n"
        f"Tenant: {tenant_label}\n\n"
        f"Acesse o painel administrativo para aprovar ou rejeitar:\n"
        f"{build_login_url()}\n"
    )
    return send_email(to_address=approver_email, subject=subject, text_body=text_body)


def send_approved_user_email(user: User, tenant: Tenant | None = None) -> bool:
    subject = "Sua conta foi aprovada"
    text_body = (
        f"Olá, {user.name}.\n\n"
        f"Sua conta foi aprovada na {platform_name(tenant)}.\n"
        f"Voce ja pode acessar a plataforma em:\n"
        f"{build_login_url()}\n"
    )
    return send_email(to_address=user.email, subject=subject, text_body=text_body)


def send_rejected_user_email(user: User, tenant: Tenant | None = None) -> bool:
    subject = "Atualizacao sobre seu cadastro"
    support_line = ""
    if settings.email_support_address:
        support_line = f"\nSe precisar de suporte, responda para {settings.email_support_address}.\n"

    text_body = (
        f"Olá, {user.name}.\n\n"
        f"Seu cadastro na {platform_name(tenant)} nao foi aprovado neste momento."
        f"{support_line}"
    )
    return send_email(to_address=user.email, subject=subject, text_body=text_body)
