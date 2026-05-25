# Deployment & Automation Guide

This document outlines how to move the Medallion Quant Prototype from manual development runs to an automated production environment.

## 1. Environment Setup
Ensure the following are configured on the production server:
- ## Database PostgreSQL with TimescaleDB extension.
- ## Python Version 3.10+ with `uv` or `pip` installed.
- ## The `.env` file must now contain:
    - ## ACTIVE_DATA_PROVIDER 
    - ## UPSTOX_ACCESS_TOKEN 
    - ## DB_URL
    - ## DATA_INGESTION_MODE: `WATCHLIST` (Dev/Backtest) or `FULL` (Production).
    - ## MAX_PAGINATION_DAYS_1M`: Set to 30 for stability.
    - ## HISTORICAL_LOOKBACK_DAYS`: Set to 0 to use incremental "Delta" sync logic.

## 2. Directory Structure
Ensure a logs directory exists to capture automated output:
mkdir -p logs

## 3. Automation (Cron Jobs)
Use `crontab -e` on the server to schedule these tasks. These ensure the "Medallion" system maintains itself without manual intervention.

| Task | Schedule | Purpose |
| :--- | :--- | :--- |
| **Instrument Sync** | 08:30 AM (Daily) | Syncs the full market "phonebook" from Upstox. |
| **Historical Ingest** | 04:30 PM (Daily) | Pulls OHLCV candles after market close. |
| **Expiry Cleanup** | 03:00 AM (Sat) | Archives expired F&O data to keep live tables fast. |

### Crontab Configuration Examples:
# 3.1 Daily Full Market Sync
30 8 * * * cd /path/to/project && python3 -m scripts.sync_instruments >> logs/sync.log 2>&1

# 3.2 Daily Price Ingestion (Post-Market)
30 16 * * * cd /path/to/project && python3 -m scripts.ingest_historical >> logs/ingest.log 2>&1

# 3.3 Weekly Expiry Cleanup & Archiving
0 3 * * 6 cd /path/to/project && python3 -m scripts.cleanup_expired >> logs/cleanup.log 2>&1

## 4. Monitoring & Troubleshooting
Since automated jobs run in the background, use these commands to verify health:
# 4.1 Check Logs
View the last few lines of the sync or ingestion process:
tail -n 50 logs/sync.log
tail -n 50 logs/ingest.log

# 4.2 Live Tail
Watch the logs in real-time as the cron job runs:
tail -f logs/sync.log

# 4.3 Process Check
If a job seems stuck, check if the Python process is still active:
ps aux | grep python

## 5. Production Best Practices
- **Incremental Sync**: The `PriceIngestor` checks the database for existing data before calling the API. In `FULL` mode, this ensures the daily update only takes a few minutes.
- **Source of Truth**: In production, prefer syncing 1-minute data and using TimescaleDB aggregates for higher timeframes to ensure mathematical consistency.