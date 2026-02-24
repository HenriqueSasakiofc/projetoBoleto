from datetime import date

def should_send_today(today: date, due_date: date, last_sent: date | None) -> bool:
    # não envia duas vezes no mesmo dia
    if last_sent == today:
        return False

    days = (due_date - today).days

    # mais de 30 dias antes do vencimento: não cobra
    if days > 30:
        return False

    # entre 30 e 8 dias antes: 1x por semana
    if 8 <= days <= 30:
        if last_sent is None:
            return True
        return (today - last_sent).days >= 7

    # 7 dias ou menos (inclui vencido): 1x por dia
    if last_sent is None:
        return True
    return (today - last_sent).days >= 1

def days_late(today: date, due_date: date) -> int:
    return max(0, (today - due_date).days)