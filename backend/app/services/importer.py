import re
import unicodedata
from io import BytesIO
import pandas as pd
from sqlalchemy.orm import Session
from .. import models

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = re.sub(r"\s+", " ", s)
    return s

def extract_first_email(text) -> str | None:
    if text is None:
        return None
    text = str(text).replace("mailto:", " ")
    found = EMAIL_RE.findall(text)
    return found[0].lower() if found else None

def read_excel_bytes(file_bytes: bytes, header_row: int) -> pd.DataFrame:
    return pd.read_excel(BytesIO(file_bytes), header=header_row)

def import_from_excels(db: Session, contas_bytes: bytes, clientes_bytes: bytes) -> tuple[int, int, int]:
    # suas planilhas têm título na linha 1 e cabeçalho na linha 2 -> header=1
    contas = read_excel_bytes(contas_bytes, header_row=1)
    clientes = read_excel_bytes(clientes_bytes, header_row=1)

    # remove linhas "Total" / "Gerado em..."
    if "Documento" in contas.columns:
        contas = contas[contas["Documento"].notna()]
        contas = contas[contas["Documento"].astype(str).str.upper() != "TOTAL"]
        contas = contas[~contas["Documento"].astype(str).str.startswith("Gerado em", na=False)]

    if "Código" in clientes.columns:
        clientes = clientes[clientes["Código"].notna()]
        clientes = clientes[~clientes["Código"].astype(str).str.startswith("Gerado em", na=False)]

    # prioridade de email no cadastro do cliente
    email_cols = ["E-mail para cobrança", "E-mail do financeiro", "E-mail do faturamento", "E-mail"]

    # monta mapa de clientes por nome_norm
    client_map = {}
    for _, row in clientes.iterrows():
        nome = str(row.get("Nome", "")).strip()
        nome_norm = normalize_text(nome)
        if not nome_norm:
            continue

        email = None
        for c in email_cols:
            if c in clientes.columns:
                email = extract_first_email(row.get(c))
                if email:
                    break

        client_map[nome_norm] = {
            "codigo": str(row.get("Código")).strip() if row.get("Código") is not None else None,
            "nome": nome,
            "nome_norm": nome_norm,
            "email": email,
            "documento": str(row.get("CNPJ/CPF")).strip() if row.get("CNPJ/CPF") is not None else None,
        }

    # upsert clientes
    clientes_importados = 0
    for data in client_map.values():
        existing = db.query(models.Cliente).filter(models.Cliente.nome_norm == data["nome_norm"]).first()
        if existing:
            existing.codigo = data["codigo"]
            existing.nome = data["nome"]
            existing.email_cobranca = data["email"]
            existing.documento = data["documento"]
        else:
            db.add(models.Cliente(**{
                "codigo": data["codigo"],
                "nome": data["nome"],
                "nome_norm": data["nome_norm"],
                "email_cobranca": data["email"],
                "documento": data["documento"],
            }))
        clientes_importados += 1
    db.commit()

    # mapa nome_norm -> cliente(id/email)
    clientes_db = db.query(models.Cliente).all()
    clientes_id_map = {c.nome_norm: c for c in clientes_db}

    # converte datas
    if "Vencimento" in contas.columns:
        contas["Vencimento"] = pd.to_datetime(contas["Vencimento"], errors="coerce", dayfirst=True)

    cobrancas_importadas = 0
    cobrancas_sem_email = 0

    for _, row in contas.iterrows():
        nome = str(row.get("Nome", "")).strip()
        nome_norm = normalize_text(nome)
        cliente = clientes_id_map.get(nome_norm)

        email = cliente.email_cobranca if cliente else None
        if not email:
            cobrancas_sem_email += 1

        venc = row.get("Vencimento")
        if pd.isna(venc):
            continue
        venc_date = venc.date()

        documento = str(row.get("Documento", "")).strip()
        nosso_numero = row.get("Nosso Numero")
        nosso_numero_str = str(int(nosso_numero)) if pd.notna(nosso_numero) else None

        valor = float(row.get("Valor", 0) or 0)
        saldo = float(row.get("Saldo", 0) or 0)

        status_raw = str(row.get("Status", "")).strip().upper()
        status = "PAGO" if status_raw == "PAGO" else "ABERTO"

        descricao = f"Documento {documento}"

        # upsert cobranca (por nosso_numero se tiver, senão documento+vencimento)
        existing = None
        if nosso_numero_str:
            existing = db.query(models.Cobranca).filter(models.Cobranca.nosso_numero == nosso_numero_str).first()

        if not existing:
            existing = db.query(models.Cobranca).filter(
                models.Cobranca.documento == documento,
                models.Cobranca.vencimento == venc_date
            ).first()

        if existing:
            existing.cliente_id = cliente.id if cliente else None
            existing.cliente_nome = nome
            existing.email_cobranca = email
            existing.vencimento = venc_date
            existing.valor = valor
            existing.saldo = saldo
            existing.status = status
            existing.descricao = descricao
            existing.nosso_numero = nosso_numero_str
        else:
            db.add(models.Cobranca(
                documento=documento,
                nosso_numero=nosso_numero_str,
                cliente_id=cliente.id if cliente else None,
                cliente_nome=nome,
                email_cobranca=email,
                vencimento=venc_date,
                valor=valor,
                saldo=saldo,
                descricao=descricao,
                status=status,
            ))

        cobrancas_importadas += 1

    db.commit()
    return clientes_importados, cobrancas_importadas, cobrancas_sem_email