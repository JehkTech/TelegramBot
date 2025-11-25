# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

def now():
    return datetime.datetime.utcnow()

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)           # Telegram user id
    username = Column(String, nullable=True)
    pair = Column(String, nullable=False)           # e.g., BTCUSD
    direction = Column(String, nullable=False)      # LONG / SHORT
    entry = Column(Float, nullable=True)
    exit = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    size = Column(Float, nullable=True)             # lots / units
    notes = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True) # optional
    pnl = Column(Float, nullable=True)              # calculated or entered
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    closed = Column(Boolean, default=False)         # open or closed trade
