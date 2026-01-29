from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

class CobrancaCreate(BaseModel):
    remetente_nome: str
    remetente_email: EmailStr
    sacado_nome: str
    sacado_email: EmailStr
    valor: float
    vencimento: date

class BoletoOut(BaseModel):
    linha_digitavel: str
    pdf_url: str

class CobrancaOut(BaseModel):
    id: int
    status: str
    boleto: Optional[BoletoOut] = None
