# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from models import Base, Trade
import os
import asyncio

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_journal.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)

# sync helpers (we'll call them via asyncio.to_thread from async code)
def create_trade_sync(payload: dict) -> dict:
    session = SessionLocal()
    try:
        t = Trade(**payload)
        session.add(t)
        session.commit()
        session.refresh(t)
        return {"success": True, "id": t.id}
    except SQLAlchemyError as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

def update_trade_sync(trade_id: int, updates: dict) -> dict:
    session = SessionLocal()
    try:
        t = session.query(Trade).filter(Trade.id == trade_id).first()
        if not t:
            return {"success": False, "error": "not_found"}
        for k, v in updates.items():
            setattr(t, k, v)
        session.commit()
        return {"success": True}
    except SQLAlchemyError as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

def get_recent_trades_sync(user_id: int, limit: int = 20):
    session = SessionLocal()
    try:
        rows = session.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.created_at.desc()).limit(limit).all()
        results = []
        for r in rows:
            results.append({
                "id": r.id,
                "pair": r.pair,
                "direction": r.direction,
                "entry": r.entry,
                "exit": r.exit,
                "pnl": r.pnl,
                "notes": r.notes,
                "created_at": r.created_at.isoformat(),
                "closed": r.closed
            })
        return results
    finally:
        session.close()

def get_user_stats_sync(user_id: int):
    session = SessionLocal()
    try:
        total = session.query(Trade).filter(Trade.user_id == user_id).count()
        wins = session.query(Trade).filter(Trade.user_id == user_id, Trade.pnl > 0).count()
        losses = session.query(Trade).filter(Trade.user_id == user_id, Trade.pnl <= 0).count()
        avg_pnl = session.query(Trade).filter(Trade.user_id == user_id).with_entities(
            (Trade.pnl).label("pnl")
        )
        # simple avg via Python to keep SQL simple
        all_pnls = [t.pnl for t in session.query(Trade).filter(Trade.user_id == user_id, Trade.pnl != None).all()]
        avg = sum(all_pnls) / len(all_pnls) if all_pnls else 0
        return {"total": total, "wins": wins, "losses": losses, "avg_pnl": avg}
    finally:
        session.close()
