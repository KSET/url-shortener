from sqlalchemy import Column, Integer, String, DateTime, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    short_id = Column(String, unique=True, index=True)
    original_url = Column(String)
    click_count = Column(Integer, default=0, nullable=False)
    last_clicked_at = Column(DateTime, nullable=True)
    qr_template = Column(String, default="general", nullable=False)
    qr_code_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def ensure_columns():
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns("urls")}
    statements = {
        "click_count": "ALTER TABLE urls ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0",
        "last_clicked_at": "ALTER TABLE urls ADD COLUMN last_clicked_at TIMESTAMP",
        "qr_template": "ALTER TABLE urls ADD COLUMN qr_template VARCHAR DEFAULT 'general' NOT NULL",
        "qr_code_path": "ALTER TABLE urls ADD COLUMN qr_code_path VARCHAR",
    }

    with engine.begin() as connection:
        for column_name, statement in statements.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))

def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_columns()
