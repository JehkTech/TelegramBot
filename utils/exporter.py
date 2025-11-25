# utils/exporter.py
import asyncio
import pandas as pd
from db import SessionLocal
from models import Trade

def export_user_trades_sync(user_id: int, path: str):
    session = SessionLocal()
    try:
        rows = session.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.created_at.desc()).all()
        data = []
        for r in rows:
            data.append({
                "id": r.id,
                "pair": r.pair,
                "direction": r.direction,
                "entry": r.entry,
                "exit": r.exit,
                "stop_loss": r.stop_loss,
                "size": r.size,
                "pnl": r.pnl,
                "notes": r.notes,
                "created_at": r.created_at
            })
        df = pd.DataFrame(data)
        df.to_csv(path, index=False)
        return True
    except Exception as e:
        print("export error", e)
        return False
    finally:
        session.close()

async def export_user_trades(user_id: int, path: str):
    return await asyncio.to_thread(export_user_trades_sync, user_id, path)
