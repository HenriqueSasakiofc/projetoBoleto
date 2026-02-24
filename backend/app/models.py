from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, nullable=True)              # coluna "Código" da planilha
    nome = Column(String, nullable=False)
    nome_norm = Column(String, nullable=False, index=True)  # nome normalizado p/ cruzar
    email_cobranca = Column(String, nullable=True)
    documento = Column(String, nullable=True)           # CPF/CNPJ

    cobrancas = relationship("Cobranca", back_populates="cliente")

class Cobranca(Base):
    __tablename__ = "cobrancas"

    id = Column(Integer, primary_key=True, index=True)

    documento = Column(String, nullable=True)       # "Documento" do contas a receber (ex.: 005445/1)
    nosso_numero = Column(String, nullable=True)    # "Nosso Numero" do contas a receber

    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    cliente_nome = Column(String, nullable=False)
    email_cobranca = Column(String, nullable=True)

    vencimento = Column(Date, nullable=False)
    valor = Column(Float, nullable=False)
    saldo = Column(Float, nullable=True)

    descricao = Column(String, nullable=True)        # texto que vai no e-mail
    status = Column(String, nullable=False, default="ABERTO")  # ABERTO / PAGO

    ultimo_envio_em = Column(Date, nullable=True)    # evita mandar 2x no mesmo dia
    pago_em = Column(Date, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="cobrancas")
    envios = relationship("Envio", back_populates="cobranca")

class Envio(Base):
    __tablename__ = "envios"

    id = Column(Integer, primary_key=True, index=True)
    cobranca_id = Column(Integer, ForeignKey("cobrancas.id"), nullable=False)

    tipo = Column(String, nullable=False)     # COBRANCA ou CONFIRMACAO
    canal = Column(String, nullable=False)    # EMAIL (por enquanto)

    para = Column(String, nullable=False)
    assunto = Column(String, nullable=False)
    corpo = Column(String, nullable=False)

    status = Column(String, nullable=False)   # ENVIADO / FALHA
    erro = Column(String, nullable=True)

    enviado_em = Column(DateTime, default=datetime.utcnow)

    cobranca = relationship("Cobranca", back_populates="envios")