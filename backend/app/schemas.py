from pydantic import BaseModel
from datetime import date
from typing import Optional

class ImportResult(BaseModel):
    clientes_importados: int
    cobrancas_importadas: int
    cobrancas_sem_email: int

class RunResult(BaseModel):
    enviados: int
    pulados: int
    sem_email: int
    erros: int

class MarcarPagoIn(BaseModel):
    nosso_numero: Optional[str] = None
    documento: Optional[str] = None
    pago_em: Optional[date] = None