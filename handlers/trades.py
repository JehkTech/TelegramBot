# handlers/trades.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import asyncio
from db import create_trade_sync, get_recent_trades_sync, update_trade_sync, get_user_stats_sync

# Conversation states
PAIR, DIRECTION, ENTRY, EXIT, STOP, SIZE, NOTES, CONFIRM = range(8)

async def start_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Let's log a trade. What instrument/pair? (e.g., BTCUSD, EURUSD)")
    return PAIR

async def ask_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pair'] = update.message.text.strip().upper()
    keyboard = [
        [InlineKeyboardButton("LONG", callback_data="LONG"), InlineKeyboardButton("SHORT", callback_data="SHORT")]
    ]
    await update.message.reply_text("Direction?", reply_markup=InlineKeyboardMarkup(keyboard))
    return DIRECTION

async def direction_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    direction = query.data
    context.user_data['direction'] = direction
    await query.edit_message_text(f"Direction: {direction}\nEnter ENTRY price (or type 'skip'):")
    return ENTRY

async def entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() == "skip":
        context.user_data['entry'] = None
    else:
        try:
            context.user_data['entry'] = float(txt)
        except:
            await update.message.reply_text("Invalid number. Please send entry price or 'skip'")
            return ENTRY
    await update.message.reply_text("Exit price (or type 'skip' for open trade):")
    return EXIT

async def exit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() == "skip":
        context.user_data['exit'] = None
    else:
        try:
            context.user_data['exit'] = float(txt)
        except:
            await update.message.reply_text("Invalid number. Please send exit price or 'skip'")
            return EXIT
    await update.message.reply_text("Stop Loss (or 'skip'):")
    return STOP

async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() == "skip":
        context.user_data['stop_loss'] = None
    else:
        try:
            context.user_data['stop_loss'] = float(txt)
        except:
            await update.message.reply_text("Invalid number. Please send stop loss or 'skip'")
            return STOP
    await update.message.reply_text("Size (units or lots) (or 'skip'):")
    return SIZE

async def size_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() == "skip":
        context.user_data['size'] = None
    else:
        try:
            context.user_data['size'] = float(txt)
        except:
            await update.message.reply_text("Invalid. send numeric or 'skip'")
            return SIZE
    await update.message.reply_text("Optional notes for this trade (or 'skip'):")
    return NOTES

async def notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    context.user_data['notes'] = None if txt.lower() == "skip" else txt
    # show confirmation
    u = update.effective_user
    summary = (
        f"User: {u.first_name}\n"
        f"Pair: {context.user_data.get('pair')}\n"
        f"Direction: {context.user_data.get('direction')}\n"
        f"Entry: {context.user_data.get('entry')}\n"
        f"Exit: {context.user_data.get('exit')}\n"
        f"Stop: {context.user_data.get('stop_loss')}\n"
        f"Size: {context.user_data.get('size')}\n"
        f"Notes: {context.user_data.get('notes')}\n\n"
        "Confirm save?"
    )
    keyboard = [[InlineKeyboardButton("Save", callback_data="SAVE"), InlineKeyboardButton("Cancel", callback_data="CANCEL")]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM

async def confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "SAVE":
        u = query.from_user
        payload = {
            "user_id": u.id,
            "username": u.username,
            "pair": context.user_data.get('pair'),
            "direction": context.user_data.get('direction'),
            "entry": context.user_data.get('entry'),
            "exit": context.user_data.get('exit'),
            "stop_loss": context.user_data.get('stop_loss'),
            "size": context.user_data.get('size'),
            "notes": context.user_data.get('notes'),
            "closed": True if context.user_data.get('exit') is not None else False,
        }
        # write to DB using sync call in thread
        res = await asyncio.to_thread(create_trade_sync, payload)
        if res.get("success"):
            await query.edit_message_text("Trade saved ✅ (id: {})".format(res.get("id")))
        else:
            await query.edit_message_text("Failed to save trade: {}".format(res.get("error")))
    else:
        await query.edit_message_text("Cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trade logging cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# simple list recent trades
async def list_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    rows = await asyncio.to_thread(get_recent_trades_sync, u.id, 10)
    if not rows:
        await update.message.reply_text("No recent trades found.")
        return
    lines = []
    for r in rows:
        lines.append(f"#{r['id']} {r['pair']} {r['direction']} entry:{r['entry']} exit:{r['exit']} pnl:{r['pnl']} closed:{r['closed']}")
    await update.message.reply_text("\n".join(lines))

# /stats
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    stats = await asyncio.to_thread(get_user_stats_sync, u.id)
    await update.message.reply_text(f"Total trades: {stats['total']}\nWins: {stats['wins']}\nLosses: {stats['losses']}\nAvg pnl: {stats['avg_pnl']:.2f}")

# Conversation handler factory
def get_trade_conversation():
    conv = ConversationHandler(
        entry_points=[CommandHandler("log", start_trade)],
        states={
            PAIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_direction)],
            DIRECTION: [CallbackQueryHandler(direction_cb)],
            ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, entry_handler)],
            EXIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exit_handler)],
            STOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, stop_handler)],
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, size_handler)],
            NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, notes_handler)],
            CONFIRM: [CallbackQueryHandler(confirm_cb)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300
    )
    return conv
