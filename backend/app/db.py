from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite vai criar um arquivo boleto.db dentro da pasta backend/
DATABASE_URL = "sqlite:///./boleto.db"

# engine = “ponte” de conexão com o banco
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# SessionLocal = fábrica de sessões (cada request abre uma sessão)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = classe base para declarar tabelas (models)
Base = declarative_base()
