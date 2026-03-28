from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from .db import Base, engine, SessionLocal
from . import models, schemas
from .services.importer import import_from_excels
from .services.rules import should_send_today
from .services.notifier import build_charge_email, build_paid_email
from .services.notifier import SmtpMailer

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cobrador MVP (outbox)")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"msg": "Servidor rodando. Vá em /docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/importar", response_model=schemas.ImportResult)
async def importar(
    contas: UploadFile = File(...),
    clientes: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contas_bytes = await contas.read()
    clientes_bytes = await clientes.read()

    c1, c2, sem_email = import_from_excels(db, contas_bytes, clientes_bytes)
    return {"clientes_importados": c1, "cobrancas_importadas": c2, "cobrancas_sem_email": sem_email}

@app.get("/cobrancas")
def listar_cobrancas(db: Session = Depends(get_db)):
    items = db.query(models.Cobranca).order_by(models.Cobranca.vencimento.asc()).limit(100).all()
    return [{
        "id": c.id,
        "cliente": c.cliente_nome,
        "email": c.email_cobranca,
        "valor": c.valor,
        "vencimento": str(c.vencimento),
        "status": c.status,
        "nosso_numero": c.nosso_numero,
        "documento": c.documento,
        "ultimo_envio_em": str(c.ultimo_envio_em) if c.ultimo_envio_em else None
    } for c in items]

@app.get("/simular-cobranca")
def simular_cobranca(db: Session = Depends(get_db)):
    hoje = date.today()
    cobrancas = db.query(models.Cobranca).filter(models.Cobranca.status == "ABERTO").all()

    vai_cobrar = []
    nao_vai = []

    for c in cobrancas:
        if not c.email_cobranca:
            nao_vai.append({"id": c.id, "cliente": c.cliente_nome, "motivo": "SEM_EMAIL"})
            continue

        if should_send_today(hoje, c.vencimento, c.ultimo_envio_em):
            vai_cobrar.append({"id": c.id, "cliente": c.cliente_nome, "vencimento": str(c.vencimento)})
        else:
            nao_vai.append({"id": c.id, "cliente": c.cliente_nome, "motivo": "REGRA_NAO_PERMITE"})

    return {"hoje": str(hoje), "vai_cobrar": vai_cobrar, "nao_vai": nao_vai}

@app.post("/rodar-cobrador", response_model=schemas.RunResult)
def rodar_cobrador(db: Session = Depends(get_db)):
    hoje = date.today()
    cobrancas = db.query(models.Cobranca).filter(models.Cobranca.status == "ABERTO").all()

    enviados = pulados = sem_email = erros = 0

    for c in cobrancas:
        if not c.email_cobranca:
            sem_email += 1
            continue

        if not should_send_today(hoje, c.vencimento, c.ultimo_envio_em):
            pulados += 1
            continue

        subject, body = build_charge_email(
            cliente_nome=c.cliente_nome,
            valor=c.valor,
            vencimento=c.vencimento,
            descricao=c.descricao or "Cobrança",
            texto_extra=None
        )

        try:
            db.add(models.Envio(
                cobranca_id=c.id,
                tipo="COBRANCA",
                canal="EMAIL",
                para=c.email_cobranca,
                assunto=subject,
                corpo=body,
                status="PENDENTE",
            ))
            c.ultimo_envio_em = hoje
            enviados += 1
        except Exception as e:
            db.add(models.Envio(
                cobranca_id=c.id,
                tipo="COBRANCA",
                canal="EMAIL",
                para=c.email_cobranca,
                assunto=subject,
                corpo=body,
                status="FALHA",
                erro=str(e),
            ))
            erros += 1

    db.commit()
    return {"enviados": enviados, "pulados": pulados, "sem_email": sem_email, "erros": erros}

@app.get("/outbox")
def ver_outbox(db: Session = Depends(get_db)):
    pendentes = db.query(models.Envio).filter(models.Envio.status == "PENDENTE").order_by(models.Envio.enviado_em.asc()).limit(200).all()
    return [{
        "id": e.id,
        "tipo": e.tipo,
        "para": e.para,
        "assunto": e.assunto,
        "cobranca_id": e.cobranca_id,
        "status": e.status,
        "enviado_em": str(e.enviado_em)
    } for e in pendentes]

@app.get("/outbox/{envio_id}")
def ver_envio(envio_id: int, db: Session = Depends(get_db)):
    e = db.query(models.Envio).filter(models.Envio.id == envio_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Envio não encontrado")
    return {
        "id": e.id,
        "tipo": e.tipo,
        "para": e.para,
        "assunto": e.assunto,
        "corpo": e.corpo,
        "status": e.status,
        "erro": e.erro
    }

@app.post("/outbox/enviar-para-teste/{envio_id}")
def enviar_para_teste(envio_id: int, to: str, db: Session = Depends(get_db)):
    e = db.query(models.Envio).filter(models.Envio.id == envio_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Envio não encontrado")

    smtp = SmtpMailer.from_env()
    smtp.send(to_email=to, subject=e.assunto, body=e.corpo)

    # IMPORTANTE: não marca como ENVIADO (porque foi só teste)
    return {"ok": True, "msg": "Enviado para teste (não alterei o status)", "envio_id": e.id, "to": to}

@app.post("/marcar-pago")
def marcar_pago(payload: schemas.MarcarPagoIn, db: Session = Depends(get_db)):
    if not payload.nosso_numero and not payload.documento:
        raise HTTPException(status_code=400, detail="Informe nosso_numero ou documento")

    q = db.query(models.Cobranca)
    if payload.nosso_numero:
        q = q.filter(models.Cobranca.nosso_numero == payload.nosso_numero)
    else:
        q = q.filter(models.Cobranca.documento == payload.documento)

    c = q.first()
    if not c:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    if c.status == "PAGO":
        return {"ok": True, "msg": "Já estava pago"}

    c.status = "PAGO"
    c.pago_em = payload.pago_em or date.today()

    if c.email_cobranca:
        subject, body = build_paid_email(
            cliente_nome=c.cliente_nome,
            valor=c.valor,
            descricao=c.descricao or "Cobrança"
        )
        db.add(models.Envio(
            cobranca_id=c.id,
            tipo="CONFIRMACAO",
            canal="EMAIL",
            para=c.email_cobranca,
            assunto=subject,
            corpo=body,
            status="PENDENTE",
        ))

    db.commit()
    return {"ok": True}



@app.post("/teste-email")
def teste_email(to: str):
    smtp = SmtpMailer.from_env()
    smtp.send(
        to_email=to,
        subject="Teste do Cobrador (SMTP OK)",
        body="Se você recebeu este e-mail, o envio SMTP real está funcionando."
    )
    return {"ok": True}


@app.post("/outbox/enviar-proximo-teste")
def enviar_proximo_teste(db: Session = Depends(get_db)):
    test_email = os.getenv("TEST_EMAIL")
    if not test_email:
        raise HTTPException(status_code=400, detail="TEST_EMAIL não configurado.")

    e = (
        db.query(models.Envio)
        .filter(models.Envio.status == "PENDENTE")
        .order_by(models.Envio.enviado_em.asc())
        .first()
    )
    if not e:
        return {"ok": False, "msg": "Não existe mensagem PENDENTE na outbox"}

    smtp = SmtpMailer.from_env()

    # envia só para o email de teste
    smtp.send(to_email=test_email, subject=e.assunto, body=e.corpo)

    # não muda status (você pode testar várias vezes sem “consumir”)
    return {"ok": True, "enviado_para": test_email, "envio_id": e.id, "original_para_seria": e.para}