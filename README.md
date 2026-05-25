# Medallion Quant Prototype (Indian Equity Market)

An algorithmic trading platform inspired by the Medallion Fund's high-efficiency data handling. This prototype focuses on the Indian Equity and F&O markets, utilizing a "Modular Monolith" architecture with TimescaleDB.

## 📊 Data Architecture
The system uses a parent-child relationship for instruments to optimize for both high-frequency trading and long-term quantitative research. It utilizes TimescaleDB to handle massive time-series datasets efficiently.

- **`instruments` (Master)**: The central registry for all assets (Stocks, Commodities, and F&O contracts).
- **`instrument_derivatives` (Active)**: A specialized table for metadata of live F&O contracts (Expiry, Strike, Option Type).
- **`instruments_expired_archive`**: Cold storage for expired contract metadata, ensuring the primary tables stay lean while supporting historical backtesting.
- **`prices_ohlc` (Hypertable)**: Stores raw 1-minute.
- **`ohlc_5m, ohlc_15m, ohlc_1h, ohlc_1d, ohlc_1w, ohlc_1M` (Continuous Aggregate)**: Materialized views for high-performance time-series analysis.

## 🛠 Tech Stack
- **Language**: Python 3.10+ (Logic) & Node.js (Real-time Backend)
- **Database**: PostgreSQL with TimescaleDB extension
- **Data Provider**: Upstox API via Factory Pattern
- **Environment**: Linux (Ubuntu) via PuTTY

## 🚀 Getting Started
1. **Initialize DB**: `python -m scripts.init_db`
2. **Sync Metadata**: `python -m scripts.sync_instruments`
3. **Ingest Prices**: 
   - Set `DATA_INGESTION_MODE=WATCHLIST` in `.env`.
   - Run `python -m scripts.price_ingestion`
4. **Manual View Kickstart (First Time Only)**:
   Because views are created `WITH NO DATA` for speed, you must manually refresh them after your first big historical backfill:
   - CALL refresh_continuous_aggregate('ohlc_5m', NULL, NULL);
   - CALL refresh_continuous_aggregate('ohlc_15m', NULL, NULL);
   - CALL refresh_continuous_aggregate('ohlc_1h', NULL, NULL);
   - CALL refresh_continuous_aggregate('ohlc_1d', NULL, NULL);

## 🛠 Maintenance:
- Historical Gap Filling: If you modify historical data, use refresh_continuous_aggregate(view, start, end) to re-calculate those specific dates.
- Background Policies: Daily data is automatically aggregated by TimescaleDB policies every hour.