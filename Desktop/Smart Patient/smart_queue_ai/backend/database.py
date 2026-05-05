import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string
# postgresql://postgres:postgres@localhost:5432/smart_queue_db
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Sany%407396@localhost:5432/smart_queue_db")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
