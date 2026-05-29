import pandas as pd
import logging
import numpy as np
import os
from sqlalchemy import text
from veridian_quant.core.analytics.vectorized_math import (
    calculate_z_score, 
    calculate_expected_move,
    check_cycle_phase,
    calculate_shannon_entropy,
    calculate_wavelet_momentum_intensity  # Stage 2.2 Node integration anchor
)
from src.veridian_quant.core.analytics.markov_analysis import calculate_transition_matrix

# Logging profile layout configuration setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EquityScanner:
    """
    Unified Parallel Node Strategy Registry Engine.
    
    Coordinates the execution of quantitative mathematical strategies simultaneously.
    Instead of executing as a traditional linear filtering pipeline where failures abort processing,
    this component evaluates all statistical states concurrently, packaging them into a uniform 
    multi-dimensional nested dictionary data payload structure for production or backtesting.
    """
    def __init__(self, db_engine, mode='PROD', source_table='ohlc_1d'):
        """
        Initializes the calculation engine state and extracts global master matrix toggles.
        """
        self.engine = db_engine
        self.mode = mode
        self.source_table = source_table
        
        # Unpack Parallel Master Core Signals Matrix environment configurations
        self.node_z_score_enabled = os.getenv("NODE_Z_SCORE_ENABLED", "true").lower() == "true"
        self.node_z_score_lookback = int(os.getenv("NODE_Z_SCORE_LOOKBACK", "20"))
        
        self.node_macro_regime_enabled = os.getenv("NODE_MACRO_REGIME_ENABLED", "true").lower() == "true"
        
        self.node_entropy_enabled = os.getenv("NODE_SHANNON_ENTROPY_ENABLED", "true").lower() == "true"
        self.node_entropy_lookback = int(os.getenv("NODE_SHANNON_ENTROPY_LOOKBACK", "20"))
        self.node_entropy_max_threshold = float(os.getenv("NODE_SHANNON_ENTROPY_MAX_THRESHOLD", "0.75"))
        
        self.node_fft_enabled = os.getenv("NODE_FFT_TIMING_ENABLED", "true").lower() == "true"
        self.node_vsa_enabled = os.getenv("NODE_VSA_VALIDATION_ENABLED", "true").lower() == "true"
        
        self.node_markov_enabled = os.getenv("NODE_MARKOV_CASCADE_ENABLED", "true").lower() == "true"
        self.node_markov_lookback = int(os.getenv("NODE_MARKOV_LOOKBACK_DAYS", "90"))
        self.node_markov_max_persistence = float(os.getenv("NODE_MARKOV_MAX_PERSISTENCE", "0.60"))
        
        # Advanced Phase Expansion Registry Toggles
        self.node_cwt_enabled = os.getenv("NODE_CWT_ANALYSIS_ENABLED", "true").lower() == "true"
        self.node_cwt_activation_threshold = float(os.getenv("NODE_CWT_ACTIVATION_THRESHOLD", "1.90"))
        self.node_mc_enabled = os.getenv("NODE_MONTE_CARLO_ENABLED", "false").lower() == "true"
        self.node_bayesian_enabled = os.getenv("NODE_BAYESIAN_MASTER_ENABLED", "false").lower() == "true"

        print(f"📡 Parallel Scanner Engine Instantiated | Mode: {self.mode} | Database Source Target Table: {self.source_table}")
        print(f"⚙️ Enabled Registries: Z-Score={self.node_z_score_enabled}, Macro={self.node_macro_regime_enabled}, Entropy={self.node_entropy_enabled}, FFT={self.node_fft_enabled}, VSA={self.node_vsa_enabled}, Markov={self.node_markov_enabled}, CWT={self.node_cwt_enabled}")

    def get_dynamic_z_threshold(self, as_of_date=None):
        """
        Determines the dynamic Z-Score threshold based on India VIX, 
        Nifty 50 50-SMA location, and its structural % slope velocity.
        """
        target_date = as_of_date if as_of_date else pd.Timestamp.now().date()
        
        try:
            vix_res, nifty_res = self._fetch_market_context_data(target_date)
            
            if not vix_res or not nifty_res or len(nifty_res) < 55:
                return -2.5, 0.0, "UNKNOWN"
            
            vix = float(vix_res[0])
            is_bullish, regime, _ = self._calculate_nifty_momentum(nifty_res)
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
        
        # Block configurations showing massive institutional liquidation risk
        if relative_volume >= 1.5 and closing_position <= 0.3:
            return False, relative_volume, closing_position, "STANCE_LIQUIDATION"
            
        vsa_status = "STANCE_ABSORPTION" if closing_position >= 0.5 else "STANCE_NEUTRAL"
        return True, relative_volume, closing_position, vsa_status

    def scan_instrument(self, instrument_key, symbol, as_of_date=None):
        """
        Master Telemetry Processing Matrix Node Entry Point.
        
        Gathers structural inputs and routes execution concurrently across all strategy scripts,
        returning a complete descriptive voting payload mapping the specific transaction date.
        """
        # 1. Fetch historical data slices and global dynamic macro context parameters
        dynamic_threshold, current_vix, regime = self.get_dynamic_z_threshold(as_of_date=as_of_date)
        
        # Ensure deep history requirements are reached to compute the full analytical suite safely
        lookback_limit = max(self.node_markov_lookback + 25, 120)
        df = self.fetch_data(instrument_key, limit=lookback_limit, as_of_date=as_of_date)
        
        if len(df) < 60:
            return None

        # 2. Base Statistical Signal Ingestion Engine (Z-Score Core Base)
        z_scores = calculate_z_score(df['close'])
        latest_z = z_scores.iloc[-1]

        if pd.isna(latest_z):
            return None

        # Determine if the asset has met the baseline core crash reversal entry threshold
        core_triggered = latest_z < dynamic_threshold

        # Initialize structured nested tracking schemas to hold calculations concurrently
        payload_metrics = {
            "z_score": float(latest_z),
            "vix_value": float(current_vix),
            "dynamic_threshold": float(dynamic_threshold),
            "shannon_entropy": 0.0,
            "markov_p_persistence": 0.0,
            "vsa_relative_volume": 1.0,
            "vsa_closing_position": 0.5,
            "wavelet_intensity": 1.0,        # Stage 2.2 Live Metric
            "ensemble_conviction_score": 0.0  # Stage 5 Hub Anchor
        }

        payload_votes = {
            "z_score_triggered": bool(core_triggered),
            "shannon_entropy_vote": False,
            "fft_cycle_turning_vote": False,
            "vsa_confirmed_vote": False,
            "markov_vote": False,
            "cwt_spectrum_vote": False,       # Stage 2.2 Active Registry
            "monte_carlo_vote": False         # Stage 4 Placeholder
        }

        # CONCURRENT MATRIX EVALUATION LOOP (Executes regardless of core_triggered state)
        
        # NODE CODE 1: Shannon Information Entropy Noise Shield Node
        if self.node_entropy_enabled:
            entropy_val = calculate_shannon_entropy(df['close'], window=self.node_entropy_lookback)
            payload_metrics["shannon_entropy"] = float(entropy_val)
            # A vote passes only if the systemic chaos remains inside bounds
            payload_votes["shannon_entropy_vote"] = bool(entropy_val <= self.node_entropy_max_threshold)

        # NODE CODE 1.5: Stage 2.2 Continuous Wavelet Transform (CWT) Node
        if self.node_cwt_enabled:
            try:
                wavelet_val = calculate_wavelet_momentum_intensity(df['close'])
                payload_metrics["wavelet_intensity"] = float(wavelet_val)
                # True signals a massive high-frequency velocity expansion regime
                payload_votes["cwt_spectrum_vote"] = bool(wavelet_val >= self.node_cwt_activation_threshold)
            except Exception as e:
                logger.error(f"Failed concurrent Wavelet processing calculation: {e}")
                payload_metrics["wavelet_intensity"] = 1.0
                payload_votes["cwt_spectrum_vote"] = False

        # NODE CODE 2: Fast Fourier Transform Wave Phase Turning Node
        if self.node_fft_enabled:
            is_cycle_turning = check_cycle_phase(df['close'])
            payload_votes["fft_cycle_turning_vote"] = bool(is_cycle_turning)

        # NODE CODE 3: Volume Spread Analysis Structural Node
        if self.node_vsa_enabled:
            vsa_passed, rel_vol, close_pos, vsa_stance = self._validate_vsa_profile(df)
            payload_metrics["vsa_relative_volume"] = float(rel_vol)
            payload_metrics["vsa_closing_position"] = float(close_pos)
            payload_votes["vsa_confirmed_vote"] = bool(vsa_passed)

        # NODE CODE 4: Point-In-Time Markov Chain Transition Regime Node
        if self.node_markov_enabled:
            # Recompute standard terminal rolling Z-scores matching historical tracking boundaries
            mean_series = df['close'].rolling(window=20).mean()
            std_series = df['close'].rolling(window=20).std()
            z_series = (df['close'] - mean_series) / std_series
            clean_z_slice = z_series.tail(self.node_markov_lookback).reset_index(drop=True)
            
            try:
                t_matrix = calculate_transition_matrix(clean_z_slice)
                p_crater_persistence = t_matrix[0][0]
                payload_metrics["markov_p_persistence"] = float(p_crater_persistence)
                # Markov selection clears only if asset is safe from structural down-cascade persistence
                payload_votes["markov_vote"] = bool(p_crater_persistence <= self.node_markov_max_persistence)
            except Exception as e:
                logger.error(f"Failed concurrent Markov processing calculation: {e}")
                payload_votes["markov_vote"] = False

        # STAGE 5 ARCHITECTURE: Unified Bayesian Ensemble Weighting Module
        # Dynamically increments empirical execution conviction based on parallel responses
        total_enabled_nodes = 0
        passed_votes = 0
        
        # Note: cwt_spectrum_vote is deliberately excluded from the traditional binary ensemble pool
        # to preserve its continuous scale and isolate it as an absolute execution overrule shield.
        for key in ["shannon_entropy_vote", "fft_cycle_turning_vote", "vsa_confirmed_vote", "markov_vote"]:
            total_enabled_nodes += 1
            if payload_votes[key]:
                passed_votes += 1
                
        conviction_pct = (passed_votes / total_enabled_nodes) * 100 if total_enabled_nodes > 0 else 0.0
        payload_metrics["ensemble_conviction_score"] = round(conviction_pct, 2)

        # --- CWT HARD CUTOFF OVERRULE SHIELD ---
        # Intercepts active setup execution orders if micro-velocity conditions are unmet
        if core_triggered and self.node_cwt_enabled:
            if payload_metrics["wavelet_intensity"] < self.node_cwt_activation_threshold:
                logger.info(f"⚠️ [{symbol}] Base setup aborted by CWT Alpha Shield: Intensity ({payload_metrics['wavelet_intensity']:.4f}) < Floor ({self.node_cwt_activation_threshold:.4f})")
                core_triggered = False

        # 4. Generate Target Boundaries using Average True Range (ATR Multipliers)
        atr_values = calculate_expected_move(df['close'])
        latest_atr = float(atr_values.iloc[-1])
        latest_price = float(df['close'].iloc[-1])
        
        stop_loss = latest_price - (2 * latest_atr)
        target_price = latest_price + (4 * latest_atr)
        expected_days = int((target_price - latest_price) / latest_atr) if latest_atr > 0 else 30

        # Construct unified return interface mapping structural variables safely
        return {
            "core_setup_triggered": core_triggered,
            "instrument_key": instrument_key,
            "trading_symbol": symbol,
            "entry_price": latest_price,
            "target_price": target_price,
            "stop_loss_price": stop_loss,
            "expected_duration_days": expected_days,
            "market_regime": regime,
            "metrics": payload_metrics,
            "votes": payload_votes
        }

    def save_recommendation(self, rec):
        """Persists identified trading setups into the database layers."""
        if not rec:
            return

        query = text("""
            INSERT INTO equity_recommendations 
            (instrument_key, trading_symbol, investment_type, entry_price, 
             target_1, stop_loss, expected_duration_val, expected_duration_unit, strategies_involved, 
             notes, status)
            VALUES (:instrument_key, :trading_symbol, 'SWING', :entry_price, 
                    :target_1, :stop_loss, :expected_duration_days, 'DAYS', :strategies_involved, 
                    :notes, 'PENDING');
        """)

        try:
            with self.engine.begin() as conn: 
                conn.execute(query, {
                    'instrument_key': rec['instrument_key'],
                    'trading_symbol': rec['symbol'],
                    'entry_price': rec['entry_price'],
                    'target_1': rec['target_price'],  # Preserved property assignment
                    'stop_loss': rec['stop_loss_price'],
                    'expected_duration_days': rec['expected_duration_days'],
                    'strategies_involved': ['PARALLEL_ENSEMBLE_MATRIX'],
                    'notes': f"Regime: {rec['market_regime']} | VIX: {rec['metrics']['vix_value']:.2f} | Base Z: {rec['metrics']['z_score']:.2f} | CWT Intensity: {rec['metrics']['wavelet_intensity']:.2f}"
                })
            logger.info(f"✅ Production transaction recommendation successfully archived for asset token: {rec['trading_symbol']}")
        except Exception as e:
            logger.error(f"Failed to save recommendation execution payload for {rec['trading_symbol']}: {e}")