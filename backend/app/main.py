from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal
from . import models, schemas
from .services.provider import MockBoletoProvider
from .services.notifier import EmailNotifier

# cria tabelas no SQLite se ainda não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Projeto Boleto MVP")

def get_db():
    # abre sessão do banco por request
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

provider = MockBoletoProvider()
notifier = EmailNotifier()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/cobrancas", response_model=schemas.CobrancaOut)
def criar_cobranca(payload: schemas.CobrancaCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    # 1) cria a cobrança no banco
    cobranca = models.Cobranca(
        remetente_nome=payload.remetente_nome,
        remetente_email=str(payload.remetente_email),
        sacado_nome=payload.sacado_nome,
        sacado_email=str(payload.sacado_email),
        valor=payload.valor,
        vencimento=payload.vencimento,
        status="CRIADA",
    )
    db.add(cobranca)
    db.commit()
    db.refresh(cobranca)  # agora cobranca.id existe

    # 2) gera boleto (mock)
    boleto_data = provider.gerar_boleto(
        valor=cobranca.valor,
        vencimento=cobranca.vencimento,
        sacado_nome=cobranca.sacado_nome
    )

    # 3) salva boleto e atualiza status da cobrança
    cobranca.provider_charge_id = boleto_data["provider_charge_id"]
    cobranca.status = "BOLETO_GERADO"

    boleto = models.Boleto(
        cobranca_id=cobranca.id,
        linha_digitavel=boleto_data["linha_digitavel"],
        pdf_url=boleto_data["pdf_url"],
        status="GERADO"
    )
    db.add(boleto)

    # 4) registra uma notificação pendente
    notif = models.Notificacao(
        cobranca_id=cobranca.id,
        tipo="EMAIL",
        para=cobranca.remetente_email,
        status="PENDENTE",
        tentativas=0,
    )
    db.add(notif)

    db.commit()

    # 5) envia notificação em background (não trava a API)
    background.add_task(
        notifier.enviar_email_boleto_gerado,
        cobranca.remetente_email,
        cobranca.id,
        boleto.pdf_url,
        boleto.linha_digitavel
    )

    return {
        "id": cobranca.id,
        "status": cobranca.status,
        "boleto": {
            "linha_digitavel": boleto.linha_digitavel,
            "pdf_url": boleto.pdf_url
        }
    }

@app.get("/cobrancas/{cobranca_id}", response_model=schemas.CobrancaOut)
def buscar_cobranca(cobranca_id: int, db: Session = Depends(get_db)):
    cobranca = db.query(models.Cobranca).filter(models.Cobranca.id == cobranca_id).first()
    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    boleto = db.query(models.Boleto).filter(models.Boleto.cobranca_id == cobranca.id).first()

    return {
        "id": cobranca.id,
        "status": cobranca.status,
        "boleto": None if not boleto else {
            "linha_digitavel": boleto.linha_digitavel,
            "pdf_url": boleto.pdf_url
        }
    }
