"""
PostgreSQL Database Models using SQLAlchemy.
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resume_screening.db")

engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class Candidate(Base):
    __tablename__ = "candidates"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(255))
    email            = Column(String(255))
    experience_years = Column(Float)
    skills           = Column(Text)
    raw_json         = Column(Text)


def init_db():
    Base.metadata.create_all(bind=engine)
