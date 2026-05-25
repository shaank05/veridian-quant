import pandas as pd
from src.veridian_quant.data.db_client import DatabaseClient
from sqlalchemy import text

def analyze_vix_impact(report_path):
    db = DatabaseClient()
    engine = db.get_engine()
    
    # 1. Load your existing backtest report
    df = pd.read_csv(report_path)
    df['signal_date'] = pd.to_datetime(df['signal_date']).dt.date
    
    # 2. Fetch VIX data from your new table
    query = text("""
        SELECT timestamp::date as signal_date, close as vix_close 
        FROM market_indicators 
        WHERE indicator_name = 'INDIA_VIX'
    """)
    
    with engine.connect() as conn:
        vix_df = pd.read_sql(query, conn)
    
    # 3. Merge Backtest results with VIX levels
    merged_df = pd.merge(df, vix_df, on='signal_date', how='left')
    
    # 4. Create VIX Buckets for analysis
    bins = [0, 15, 20, 25, 30, 100]
    labels = ['10-15 (Calm)', '15-20 (Normal)', '20-25 (High)', '25-30 (Stress)', '30+ (Panic)']
    merged_df['vix_bucket'] = pd.cut(merged_df['vix_close'], bins=bins, labels=labels)
    
    # 5. Calculate Stats per Bucket
    stats = merged_df.groupby('vix_bucket', observed=False).agg({
        'outcome': lambda x: (x == 'HIT_TARGET').sum(),
        'symbol': 'count'
    }).rename(columns={'outcome': 'Targets', 'symbol': 'Total_Trades'})
    
    stats['Win_Rate_%'] = (stats['Targets'] / stats['Total_Trades'] * 100).round(2)
    
    print("\n📊 VIX IMPACT ANALYSIS")
    print("="*50)
    print(stats)
    print("="*50)
    
    return merged_df

if __name__ == "__main__":
    # Use your 2020 report as the first test case since it has the most variance
    analyze_vix_impact('backtest_report_20250101.csv')