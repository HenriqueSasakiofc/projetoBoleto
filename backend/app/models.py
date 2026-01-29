from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Cobranca(Base):
    __tablename__ = "cobrancas"

    id = Column(Integer, primary_key=True, index=True)

    remetente_nome = Column(String, nullable=False)
    remetente_email = Column(String, nullable=False)

    sacado_nome = Column(String, nullable=False)
    sacado_email = Column(String, nullable=False)

    valor = Column(Float, nullable=False)
    vencimento = Column(Date, nullable=False)

    status = Column(String, nullable=False, default="CRIADA")
    provider_charge_id = Column(String, nullable=True)

    # ligações (1 cobrança -> 1 boleto) e (1 cobrança -> várias notificações)
    boleto = relationship("Boleto", back_populates="cobranca", uselist=False)
    notificacoes = relationship("Notificacao", back_populates="cobranca")

class Boleto(Base):
    __tablename__ = "boletos"

    id = Column(Integer, primary_key=True, index=True)
    cobranca_id = Column(Integer, ForeignKey("cobrancas.id"), nullable=False)

    linha_digitavel = Column(String, nullable=False)
    pdf_url = Column(String, nullable=False)

    status = Column(String, nullable=False, default="GERADO")
    gerado_em = Column(DateTime, default=datetime.utcnow)

    cobranca = relationship("Cobranca", back_populates="boleto")

class Notificacao(Base):
    __tablename__ = "notificacoes"

    id = Column(Integer, primary_key=True, index=True)
    cobranca_id = Column(Integer, ForeignKey("cobrancas.id"), nullable=False)

    tipo = Column(String, nullable=False, default="EMAIL")
    para = Column(String, nullable=False)

    status = Column(String, nullable=False, default="PENDENTE")  # PENDENTE, ENVIADA, FALHA
    tentativas = Column(Integer, nullable=False, default=0)
    ultimo_erro = Column(String, nullable=True)

    criada_em = Column(DateTime, default=datetime.utcnow)

    cobranca = relationship("Cobranca", back_populates="notificacoes")
