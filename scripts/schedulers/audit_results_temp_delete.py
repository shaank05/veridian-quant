import pandas as pd
import numpy as np
import os

def run_deep_annualized_profit_audit():
    csv_file = "backtest_report_20200101.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ Could not locate {csv_file}")
        return

    df = pd.read_csv(csv_file)
    
    # Clean and parse timeline keys
    df['backtest_date'] = pd.to_datetime(df['backtest_date'])
    df['year'] = df['backtest_date'].dt.year

    print("\n" + "="*115)
    print("      🎯 TRUE SYSTEM BENCHMARK ENGINE: SIDE-BY-SIDE ANNUALIZED MATRIX      ")
    print("="*115 + "\n")

    rawrs_col = 'rawrs_modifier' if 'rawrs_modifier' in df.columns else ('rawrs_score' if 'rawrs_score' in df.columns else None)

    def get_slices(dataframe):
        # Clean baseline comparison structure
        slice_baseline = dataframe.copy()
        
        # Simple, non-flawed evaluation gate using pure historical column attributes
        # Setting a standard structural filter baseline
        if rawrs_col:
            slice_experiment = dataframe[dataframe[rawrs_col] >= 0.70].copy()
        else:
            slice_experiment = dataframe.copy()
            
        return slice_baseline, slice_experiment

    def compute_metrics(data_slice):
        total = len(data_slice)
        if total == 0:
            return {"trades": 0, "wr": 0, "pf": 0, "hits": 0, "sls": 0, "exp": 0, "net_pnl": 0}
            
        hits = len(data_slice[data_slice['outcome'].isin(['HIT_TARGET', 'TARGET', 'T'])])
        sls = len(data_slice[data_slice['outcome'].isin(['HIT_STOP_LOSS', 'SL', 'S'])])
        exp = len(data_slice[data_slice['outcome'].isin(['EXPIRED', 'E'])])
        
        win_rate = (hits / total) * 100

        net_pnl = data_slice['pnl_amount'].sum() if 'pnl_amount' in data_slice.columns else 0.0
        gross_profit = data_slice[data_slice['pnl_amount'] > 0]['pnl_amount'].sum() if 'pnl_amount' in data_slice.columns else 0
        gross_loss = abs(data_slice[data_slice['pnl_amount'] < 0]['pnl_amount'].sum()) if 'pnl_amount' in data_slice.columns else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {"trades": total, "wr": win_rate, "pf": pf, "hits": hits, "sls": sls, "exp": exp, "net_pnl": net_pnl}

    def print_metric_block(label, m):
        print(f"      |-- {label:<11} -> Trades: {m['trades']:<4} | Win Rate: {m['wr']:5.2f}% (T: {m['hits']:<3} | S: {m['sls']:<3} | E: {m['exp']:<3}) | PF: {m['pf']:.2f}x | Net Cash PnL: ₹{m['net_pnl']:,.2f}")

    # --- ANNUALIZED BREAKDOWNS ---
    years = sorted(df['year'].unique())
    for year in years:
        df_year = df[df['year'] == year]
        base_slice, exp_slice = get_slices(df_year)
        
        m_base = compute_metrics(base_slice)
        m_exp = compute_metrics(exp_slice)
        pnl_delta = m_exp["net_pnl"] - m_base["net_pnl"]
        delta_sign = "+" if pnl_delta >= 0 else ""
        
        print(f"📅 PERIOD TIMELINE AUDIT: {year}")
        print_metric_block("OLD BASELINE", m_base)
        print_metric_block("NEW OPTIMIZED", m_exp)
        print(f"      |>>> 📈 NET PNL CASH VARIANCE ACCRETION : {delta_sign}₹{pnl_delta:,.2f}")
        print("-" * 115)

    # --- CUMULATIVE AGGREGATE SUMMARY ---
    print("\n" + "═"*115)
    print("                           📊 SIX-YEAR AGGREGATE CUMULATIVE PORTFOLIO PERFORMANCE SUMMARY                           ")
    print("═"*115 + "\n")
    
    total_base, total_exp = get_slices(df)
    m_t_base = compute_metrics(total_base)
    m_t_exp = compute_metrics(total_exp)
    total_delta = m_t_exp["net_pnl"] - m_t_base["net_pnl"]
    total_sign = "+" if total_delta >= 0 else ""

    print_metric_block("TOTAL CONTROL BASELINE ", m_t_base)
    print_metric_block("TOTAL EXPERIMENT MATRIC", m_t_exp)
    print("\n" + "═"*115)
    print(f" 🏆 ULTIMATE CUMULATIVE MULTI-YEAR PROFIT SHIFT : {total_sign}₹{total_delta:,.2f}")
    print("═"*115 + "\n")

if __name__ == "__main__":
    run_deep_annualized_profit_audit()