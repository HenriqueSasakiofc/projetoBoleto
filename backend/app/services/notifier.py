from datetime import date
from .rules import days_late
import os
import smtplib
from email.message import EmailMessage

def build_charge_email(cliente_nome: str, valor: float, vencimento: date, descricao: str, texto_extra: str | None = None) -> tuple[str, str]:
    atraso = days_late(date.today(), vencimento)
    assunto = f"Cobrança - {descricao} - Vencimento {vencimento.strftime('%d/%m/%Y')}"
    corpo = (
        f"Olá, {cliente_nome}.\n\n"
        f"Estamos entrando em contato sobre a cobrança abaixo:\n"
        f"- Descrição: {descricao}\n"
        f"- Valor: R$ {valor:.2f}\n"
        f"- Vencimento: {vencimento.strftime('%d/%m/%Y')}\n"
        f"- Dias em atraso: {atraso}\n\n"
        f"Se já realizou o pagamento, por favor desconsidere esta mensagem.\n"
    )
    if texto_extra:
        corpo += f"\n{texto_extra}\n"
    return assunto, corpo

def build_paid_email(cliente_nome: str, valor: float, descricao: str) -> tuple[str, str]:
    assunto = f"Pagamento confirmado - {descricao}"
    corpo = (
        f"Olá, {cliente_nome}.\n\n"
        f"Confirmamos o pagamento da cobrança:\n"
        f"- Descrição: {descricao}\n"
        f"- Valor: R$ {valor:.2f}\n\n"
        f"Obrigado.\n"
    )
    return assunto, corpo

class DevMailer:
    def send(self, to_email: str, subject: str, body: str) -> None:
        print("\n=== EMAIL (DEV) ===")
        print("Para:", to_email)
        print("Assunto:", subject)
        print(body)
        print("===================\n")


class SmtpMailer:
    """
    Envia e-mail real via SMTP.
    Configuração vem de variáveis de ambiente:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_TLS, MAIL_FROM
    """

    def __init__(self, host: str, port: int, user: str, password: str, use_tls: bool, mail_from: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.mail_from = mail_from


    def send(self, to_email: str, subject: str, body: str) -> None:
        safe_mode = os.getenv("SAFE_MODE", "true").lower() in ("1", "true", "yes", "y")
        test_email = (os.getenv("TEST_EMAIL") or "").strip().lower()

        if safe_mode:
            if not test_email:
                raise RuntimeError("SAFE_MODE ativo, mas TEST_EMAIL não está configurado.")
            # BLOQUEIA qualquer envio que não seja o email de teste
            if to_email.strip().lower() != test_email:
                raise RuntimeError(f"SAFE_MODE: envio para '{to_email}' bloqueado. Só pode enviar para TEST_EMAIL.")

        msg = EmailMessage()
        msg["From"] = self.mail_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=20) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)

    @staticmethod
    def from_env():
        host = os.getenv("SMTP_HOST")
        port = os.getenv("SMTP_PORT")
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")
        tls = os.getenv("SMTP_TLS", "true").lower() in ("1", "true", "yes", "y")
        mail_from = os.getenv("MAIL_FROM") or user

        missing = [k for k, v in {
            "SMTP_HOST": host,
            "SMTP_PORT": port,
            "SMTP_USER": user,
            "SMTP_PASS": password,
        }.items() if not v]

        if missing:
            raise RuntimeError(f"Config SMTP incompleta. Faltando: {', '.join(missing)}")

        return SmtpMailer(
            host=host,
            port=int(port),
            user=user,
            password=password,
            use_tls=tls,
            mail_from=mail_from,
        )

    def send(self, to_email: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.mail_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=20) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)