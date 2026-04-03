import yfinance as yf
import pandas as pd
import numpy as np
import ta
import joblib
import statsmodels.api as sm
import warnings

warnings.filterwarnings("ignore")
print("🔬 Initializing Academic Statistical Regression Engine...")

# 1. DEFINE THE BASKET
tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS"]

# 2. LOAD YOUR ML MODEL
try:
    model_daily = joblib.load("bolt_quant_model_daily.pkl")
    print("✅ ML Model loaded successfully.")
except:
    print("❌ ERROR: Could not find 'bolt_quant_model_daily.pkl'.")
    exit()

all_data = []

print("📡 Fetching historical panel data and calculating probabilities...")
for ticker in tickers:
    df = yf.Ticker(ticker).history(period="5y")
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
    
    # Proxy for Historical Beta (20-day rolling volatility)
    df['Historical_Vol'] = df['Daily_Return'].rolling(window=20).std() * np.sqrt(252)
    
    df = df.dropna()
    
    # Extract ML Features and get the PROBABILITY of a win (not just 1 or 0)
    features = ['Daily_Return', 'RSI', 'MACD', 'BB_High_Ind', 'BB_Low_Ind', 'SMA_20_Pct', 'SMA_50_Pct']
    X_ml = df[features]
    
    # Get the probability that the stock will go up (Class 1)
    df['ML_Probability'] = model_daily.predict_proba(X_ml)[:, 1]
    
    # Define Target Variables for the Regressions
    df['Next_Day_Return'] = df['Close'].shift(-1) / df['Close'] - 1 # For Linear Regression
    df['Target_Win'] = np.where(df['Next_Day_Return'] > 0, 1, 0)    # For Logistic Regression
    
    df = df.dropna()
    all_data.append(df)

# Combine all stock data into one massive DataFrame (Panel Data)
master_df = pd.concat(all_data)

# ==========================================
# TEST 1: PRIMARY LINEAR REGRESSION (OLS)
# Formula: Return_i = β0 + β1*RSI + β2*MACD + β3*Vol + β4*MLProb + ε
# ==========================================
print("\n" + "="*60)
print("📊 TEST 1: OLS LINEAR REGRESSION (Predicting Exact Return)")
print("="*60)

# Define Independent Variables (X) and Dependent Variable (Y)
X_linear = master_df[['RSI', 'MACD', 'Historical_Vol', 'ML_Probability']]
X_linear = sm.add_constant(X_linear) # Adds the Beta_0 intercept
Y_linear = master_df['Next_Day_Return']

# Fit the OLS Model
ols_model = sm.OLS(Y_linear, X_linear).fit()
print(ols_model.summary())

# ==========================================
# TEST 2: LOGISTIC REGRESSION (Logit)
# Formula: P(Y=1) = 1 / (1 + e^-(β0 + β1*RSI + β2*MACD + β3*Vol + β4*MLProb))
# ==========================================
print("\n" + "="*60)
print("📈 TEST 2: LOGISTIC REGRESSION (Predicting Win/Loss Probability)")
print("="*60)

# Define Dependent Variable (Y) as Binary (1 or 0)
Y_logit = master_df['Target_Win']

try:
    # Fit the Logistic Model
    logit_model = sm.Logit(Y_logit, X_linear).fit(disp=0)
    print(logit_model.summary())
except Exception as e:
    print(f"Logistic Regression failed to converge: {e}")

print("\n✅ Regressions complete. Copy these tables into your research paper!")