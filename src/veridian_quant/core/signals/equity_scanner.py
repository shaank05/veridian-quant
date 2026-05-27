import pandas as pd
import logging
import numpy as np
import os
from sqlalchemy import text
from veridian_quant.core.analytics.vectorized_math import (
    calculate_z_score, 
    calculate_expected_move,
    check_cycle_phase,
    calculate_shannon_entropy
)
from src.veridian_quant.core.analytics.markov_analysis import calculate_transition_matrix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EquityScanner:
    def __init__(self, db_engine, mode='PROD', source_table='ohlc_1d'):
        """
        Initializes the Scanner.
        :param mode: 'PROD' (enforces one active trade) or 'BACKTEST' (logs all signals).
        :param source_table: 'ohlc_1d' for Prod views, 'prices_ohlc' for Dev historical table.
        """
        self.engine = db_engine
        self.mode = mode
        self.source_table = source_table
        
        # Parse environment configuration parameters for the Markov filter layer
        # Set to force-false/disabled to transition system capital back to clean baseline metrics
        self.markov_enabled = False
        self.markov_lookback = int(os.getenv("MARKOV_LOOKBACK_DAYS", "90"))
        # Swapped from min probability hurdle to an anti-cascade maximum persistence ceiling threshold
        self.markov_max_persistence = float(os.getenv("MARKOV_MAX_PERSISTENCE_THRESHOLD", "0.60"))

        # Parse environment configurations for Stage 2.1 Shannon Entropy Noise Shield Gate
        self.entropy_enabled = os.getenv("ENTROPY_FILTER_ENABLED", "false").lower() == "true"
        self.entropy_lookback = int(os.getenv("ENTROPY_LOOKBACK_DAYS", "20"))
        self.entropy_max_threshold = float(os.getenv("ENTROPY_MAX_THRESHOLD", "0.75"))

    def get_dynamic_z_threshold(self, as_of_date=None):
        """
        Determines the dynamic Z-Score threshold based on India VIX, 
        Nifty 50 50-SMA location, and its structural % slope velocity.
        """
        target_date = as_of_date if as_of_date else pd.Timestamp.now().date()
        
        try:
            # 1. Fetch raw context metrics from database layers
            vix_res, nifty_res = self._fetch_market_context_data(target_date)
            
            if not vix_res or not nifty_res or len(nifty_res) < 55:
                logger.warning(f"Insufficient Market Data for {target_date} (Need 55 Nifty bars). Using default -2.5")
                return -2.5, 0.0, "UNKNOWN"
            
            # 2. Derive trend structural and velocity dynamics
            vix = float(vix_res[0])
            is_bullish, regime, sma_slope_pct = self._calculate_nifty_momentum(nifty_res)
            
            # 3. Apply conditional boundary mapping matrix
            threshold = self._evaluate_regime_threshold(vix, is_bullish, nifty_res)
                
            return threshold, vix, regime
            
        except Exception as e:
            logger.error(f"Error in Trend-Aware Context Engine: {e}")
            return -2.5, 0.0, "ERROR"

    def _fetch_market_context_data(self, target_date):
        """Extracts macro indicator parameters from storage engines."""
        vix_query = text("""
            SELECT close FROM market_indicators 
            WHERE indicator_name = 'INDIA_VIX' 
            AND timestamp::date <= :target_date
            ORDER BY timestamp DESC LIMIT 1
        """)
        
        nifty_query = text("""
            SELECT close FROM prices_ohlc 
            WHERE instrument_key = 'NSE_INDEX|Nifty 50'
            AND timestamp::date <= :target_date
            ORDER BY timestamp DESC LIMIT 55
        """)
        
        with self.engine.connect() as conn:
            vix_res = conn.execute(vix_query, {"target_date": target_date}).fetchone()
            nifty_res = conn.execute(nifty_query, {"target_date": target_date}).fetchall()
            
        return vix_res, nifty_res

    def _calculate_nifty_momentum(self, nifty_res):
        """Analyzes historical pricing paths to quantify velocity filters."""
        nifty_prices = [float(row[0]) for row in nifty_res]
        latest_nifty = nifty_prices[0]
        
        current_window = nifty_prices[0:50]   
        prior_window = nifty_prices[5:55]     
        
        latest_sma50 = sum(current_window) / len(current_window)
        prior_sma50 = sum(prior_window) / len(prior_window)
        
        sma_slope_pct = ((latest_sma50 - prior_sma50) / prior_sma50) * 100
        
        MIN_SLOPE_HURDLE = 0.10 
        is_price_above_sma = latest_nifty > latest_sma50
        is_slope_accelerating = sma_slope_pct >= MIN_SLOPE_HURDLE
        
        is_bullish = is_price_above_sma or is_slope_accelerating
        regime = "BULL_SLOPE_50" if is_bullish else "BEAR_FLAT_50"
        
        return is_bullish, regime, sma_slope_pct

    def _evaluate_regime_threshold(self, vix, is_bullish, nifty_res):
        """Maps specific mathematical thresholds to current volatility matrix bounds."""
        nifty_prices = [float(row[0]) for row in nifty_res]
        latest_nifty = nifty_prices[0]
        latest_sma50 = sum(nifty_prices[0:50]) / 50
        sma_slope_pct = ((latest_sma50 - (sum(nifty_prices[5:55]) / 50)) / (sum(nifty_prices[5:55]) / 50)) * 100
        
        is_price_above_sma = latest_nifty > latest_sma50
        is_slope_accelerating = sma_slope_pct >= 0.10

        if vix < 13:
            is_true_bull_squeeze = is_price_above_sma and is_slope_accelerating
            return -2.0 if is_true_bull_squeeze else -2.8
        elif 13 <= vix < 15:
            return -2.2 if (is_price_above_sma and is_slope_accelerating) else -2.8
        elif 15 <= vix < 25:
            return -2.2  
        elif 25 <= vix < 30:
            return -2.5  
        else: 
            return -3.0  

    def fetch_data(self, instrument_key, interval='day', limit=250, as_of_date=None):
        """Fetches historical price and volume data up to a specific 'as_of_date'."""
        query_parts = [f"SELECT timestamp, close, high, low, open, volume FROM {self.source_table} WHERE instrument_key = :inst_key"]
        params = {"inst_key": instrument_key}

        if self.source_table == 'prices_ohlc':
            query_parts.append("AND interval = :interval")
            params["interval"] = interval

        if as_of_date:
            query_parts.append("AND timestamp <= :as_of_date")
            params["as_of_date"] = as_of_date

        query_parts.append("ORDER BY timestamp DESC LIMIT :limit")
        params["limit"] = limit

        full_query = text(" ".join(query_parts))

        try:
            df = pd.read_sql(full_query, self.engine, params=params)
            if df.empty:
                return pd.DataFrame()
            return df.sort_values('timestamp') 
        except Exception as e:
            logger.error(f"SQL Error on {instrument_key}: {e}")
            return pd.DataFrame()

    def is_already_recommended(self, symbol):
        """Checks for any existing 'PENDING' or 'ACTIVE' recommendations to avoid duplication."""
        query = text("""
            SELECT count(*) FROM equity_recommendations 
            WHERE trading_symbol = :symbol 
              AND status IN ('PENDING', 'ACTIVE');
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"symbol": symbol})
            return result.scalar() > 0

    def _validate_production_markov_regime(self, instrument_key, symbol, as_of_date):
        """
        Isolated verification method to check the live end-of-day Markov regime status.
        Returns True if the asset clears the threshold transition requirements, False if blocked.
        """
        if not self.markov_enabled or self.mode != 'PROD':
            return True  # Instantly clear validation if disabled or running in simulation backtest mode
            
        # Pull an extra 20 rows beyond lookback configuration to guarantee stable rolling indicators
        lookback_limit = self.markov_lookback + 20
        prod_df = self.fetch_data(instrument_key, limit=lookback_limit, as_of_date=as_of_date)
        
        if prod_df.empty or len(prod_df) < self.markov_lookback:
            logger.warning(f"Insufficient live historical bars found to execute production Markov validation for {symbol}.")
            return True  # Fail-safe open boundary path to prevent skipping valid inputs on system data gaps
            
        # Recompute standard terminal rolling Z-scores matching the production close timeline
        prod_mean = prod_df['close'].rolling(window=20).mean()
        prod_std = prod_df['close'].rolling(window=20).std()
        prod_z_scores = (prod_df['close'] - prod_mean) / prod_std
        
        # Extract the clean matrix input slice matching the configuration lookback days
        clean_z_slice = prod_z_scores.tail(self.markov_lookback).reset_index(drop=True)
        
        # Run transition calculation across the active asset tracking history
        transition_matrix = calculate_transition_matrix(clean_z_slice)
        p_crater_persistence = transition_matrix[0][0]
        
        # Suppress trade generation if stock has a high probability of cascading down further inside State 0
        if p_crater_persistence > self.markov_max_persistence:
            logger.info(f"🛡️ [Live Markov Anti-Cascade Block] {symbol} suppressed. P(Crater->Crater): {p_crater_persistence:.2f} > Max Ceiling: {self.markov_max_persistence}")
            return False
            
        return True

    def scan_instrument(self, instrument_key, symbol, as_of_date=None):
        """
        Applies macro trend-regime filters, statistical Z-score conditions, FFT timing cycle turns, 
        and Volume Spread Analysis validation layers to isolate setups.
        """
        dynamic_threshold, current_vix, regime = self.get_dynamic_z_threshold(as_of_date=as_of_date)

        df = self.fetch_data(instrument_key, as_of_date=as_of_date)
        if len(df) < 40:
            logger.debug(f"DEBUG: {symbol} only has {len(df)} rows. Need 40 for Spectral Analysis.")
            return None

        z_scores = calculate_z_score(df['close'])
        latest_z = z_scores.iloc[-1]

        if pd.isna(latest_z):
            print(f"DEBUG: {symbol} Z-score is NaN. Check your price data.")
            return None

        # Primary entry filter execution
        if latest_z < dynamic_threshold:
            
            # --- SHANNON INFORMATION ENTROPY PRE-SIGNAL FILTER ---
            if self.entropy_enabled:
                current_entropy = calculate_shannon_entropy(df['close'], window=self.entropy_lookback)
                if current_entropy > self.entropy_max_threshold:
                    logger.info(f"🛑 {symbol}: Blocked by Entropy Gate. Chaos: {current_entropy:.2f} > Threshold: {self.entropy_max_threshold} | Structural Noise Shield Engaged.")
                    return None
            
            # 1. FFT Timing Filter Gate
            is_cycle_turning = check_cycle_phase(df['close'])
            if not is_cycle_turning:
                logger.info(f"⏳ {symbol}: Z={latest_z:.2f} (Limit: {dynamic_threshold}), but FFT cycle is falling. Regime: {regime}")
                return None
            
            # 2. Volume Spread Analysis (VSA) Validation Gate
            vsa_passed, relative_volume, closing_position, vsa_status = self._validate_vsa_profile(df)
            if not vsa_passed:
                return None
                
            # 3. Modular Production Markov Regime Validation Gate
            if not self._validate_production_markov_regime(instrument_key, symbol, as_of_date):
                return None
            
            # TODO: Add Delivery Volume Analysis Gate (Track % Deliverable Quantity to confirm true long accumulation)
            
            # 4. Position Guard Rails Check
            if self.mode == 'PROD' and self.is_already_recommended(symbol):
                logger.info(f"Signal found for {symbol} but an active trade already exists. Skipping.")
                return None

            # 5. Generate Signal Output Metrics
            atr_values = calculate_expected_move(df['close'])
            latest_atr = float(atr_values.iloc[-1])
            latest_price = float(df['close'].iloc[-1])

            # TODO: Implement Stage 2.5 Dynamic Risk-Equalized Position Sizing Engine 
            # (Uses 1% total risk capital budget clamped to a 20% max fractional allocation ceiling)

            return self._compile_signal_payload(
                instrument_key, symbol, latest_price, latest_z, latest_atr, 
                current_vix, regime, dynamic_threshold, relative_volume, 
                closing_position, vsa_status
            )
        
        return None

    def _validate_vsa_profile(self, df):
        """Evaluates Volume Spread Analysis patterns to screen for institutional distribution risk."""
        latest_price = float(df['close'].iloc[-1])
        latest_volume = float(df['volume'].iloc[-1])
        volume_sma20 = df['volume'].rolling(window=20).mean().iloc[-1]
        relative_volume = (latest_volume / volume_sma20) if volume_sma20 > 0 else 1.0
        
        high_price = float(df['high'].iloc[-1])
        low_price = float(df['low'].iloc[-1])
        candle_range = high_price - low_price
        closing_position = (latest_price - low_price) / candle_range if candle_range > 0 else 0.5
        
        # Block setups showing high institutional liquidation risk (Extreme volume closing near the candle low)
        if relative_volume >= 1.5 and closing_position <= 0.3:
            logger.info(f"🚫 {df.index[-1]} blocked by VSA: RelVol {relative_volume:.2f} with weak Close Position {closing_position:.2f} (Institutional Liquidation risk).")
            return False, relative_volume, closing_position, "STANCE_LIQUIDATION"
            
        vsa_status = "STANCE_ABSORPTION" if closing_position >= 0.5 else "STANCE_NEUTRAL"
        return True, relative_volume, closing_position, vsa_status

    def _compile_signal_payload(self, instrument_key, symbol, latest_price, latest_z, latest_atr, 
                                current_vix, regime, dynamic_threshold, relative_volume, 
                                closing_position, vsa_status):
        """Packages strategy risk and target thresholds into uniform output payloads."""
        stop_loss = latest_price - (2 * latest_atr)
        target = latest_price + (4 * latest_atr)
        expected_days = int((target - latest_price) / latest_atr) if latest_atr > 0 else 0

        return {
            'instrument_key': instrument_key,
            'trading_symbol': symbol,
            'investment_type': 'SWING',
            'entry_price': latest_price,
            'target_1': target,
            'stop_loss': stop_loss,
            'z_score': latest_z,
            'vix_value': current_vix,
            'market_regime': regime,
            'dynamic_threshold': dynamic_threshold,
            'strategies_involved': ['Z_SCORE_REVERSION', 'FFT_CYCLE_TIMING', 'TREND_AWARE_VIX_FILTER', 'VOLUME_SPREAD_ANALYSIS'],
            
            'vsa_relative_volume': relative_volume,
            'vsa_closing_position': closing_position,
            'vsa_status': vsa_status,
            'notes': f"Regime: {regime} | VIX: {current_vix:.1f} | Limit: {dynamic_threshold} | Z: {latest_z:.2f} | RelVol: {relative_volume:.2f} | VSA: {vsa_status}"
        }

    def save_recommendation(self, rec):
        """Persists identified trading setups into the database."""
        if not rec:
            return

        query = text("""
            INSERT INTO equity_recommendations 
            (instrument_key, trading_symbol, investment_type, entry_price, 
             target_1, stop_loss, expected_duration_val, expected_duration_unit, strategies_involved, 
             notes, status)
            VALUES (:instrument_key, :trading_symbol, :investment_type, :entry_price, 
                    :target_1, :stop_loss, :expected_duration_days, 'DAYS', :strategies_involved, 
                    :notes, 'PENDING');
        """)

        try:
            with self.engine.begin() as conn: 
                conn.execute(query, {
                    'instrument_key': rec['instrument_key'],
                    'trading_symbol': rec['trading_symbol'],
                    'investment_type': rec['investment_type'],
                    'entry_price': rec['entry_price'],
                    'target_1': rec['target_1'],
                    'stop_loss': rec['stop_loss'],
                    'expected_duration_days': rec['expected_duration_days'],
                    'strategies_involved': rec['strategies_involved'],
                    'notes': rec['notes']
                })
            logger.info(f"✅ Recommendation saved for {rec['trading_symbol']}")
        except Exception as e:
            logger.error(f"Failed to save recommendation for {rec['trading_symbol']}: {e}")