import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import warnings
import ta
import json

warnings.filterwarnings("ignore")

def apply_technicals_and_targets(df):
    df['Daily_Return'] = df['Close'].pct_change()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BB_High_Ind'] = bb.bollinger_hband_indicator()
    df['BB_Low_Ind'] = bb.bollinger_lband_indicator()
    
    # 👇 SAFELY CONVERTED TO PERCENTAGE DISTANCE 👇
    sma_20 = ta.trend.sma_indicator(close=df['Close'], window=20)
    df['SMA_20_Pct'] = (df['Close'] - sma_20) / sma_20
    
    sma_50 = ta.trend.sma_indicator(close=df['Close'], window=50)
    df['SMA_50_Pct'] = (df['Close'] - sma_50) / sma_50
    
    # 🎯 TARGET 1: Next Day
    df['Next_Day_Return'] = df['Close'].shift(-1).pct_change()
    df['Target_Daily'] = np.where(df['Next_Day_Return'] > 0, 1, 0)
    
    # 🎯 TARGET 2: Next Week (5 Trading Days)
    df['Next_Week_Return'] = df['Close'].shift(-5).pct_change()
    df['Target_Weekly'] = np.where(df['Next_Week_Return'] > 0, 1, 0)
    
    df.dropna(inplace=True)
    return df

# ... (keep your training loop exactly the same) ...

# 👇 UPDATE THE FEATURES LIST TO MATCH 👇
features = ['Daily_Return', 'RSI', 'MACD', 'BB_High_Ind', 'BB_Low_Ind', 'SMA_20_Pct', 'SMA_50_Pct']

# ==========================================
# PHASE 1: TRAINING (Pre-2022 Data Only)
# ==========================================
print("📥 Phase 1: Fetching ALL-TIME historical data for AI Training...")
tickers = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.BO', 'SBIN.NS', 'ICICIBANK.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LT.NS']
train_data = []

for ticker in tickers:
    stock = yf.Ticker(ticker)
    df = stock.history(period="max")
    if len(df) > 100:
        df = apply_technicals_and_targets(df)
        df = df[df.index < '2022-01-01'] 
        train_data.append(df)

final_train_df = pd.concat(train_data)
features = ['Daily_Return', 'RSI', 'MACD', 'BB_High_Ind', 'BB_Low_Ind', 'SMA_20_Pct', 'SMA_50_Pct']
X_train = final_train_df[features]

y_train_daily = final_train_df['Target_Daily']
y_train_weekly = final_train_df['Target_Weekly']

print(f"\n🧠 Training Daily Brain...")
model_daily = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)
model_daily.fit(X_train, y_train_daily)

print(f"🧠 Training Weekly Brain...")
model_weekly = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)
model_weekly.fit(X_train, y_train_weekly)

# ==========================================
# PHASE 2: TESTING (2022 - Present)
# ==========================================
print("\n📈 Phase 2: Running Out-of-Sample Backtest on NIFTY 50 Index...")
nifty = yf.Ticker("^NSEI")
test_df = nifty.history(period="max")
test_df = apply_technicals_and_targets(test_df)
test_df = test_df[test_df.index >= '2022-01-01']

X_test = test_df[features]
returns_test_daily = test_df['Next_Day_Return']

# --- BACKTESTING MATH ---
# Market Baseline
cumulative_market = (1 + returns_test_daily).cumprod() - 1
total_market_return = cumulative_market.iloc[-1] * 100

# Daily Strategy
preds_daily = model_daily.predict(X_test)
strategy_returns_daily = returns_test_daily * preds_daily
cum_strategy_daily = (1 + strategy_returns_daily).cumprod() - 1
total_daily_return = cum_strategy_daily.iloc[-1] * 100
acc_daily = model_daily.score(X_test, test_df['Target_Daily']) * 100

# Weekly Strategy
preds_weekly = model_weekly.predict(X_test)
strategy_returns_weekly = returns_test_daily * preds_weekly
cum_strategy_weekly = (1 + strategy_returns_weekly).cumprod() - 1
total_weekly_return = cum_strategy_weekly.iloc[-1] * 100
acc_weekly = model_weekly.score(X_test, test_df['Target_Weekly']) * 100

print(f"\n📉 Market Buy & Hold: {total_market_return:.2f}%")
print(f"🎯 Daily AI Accuracy: {acc_daily:.2f}% | Profit: {total_daily_return:.2f}%")
print(f"🎯 Weekly AI Accuracy: {acc_weekly:.2f}% | Profit: {total_weekly_return:.2f}%")

backtest_data = {
    "market_return": f"{total_market_return:.2f}%",
    "daily": {
        "accuracy": f"{acc_daily:.2f}%",
        "return": f"{total_daily_return:.2f}%",
        "beat": bool(total_daily_return > total_market_return)
    },
    "weekly": {
        "accuracy": f"{acc_weekly:.2f}%",
        "return": f"{total_weekly_return:.2f}%",
        "beat": bool(total_weekly_return > total_market_return)
    }
}

with open("backtest_results.json", "w") as f:
    json.dump(backtest_data, f)

joblib.dump(model_daily, 'bolt_quant_model_daily.pkl')
joblib.dump(model_weekly, 'bolt_quant_model_weekly.pkl')
print("\n💾 Both Models & Backtests saved! Run Streamlit app now.")