import pandas as pd
import numpy as np
import os

def analyze_backtest_matrix():
    # Target your newly generated multi-strategy matrix file
    csv_file = "backtest_report_20200101.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ Could not locate {csv_file}. Verify your current working directory.")
        return

    print("📊 Loading Parallel Strategy Registry Backtest Ledger...")
    df = pd.read_csv(csv_file)
    
    total_trades = len(df)
    print(f"📈 Total Baseline Z-Score Signals Triggered: {total_trades}")
    print("-" * 60)

    # Helper function to compute institutional analytics
    def calculate_metrics(data_slice, label):
        if len(data_slice) == 0:
            print(f"⚠️ No matching trades found for setup: {label}")
            return
        
        wins = len(data_slice[data_slice['outcome'] == 'HIT_TARGET'])
        losses = len(data_slice[data_slice['outcome'] == 'HIT_STOP_LOSS'])
        expired = len(data_slice[data_slice['outcome'] == 'EXPIRED'])
        
        win_rate = (wins / len(data_slice)) * 100
        
        total_profit = data_slice[data_slice['pnl_amount'] > 0]['pnl_amount'].sum()
        total_loss = abs(data_slice[data_slice['pnl_amount'] < 0]['pnl_amount'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        avg_days = data_slice[data_slice['outcome'] == 'HIT_TARGET']['days_to_result'].mean()
        
        print(f"🧬 PROFILE: {label}")
        print(f"   Trades Executed : {len(data_slice)}")
        print(f"   Win Rate        : {win_rate:.2f}% (Targets: {wins} | Stops: {losses} | Expired: {expired})")
        print(f"   Profit Factor   : {profit_factor:.2f}x")
        print(f"   Avg Days to TP  : {avg_days:.1f} sessions")
        print("-" * 60)

    # 1. Evaluate the absolute Baseline performance profile
    calculate_metrics(df, "RAW CORE Z-SCORE SETUP (No Filtering Multi-Matrix)")

    # 2. Evaluate the Shannon Entropy Noise Shield Gate
    if 'shannon_entropy_vote' in df.columns:
        calculate_metrics(df[df['shannon_entropy_vote'] == 1], "FILTERED BY SHANNON ENTROPY (Low Chaos Noise Shield Active)")

    # 3. Evaluate the FFT Phase Timing Gate
    if 'fft_cycle_turning_vote_vote' in df.columns: # Maps precisely to flattened matrix key
        calculate_metrics(df[df['fft_cycle_turning_vote_vote'] == 1], "FILTERED BY FFT CYCLE (Momentum Turning Verified)")
    elif 'fft_cycle_turning_vote' in df.columns:
        calculate_metrics(df[df['fft_cycle_turning_vote'] == 1], "FILTERED BY FFT CYCLE (Momentum Turning Verified)")

    # 4. Evaluate the Volume Spread Analysis Stance Gate
    if 'vsa_confirmed_vote_vote' in df.columns:
        calculate_metrics(df[df['vsa_confirmed_vote_vote'] == 1], "FILTERED BY VSA (Institutional Accumulation Confirmed)")
    elif 'vsa_confirmed_vote' in df.columns:
        calculate_metrics(df[df['vsa_confirmed_vote'] == 1], "FILTERED BY VSA (Institutional Accumulation Confirmed)")

    # 5. Evaluate the Anti-Cascade Markov Transition State Gate
    if 'markov_vote_vote' in df.columns:
        calculate_metrics(df[df['markov_vote_vote'] == 1], "FILTERED BY MARKOV OVERLAYS (Protected from State 0 Cascades)")
    elif 'markov_vote' in df.columns:
        calculate_metrics(df[df['markov_vote'] == 1], "FILTERED BY MARKOV OVERLAYS (Protected from State 0 Cascades)")

    # 6. Evaluate High Conviction Ensemble Sweet Spots (Stage 5 Simulation)
    if 'ensemble_conviction_score' in df.columns:
        high_conviction = df[df['ensemble_conviction_score'] >= 75.0]
        calculate_metrics(high_conviction, "HIGH CONVICTION ENSEMBLE (Conviction Score >= 75.0%)")

if __name__ == "__main__":
    analyze_backtest_matrix()