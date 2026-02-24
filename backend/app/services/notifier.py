from datetime import date
from .rules import days_late

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