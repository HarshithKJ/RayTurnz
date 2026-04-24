import yfinance as yf
import pandas as pd
import numpy as np
import ta
import joblib
import statsmodels.api as sm
import warnings

warnings.filterwarnings("ignore")
print("🔬 Initializing IIMB-Tier Macro-Economic Regression Engine...")

# 1. DEFINE THE BASKETS
tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS"]

# 2. LOAD YOUR ML MODEL
try:
    model_daily = joblib.load("bolt_quant_model_daily.pkl")
    print("✅ ML Model loaded successfully.")
except:
    print("❌ ERROR: Could not find 'bolt_quant_model_daily.pkl'.")
    exit()

# Helper function to safely clean timezones from Yahoo Finance dates
def clean_dates(df):
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    return df

# 3. FETCH MACROECONOMIC DATA (The "IIMB Upgrade")
print("🌍 Fetching Macroeconomic Risk Factors (NIFTY, VIX, USD/INR)...")

nifty = clean_dates(yf.Ticker("^NSEI").history(period="5y"))['Close']
vix = clean_dates(yf.Ticker("^INDIAVIX").history(period="5y"))['Close']
usdinr = clean_dates(yf.Ticker("USDINR=X").history(period="5y"))['Close']

# Safely combine them and FORWARD FILL holidays
macro_data = pd.DataFrame({
    'NIFTY_Close': nifty,
    'VIX_Close': vix,
    'USDINR_Close': usdinr
}).ffill().dropna()

# Calculate the Macro Returns
macro_data['NIFTY_Return'] = macro_data['NIFTY_Close'].pct_change()
macro_data['VIX_Change'] = macro_data['VIX_Close'].pct_change()
macro_data['USDINR_Return'] = macro_data['USDINR_Close'].pct_change()
macro_data = macro_data[['NIFTY_Return', 'VIX_Change', 'USDINR_Return']]

# 4. FETCH STOCK DATA & MERGE
all_data = []
print("📡 Fetching historical stock data and running ML predictions...")
for ticker in tickers:
    df = clean_dates(yf.Ticker(ticker).history(period="5y"))
    if df.empty: continue
    
    # Calculate Technical Features
    df['Daily_Return'] = df['Close'].pct_change()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BB_High_Ind'] = bb.bollinger_hband_indicator()
    df['BB_Low_Ind'] = bb.bollinger_lband_indicator()
    
    sma_20 = ta.trend.sma_indicator(close=df['Close'], window=20)
    df['SMA_20_Pct'] = (df['Close'] - sma_20) / sma_20
    sma_50 = ta.trend.sma_indicator(close=df['Close'], window=50)
    df['SMA_50_Pct'] = (df['Close'] - sma_50) / sma_50
    
    df['Stock_Vol'] = df['Daily_Return'].rolling(window=20).std() * np.sqrt(252)
    
    # Join with Macro Data and drop missing values
    merged_df = df.join(macro_data, how='inner')
    merged_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    merged_df = merged_df.dropna()
    
    if merged_df.empty: continue
    
    # Extract ML Features and get the PROBABILITY
    features = ['Daily_Return', 'RSI', 'MACD', 'BB_High_Ind', 'BB_Low_Ind', 'SMA_20_Pct', 'SMA_50_Pct']
    X_ml = merged_df[features]
    merged_df['ML_Probability'] = model_daily.predict_proba(X_ml)[:, 1]
    
    # Define Target Variables
    merged_df['Next_Day_Return'] = merged_df['Close'].shift(-1) / merged_df['Close'] - 1 
    merged_df['Target_Win'] = np.where(merged_df['Next_Day_Return'] > 0, 1, 0)    
    
    merged_df = merged_df.dropna()
    all_data.append(merged_df)

# Combine into master panel data
if not all_data:
    print("❌ ERROR: All data was dropped during cleaning. Check internet connection.")
    exit()
    
master_df = pd.concat(all_data)

# ==========================================
# TEST 1: ADVANCED OLS LINEAR REGRESSION
# ==========================================
print("\n" + "="*75)
print("📊 TEST 1: INSTITUTIONAL OLS REGRESSION (Controlling for Macro Risk)")
print("="*75)

X_linear = master_df[['RSI', 'MACD', 'Stock_Vol', 'NIFTY_Return', 'VIX_Change', 'USDINR_Return', 'ML_Probability']]
X_linear = sm.add_constant(X_linear) 
Y_linear = master_df['Next_Day_Return']

ols_model = sm.OLS(Y_linear, X_linear).fit()
print(ols_model.summary())

# ==========================================
# TEST 2: ADVANCED LOGISTIC REGRESSION 
# ==========================================
print("\n" + "="*75)
print("📈 TEST 2: INSTITUTIONAL LOGIT REGRESSION (Win/Loss Probability)")
print("="*75)

Y_logit = master_df['Target_Win']

try:
    logit_model = sm.Logit(Y_logit, X_linear).fit(disp=0)
    print(logit_model.summary())
except Exception as e:
    print(f"Logistic Regression failed: {e}")

print("\n✅ Advanced Macro-Regressions complete. You are ready for IIMB!")