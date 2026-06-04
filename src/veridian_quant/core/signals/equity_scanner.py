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
    generate_rawrs_wavelet_signature,
    calculate_wavelet_momentum_intensity,
    calculate_dominant_cycle
)
from src.veridian_quant.core.analytics.markov_analysis import calculate_transition_matrix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EquityScanner:
    """
    Unified Parallel Node Strategy Registry Engine.
    
    Evolved Variant: Implements complete Phase A continuous surface calculations,
    on-the-fly Nifty macro calculation, and restored production persistence tracking.
    """
    def __init__(self, db_engine, mode='PROD', source_table='ohlc_1d'):
        self.engine = db_engine
        self.mode = mode
        self.source_table = source_table
        
        self.node_z_score_enabled = os.getenv("NODE_Z_SCORE_ENABLED", "True") == "True"
        self.node_fft_enabled = os.getenv("NODE_FFT_ENABLED", "True") == "True"
        self.node_entropy_enabled = os.getenv("NODE_ENTROPY_ENABLED", "True") == "True"
        self.node_cwt_enabled = os.getenv("NODE_CWT_ENABLED", "True") == "True"
        self.node_markov_enabled = os.getenv("NODE_MARKOV_ENABLED", "True") == "True"

        self.node_z_score_threshold = float(os.getenv("NODE_Z_SCORE_THRESHOLD", "-2.5"))
        self.node_entropy_max_threshold = float(os.getenv("NODE_ENTROPY_MAX_THRESHOLD", "2.1"))
        
        # Institutional Regime-Adaptive Node Weight Allocations Matrix
        self.regime_weights_tensor = {
            "BULL_CALM":           {"z": 0.50, "rawrs": 0.25, "fft": 0.15, "markov": 0.10},
            "VOL_EXPANSION":       {"z": 0.35, "rawrs": 0.45, "fft": 0.10, "markov": 0.10},
            "BEAR_STRESS":          {"z": 0.25, "rawrs": 0.55, "fft": 0.10, "markov": 0.10},
            "CHOP_MEAN_REVERTING":  {"z": 0.40, "rawrs": 0.30, "fft": 0.15, "markov": 0.10}
        }
        
        logger.info("⚡ [RAWRS STABILIZED BALANCED REGIME ROUTER MATRIX ACTIVE]")

    def _calculate_macro_regime_on_the_fly(self, conn, run_date: str) -> str:
        """
        Dynamically extracts macro indicators using the absolute instrument key for Nifty 50.
        """
        query = text(f"""
            SELECT p.timestamp AS date, p.close 
            FROM {self.source_table} p
            WHERE p.instrument_key = 'NSE_INDEX|Nifty 50' AND p.timestamp::date <= :run_date 
            ORDER BY p.timestamp DESC LIMIT 80;
        """)
        try:
            df = pd.read_sql(query, conn, params={"run_date": run_date})
            if df.empty or len(df) < 52:
                return "BULL_CALM", 0.0
                
            df = df.iloc[::-1].reset_index(drop=True)
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            current_sma = df['sma_50'].iloc[-1]
            prior_sma = df['sma_50'].iloc[-4] # 3-day momentum lookback
            
            if pd.isna(current_sma) or pd.isna(prior_sma) or prior_sma == 0:
                return "BULL_CALM", 0.0
                
            nifty_slope = (current_sma - prior_sma) / prior_sma
            
            if nifty_slope < -0.002:
                return "BEAR_STRESS", nifty_slope
            elif nifty_slope > 0.003:
                return "VOL_EXPANSION", nifty_slope
            else:
                return "BULL_CALM", nifty_slope
        except Exception as e:
            logger.error(f"⚠️ Dynamic macro calculation error: {str(e)}. Falling back to BULL_CALM.")
            return "BULL_CALM", 0.0

    def _calculate_rawrs_conviction_modulation(self, sig: dict, regime: str) -> tuple:
        """
        Continuous Wavelet Surface Scoring Engine.
        Integrates Meso-Energy variables to eliminate discrete boolean cliff vulnerabilities.
        """
        micro = sig["micro_energy"]
        meso  = sig["meso_energy"]
        macro = sig["macro_energy"]
        entropy = sig["spectral_entropy"]
        coherence = sig["coherence"]
        
        surface_score = (0.35 * macro) + (0.25 * meso) - (0.30 * micro) + (0.20 * coherence)
        
        if regime == "BULL_CALM":
            rawrs_score = surface_score * 1.20
            label = "CONTINUOUS_BULL_PULLBACK"
        elif regime == "VOL_EXPANSION":
            rawrs_score = surface_score * 1.00 + (0.10 * coherence)
            label = "CONTINUOUS_EXPANSION_FLOW"
        elif regime == "BEAR_STRESS":
            rawrs_score = surface_score * 0.70 - (0.20 * micro)
            label = "CONTINUOUS_BEAR_PROTECTION"
        else:
            chaos_penalty = max(0.0, entropy - 1.50)
            rawrs_score = surface_score * 0.90 - (0.15 * chaos_penalty)
            label = "CONTINUOUS_CHOP_ROTATION"
            
        normalized_score = float(np.clip((rawrs_score + 1.0) / 2.0, 0.0, 1.0))
        return normalized_score, label

    def execute_concurrent_analysis(self, tickers_data_package: dict, run_date: str) -> list:
        recommendation_payload_batch = []
        
        with self.engine.connect() as conn:
            current_market_regime, live_nifty_slope = self._calculate_macro_regime_on_the_fly(conn, run_date)
            
        weights = self.regime_weights_tensor[current_market_regime]
        
        for symbol, historical_df in tickers_data_package.items():
            print(f"🔍 [SCANNER INSTANCE PROGRESS] Processing multi-strategy parallel evaluation algorithms tracking payload node -> [{symbol}]")
            if symbol == 'NIFTY': 
                continue
            try:
                if historical_df.empty or len(historical_df) < 40: 
                    print(f"⏭️ [LOOKBACK SHORTFALL] {symbol} skipped. Rows available: {len(historical_df)} (Scanner needs >= 40)")
                    continue
                
                payload_metrics = {
                    "z_score": 0.0, "expected_move": 0.0, "shannon_entropy": 0.0,
                    "wavelet_intensity": 1.0, "fft_cycle_period": 0.0, "markov_regime_state": 0,
                    "micro_energy": 1.0, "meso_energy": 1.0, "macro_energy": 1.0,
                    "spectral_entropy": 0.5, "coherence": 1.0, "rawrs_modifier": 0.5,
                    "rawrs_topology_label": "UNINITIALIZED", "vix_value": 15.0, "nifty_slope": live_nifty_slope
                }
                
                close_series = historical_df['close']
                terminal_close_price = close_series.iloc[-1]
                
                if self.node_z_score_enabled:
                    z_history = calculate_z_score(close_series)
                    payload_metrics["z_score"] = float(z_history.iloc[-1])
                    payload_metrics["expected_move"] = float(calculate_expected_move(close_series).iloc[-1])
                    
                if self.node_entropy_enabled:
                    payload_metrics["shannon_entropy"] = float(calculate_shannon_entropy(close_series))
                    
                if self.node_fft_enabled:
                    payload_metrics["fft_cycle_period"] = float(calculate_dominant_cycle(close_series))
                    
                if self.node_markov_enabled:
                    log_returns = np.log(close_series / close_series.shift(1)).dropna().tail(30)
                    if len(log_returns) >= 20:
                        t_matrix = calculate_transition_matrix(log_returns)
                        payload_metrics["markov_regime_state"] = int(np.argmax(np.diagonal(t_matrix)))
                        
                if self.node_cwt_enabled:
                    rawrs_sig = generate_rawrs_wavelet_signature(close_series)
                    payload_metrics.update({
                        "micro_energy": rawrs_sig["micro_energy"],
                        "meso_energy": rawrs_sig["meso_energy"],
                        "macro_energy": rawrs_sig["macro_energy"],
                        "spectral_entropy": rawrs_sig["spectral_entropy"],
                        "coherence": rawrs_sig["coherence"],
                        "wavelet_intensity": rawrs_sig["wavelet_intensity"]
                    })
                    rawrs_mod, topology_lbl = self._calculate_rawrs_conviction_modulation(rawrs_sig, current_market_regime)
                    payload_metrics["rawrs_modifier"] = rawrs_mod
                    payload_metrics["rawrs_topology_label"] = topology_lbl

                # --- UNLOCKED CONTINUOUS STRATEGY SURFACE PASS ---
                # Removed hard binary limits to unlock continuous weighting downstream
                core_triggered = payload_metrics["z_score"] < self.node_z_score_threshold
                
                # Attenuate triggering gracefully under high noise environments instead of absolute vetoes
                if self.node_entropy_enabled and payload_metrics["shannon_entropy"] > self.node_entropy_max_threshold:
                    if payload_metrics["rawrs_modifier"] < 0.60:
                        core_triggered = False
                    
                if core_triggered:
                    ensemble_votes = []
                    
                    z_displacement = abs(payload_metrics["z_score"])
                    z_weight = 1.0 if z_displacement >= 3.0 else (z_displacement / 3.0)
                    ensemble_votes.append(z_weight * weights["z"])
                    
                    ensemble_votes.append(payload_metrics["rawrs_modifier"] * weights["rawrs"])
                    
                    fft_confirmed = check_cycle_phase(close_series)
                    fft_weight = 1.0 if fft_confirmed else 0.20
                    ensemble_votes.append(fft_weight * weights["fft"])
                    
                    markov_weight = 0.80 if payload_metrics["markov_regime_state"] in [0, 1] else 0.40
                    ensemble_votes.append(markov_weight * weights["markov"])
                    
                    ensemble_strength_score = float(np.sum(ensemble_votes) * 100.0)
                    
                    target_spread = max(payload_metrics["expected_move"] * 2.5, terminal_close_price * 0.05)
                    stop_spread = max(payload_metrics["expected_move"] * 1.5, terminal_close_price * 0.03)
                    
                    recommendation_record = {
                        "instrument_key": ticker_data_package_meta_extract(historical_df, "instrument_key", symbol),
                        "symbol": symbol,
                        "entry_price": float(terminal_close_price),
                        "target_price": float(terminal_close_price + target_spread),
                        "stop_loss_price": float(terminal_close_price - stop_spread),
                        "expected_duration_days": int(max(10, min(30, int(target_spread / (payload_metrics["expected_move"] + 1e-5))))),
                        "market_regime": current_market_regime,
                        "metrics": payload_metrics
                    }
                    
                    recommendation_record["metrics"]["ensemble_strength_score"] = ensemble_strength_score
                    recommendation_payload_batch.append(recommendation_record)
                    
                    logger.info(
                        f"🎯 [STABILIZED SURFACE TARGET MATCH] -> {symbol} | "
                        f"Base Z: {payload_metrics['z_score']:.2f} | "
                        f"Strength Score: {ensemble_strength_score:.1f}%"
                    )
                    
                    if self.mode == 'PROD':
                        self.save_recommendation(recommendation_record)

                else:
                    print(f"⏭️ [STRATEGY SURFACE MISMATCH] Asset [{symbol}] on [{run_date}] did not cross base Z threshold boundaries (Z: {payload_metrics['z_score']:.2f}). Skipping signal logging layout pipelines.")
                    
            except Exception as loop_error:
                logger.error(f"❌ Scanner loop tracking failure on symbol [{symbol}]: {str(loop_error)}")
                continue
                
        return recommendation_payload_batch

    def save_recommendation(self, rec: dict):
        """
        Persists generated strategy signals into the production database system tables.
        """
        query = text("""
            INSERT INTO test_table_recommendations 
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
                    'target_1': rec['target_price'],  
                    'stop_loss': rec['stop_loss_price'],
                    'expected_duration_days': rec['expected_duration_days'],
                    'strategies_involved': ['PARALLEL_ENSEMBLE_MATRIX'],
                    'notes': (
                        f"Regime: {rec['market_regime']} | "
                        f"Base Z: {rec['metrics']['z_score']:.2f} | "
                        f"RAWRS Topo: {rec['metrics']['rawrs_topology_label']} | "
                        f"RAWRS Mod: {rec['metrics']['rawrs_modifier']:.2f} | "
                        f"Strength Score: {rec['metrics']['ensemble_strength_score']:.1f}%"
                    )
                })
            logger.info(f"✅ Production transaction recommendation successfully archived for asset token: {rec['symbol']}")
        except Exception as e:
            logger.error(f"❌ Production table persistence crash matching asset token [{rec['symbol']}]: {str(e)}")

def ticker_data_package_meta_extract(df: pd.DataFrame, key_str: str, fallback: str) -> str:
    if hasattr(df, 'attrs') and key_str in df.attrs: 
        return str(df.attrs[key_str])
    return fallback