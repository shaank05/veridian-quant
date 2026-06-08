import pandas as pd
import numpy as np

# Load your generated backtest report file
# Replace filename with your actual generated output file (e.g., 'slope_+_low_vix_backtest_report_...csv')
df = pd.read_csv("backtest_report_20200101.csv")

print("==========================================================================")
print("     🧬 ENSEMBLE STRENGTH SCORE CONVICTION DISTRIBUTION AUDIT TRAIL        ")
print("==========================================================================\n")

# Segment the historical results into your planned conviction buckets
brackets = [
    ("LOW CONVICTION ZONE (< 40%)", df[df['ensemble_strength_score'] < 40]),
    ("MID CONVICTION GLIDE ZONE (40% - 70%)", df[(df['ensemble_strength_score'] >= 40) & (df['ensemble_strength_score'] <= 70)]),
    ("HIGH CONVICTION APEX ZONE (> 70%)", df[df['ensemble_strength_score'] > 70])
]

for label, slice_df in brackets:
    print(f"🔷 {label}")
    total_trades = len(slice_df)
    if total_trades == 0:
        print("   No trades found in this profile bracket.\n")
        continue
        
    # Calculate Win Rate metrics safely
    targets = len(slice_df[slice_df['outcome'] == 'HIT_TARGET'])
    stops = len(slice_df[slice_df['outcome'] == 'HIT_STOP_LOSS'])
    expired = len(slice_df[slice_df['outcome'] == 'EXPIRED'])
    win_rate = (targets / total_trades) * 100
    
    # Calculate performance expectancy factors
    avg_pnl_pct = slice_df['pnl_percentage'].mean() if 'pnl_percentage' in slice_df.columns else 0.0
    
    print(f"   • Total Trades Executed : {total_trades}")
    print(f"   • Realized Win Rate     : {win_rate:.2%}% (Targets: {targets} | Stops: {stops} | Expired: {expired})")
    print(f"   • Avg PnL % Per Trade   : {avg_pnl_pct:.2f}%")
    print("-" * 74)