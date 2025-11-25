# bot.py
import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from handlers.trades import get_trade_conversation, list_trades, stats_command
from db import init_db
from utils.exporter import export_user_trades
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
TZ = os.getenv("TIMEZONE", "Africa/Lusaka")
DAILY_HOUR = int(os.getenv("DAILY_SUMMARY_HOUR", "20"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# init DB
init_db()

scheduler = AsyncIOScheduler()

# scheduled job: daily summary for each user who has trades
from db import SessionLocal

async def send_daily_summary(app):
    # iterate over users in DB (simple)
    session = SessionLocal()
    try:
        users = session.query(Trade.user_id).distinct().all()
        for (user_id,) in users:
            # compute simple stats
            stats = await asyncio.to_thread(lambda uid: __get_stats(uid), user_id)
            text = f"Daily summary — total trades: {stats['total']}, wins: {stats['wins']}, losses: {stats['losses']}, avg pnl: {stats['avg_pnl']:.2f}"
            try:
                await app.bot.send_message(chat_id=user_id, text=text)
            except Exception as e:
                logger.warning(f"Failed to send daily summary to {user_id}: {e}")
    finally:
        session.close()

def __get_stats(uid):
    # small helper using DB sync functions
    from db import get_user_stats_sync
    return get_user_stats_sync(uid)

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    path = f"/tmp/trades_{user.id}.csv"
    ok = await export_user_trades(user.id, path)
    if ok:
        await update.message.reply_document(document=open(path, "rb"), filename=f"trades_{user.id}.csv")
    else:
        await update.message.reply_text("Failed to export.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trading Journal Bot online. Use /log to log a trade, /list to list recent trades, /export to get CSV, /stats for quick metrics.")

async def on_startup(app):
    scheduler.start()

# def main():
#     if not TOKEN:
#         raise RuntimeError("TELEGRAM_TOKEN missing in env")
#     # app = ApplicationBuilder().token(TOKEN).build()
#     app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()


#     # register handlers
#     app.add_handler(get_trade_conversation())
#     app.add_handler(CommandHandler("start", start_command))
#     app.add_handler(CommandHandler("list", list_trades))
#     app.add_handler(CommandHandler("stats", stats_command))
#     app.add_handler(CommandHandler("export", export_command))

#     # scheduler
#     scheduler = AsyncIOScheduler(timezone=TZ)
#     # run daily at DAILY_HOUR
#     # scheduler.add_job(lambda: asyncio.create_task(send_daily_summary(app)), 'cron', hour=DAILY_HOUR)
#     scheduler.add_job(lambda: asyncio.create_task(send_daily_summary(app)), 'cron', hour=DAILY_HOUR)
#     scheduler.start()

#     # run polling
#     app.run_polling()


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN missing in env")

    async def on_startup(app):
        scheduler.start()

    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    # register conversation and commands
    app.add_handler(get_trade_conversation())
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("list", list_trades))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("export", export_command))

    # scheduler is declared BEFORE run_polling, but starts AFTER.
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_summary(app)),
        'cron',
        hour=DAILY_HOUR
    )

    app.run_polling()



if __name__ == "__main__":
    main()
