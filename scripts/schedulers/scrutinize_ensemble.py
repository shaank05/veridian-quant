import pandas as pd
import numpy as np
import os

def perform_deep_ensemble_scrutiny():
    # Target your main historical backtest report output file
    csv_file = "backtest_report_20200101.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ Target report file '{csv_file}' not found in the current directory.")
        print("Please ensure you are running this from your root workspace directory where your CSV reports live.")
        return

    # Load backtest dataset
    df = pd.read_csv(csv_file)
    
    # Standardize column strings gracefully
    df.columns = [c.strip() for c in df.columns]

    print("\n" + "="*80)
    print(" 🔎 VERIDIAN QUANT SYSTEM ANALYSIS: DEEP ENSEMBLE METRIC SCRUTINY TRAIL ")
    print("="*80 + "\n")

    # Grouping profiles to isolate your top-performing low-score anomaly
    brackets = [
        ("LOW CONVICTION CRITICAL EDGE ZONE (< 40%)", df[df['ensemble_strength_score'] < 40]),
        ("MID CONVICTION CONGESTION PIT (40% - 70%)", df[(df['ensemble_strength_score'] >= 40) & (df['ensemble_strength_score'] <= 70)]),
        ("HIGH CONVICTION REGIME TREND ZONE (> 70%)", df[df['ensemble_strength_score'] > 70])
    ]

    for label, slice_df in brackets:
        print(f"🔷 {label}")
        total_trades = len(slice_df)
        if total_trades == 0:
            print("   ⚠️ No historical trades recorded inside this mathematical cluster.\n")
            continue
            
        # Calculate metric distribution characteristics safely
        targets = len(slice_df[slice_df['outcome'] == 'HIT_TARGET'])
        stops = len(slice_df[slice_df['outcome'] == 'HIT_STOP_LOSS'])
        expired = len(slice_df[slice_df['outcome'] == 'EXPIRED'])
        win_rate = (targets / total_trades) * 100
        
        avg_pnl = slice_df['pnl_percentage'].mean() if 'pnl_percentage' in slice_df.columns else 0.0
        
        print(f"   • Data Points Captured  : {total_trades} trades")
        print(f"   • Realized Win Rate     : {win_rate:.2f}% (Targets: {targets} | Stops: {stops} | Expired: {expired})")
        print(f"   • Average Return (PnL)  : {avg_pnl:.2f}%")
        
        # --- CORE COMPONENT INTERACTION TRACKING ---
        print("   • Core Component Baselines inside this slice:")
        for metric in ['z_score', 'shannon_entropy', 'fft_cycle_period', 'rawrs_score']:
            if metric in slice_df.columns:
                print(f"     - Mean {metric:<18}: {slice_df[metric].mean():.2f}")
        print("-" * 80)

if __name__ == "__main__":
    perform_deep_ensemble_scrutiny()