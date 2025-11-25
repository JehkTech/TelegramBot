# Telegram Trading Journal - MVP

## What it does
- Log trades via `/log` wizard
- List recent trades `/list`
- Export CSV `/export`
- Daily summary sent to each user with trades

## Setup
1. Clone repository
2. Create a `.env` file (copy `.env.example`)
3. Install dependencies:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

4. Run:
python bot.py

5. Talk to your bot on Telegram: `/start`, `/log`

## Notes
- Storage: `sqlite:///trading_journal.db` by default. Change `DATABASE_URL` to a Postgres URI to scale.
- To run in production, switch to webhooks + HTTPS or deploy to a managed service. Use `uvicorn` + FastAPI for webhook mode.

## Next steps
- Add trading visualizations (charts)
- Add integration with TradingView alerts
- Implement per-user timezone settings
- Add authentication for group use and admin controls

