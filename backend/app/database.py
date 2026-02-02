"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./jobtracker.db"  # Default to SQLite for development
)

# Render uses "postgres://" but SQLAlchemy needs "postgresql://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# For SQLite development
# DATABASE_URL = "sqlite:///./jobtracker.db"

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL with connection pool settings for Render
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Check connection before using
        pool_recycle=300,    # Recycle connections after 5 minutes
        pool_size=5,         # Max 5 connections in pool
        max_overflow=10,     # Allow 10 additional connections
        pool_timeout=30,     # Wait 30s for connection
    )

# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
