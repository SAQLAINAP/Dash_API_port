from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, func, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
import json

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    provider = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    input_price = Column(Float, default=0.0)
    output_price = Column(Float, default=0.0)
    context_window = Column(Integer, default=0)
    config = Column(JSON, default={})  # Stores raw fields/capabilities
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Leaderboard(Base):
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer)
    model = Column(String, index=True)
    arena_score = Column(Integer)
    ci_95 = Column(String)
    category = Column(String, default="Overall")
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)

# --- CRUD Operations ---

def upsert_model(db, model_data):
    """
    Insert or Update a model in the DB. 
    Matches by 'name'.
    """
    existing = db.query(Model).filter(Model.name == model_data['name']).first()
    
    if existing:
        existing.provider = model_data.get('provider', existing.provider)
        existing.input_price = model_data.get('input_price', existing.input_price)
        existing.output_price = model_data.get('output_price', existing.output_price)
        existing.context_window = model_data.get('context_window', existing.context_window)
        existing.config = model_data.get('config', existing.config)
    else:
        new_model = Model(
            name=model_data['name'],
            provider=model_data.get('provider', 'Unknown'),
            input_price=model_data.get('input_price', 0.0),
            output_price=model_data.get('output_price', 0.0),
            context_window=model_data.get('context_window', 0),
            config=model_data.get('config', {})
        )
        db.add(new_model)
    
    db.commit()

def clear_leaderboard(db):
    db.query(Leaderboard).delete()
    db.commit()

def insert_leaderboard_entry(db, entry):
    lb = Leaderboard(
        rank=int(entry.get('rank', 0)),
        model=entry.get('model'),
        arena_score=entry.get('arena_score'),
        ci_95=entry.get('ci_95'),
        category=entry.get('category', 'Overall')
    )
    db.add(lb)

