from fastapi import FastAPI

# Aqui criamos o "aplicativo" da API.
# O Uvicorn procura exatamente essa variável quando você roda: app.main:app
app = FastAPI(title="Projeto Boleto")

# Isso é uma "rota" (endpoint) HTTP.
# Quando alguém acessar /health, essa função responde.
@app.get("/health")
def health():
    # Isso é o JSON que a API devolve
    return {"ok": True}

from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
from datetime import date

app = FastAPI(title="Projeto Boleto")

@app.get("/health")
def health():
    return {"ok": True}

# 1) Este bloco define o "formato" do JSON que a API aceita no POST /cobrancas
class CobrancaCreate(BaseModel):
    remetente_nome: str
    remetente_email: EmailStr
    sacado_nome: str
    sacado_email: EmailStr
    valor: float
    vencimento: date

# 2) Esta rota recebe o JSON, valida automaticamente e devolve um retorno
@app.post("/cobrancas")
def criar_cobranca(payload: CobrancaCreate):
    # Aqui, "payload" já vem validado (email válido, data no formato certo, etc.)
    return {
        "status": "CRIADA",
        "recebido": payload.model_dump()
    }

