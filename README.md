## ****⚡ RayTurnz AI Stock Analyzer****

An AI-powered financial analysis platform that combines **live market data**, **quantitative models**, **fundamental analysis**, and **generative AI** to evaluate stocks and mutual funds across **NSE, BSE, and NYSE/NASDAQ**.

Built with Python and Streamlit, RayTurnz is designed to simulate a **mini institutional research terminal** for investors, analysts, and finance professionals.

---

## **What It Does**

RayTurnz helps users analyze a stock or mutual fund through a multi-layered decision engine:

- **Live market lookup** for Indian and US equities
- **Technical analysis** using RSI, MACD, Bollinger Bands, and SMA-based signals
- **Machine learning predictions** for short-term market direction
- **Fundamental screening** with valuation, profitability, liquidity, and solvency checks
- **AI-generated verdicts** that summarize the final outlook
- **News intelligence** from multiple sources with sentiment synthesis
- **Mutual fund analytics** with risk-adjusted performance metrics

---

## **Market Coverage**

RayTurnz supports:

- **India:** NSE and BSE stocks
- **US:** NYSE and NASDAQ stocks
- **Mutual Funds:** Indian mutual fund universe

The app includes market-aware ticker resolution, so users can search by **company name or ticker** and get the correct instrument automatically.

---

## 🔍 Core Features

### 1. Live Stock Analyzer
- Fetches real-time and historical market data
- Supports company search by name or ticker
- Displays price action, trend direction, and 52-week position

### 2. Technical Signal Engine
- RSI for momentum strength
- MACD for trend reversal confirmation
- Bollinger Bands for volatility positioning
- SMA distance features for short- and medium-term trend detection

### 3. Quant ML Model
- Random Forest-based classifiers for:
  - **Next-day direction**
  - **Next-week direction**
- Uses engineered market features
- Outputs bullish/bearish probability
- Backtested against the **NIFTY 50**

### 4. Fundamental Risk Scanner
- Profitability: margins, ROE, ROA
- Balance sheet strength: cash, debt, current ratio, quick ratio
- Valuation: P/E, P/B, PEG, EV/EBITDA
- Growth: revenue growth, earnings growth, payout ratio
- Red-flag detection for:
  - negative margins
  - weak liquidity
  - high debt
  - cash burn
  - expensive valuation
  - volatility risk

### 5. AI Verdict Engine
- Uses Google Gemini to generate a concise investment summary
- Synthesizes:
  - trend
  - technical indicators
  - ML prediction
  - red flags
  - news sentiment
- Produces a final **Bullish / Bearish / Hold** style verdict

### 6. News Intelligence
- Aggregates headlines from multiple sources
- Cross-verifies market news
- Uses AI to extract:
  - sentiment
  - core narrative
  - irrelevant macro noise

### 7. Mutual Fund Analytics
- Searches and compares Indian mutual funds
- Benchmarks against **NIFTY 50**
- Calculates:
  - CAGR
  - Alpha
  - Beta
  - Sharpe Ratio
  - Sortino Ratio
  - Max Drawdown
  - Capture Ratios
- Generates a custom overall score for fund comparison

### 8. Advanced Valuation Tools
- Multi-stage intrinsic value framework
- CAPM-based required return
- Beta regression and Jensen’s Alpha
- DuPont analysis
- Altman Z-Score
- DCF-style equity valuation

---

##  Why This Project Stands Out

This project is more than a stock dashboard. It combines:

- **Market data engineering**
- **Feature engineering**
- **Machine learning**
- **Financial modeling**
- **Risk management**
- **Generative AI reasoning**
- **Multi-source news analysis**

It reflects the kind of thinking used in:
- equity research
- portfolio analysis
- fintech analytics
- quant research support tools
- investment decision systems

---

##  Tech Stack

**Frontend:** Streamlit  
**Backend / Analytics:** Python, Pandas, NumPy  
**Market Data:** yfinance, Yahoo Finance feeds  
**ML:** scikit-learn, joblib  
**Technical Indicators:** ta  
**AI:** Google Gemini API  
**Visualization:** Plotly  
**Reports:** FPDF  

---

##  Project Structure

- `app.py` — main Streamlit application
- `data_engine.py` — all data fetching, analysis, valuation, and AI logic
- `train_model.py` — trains the ML models and saves backtest results
- `bolt_quant_model_daily.pkl` — daily prediction model
- `bolt_quant_model_weekly.pkl` — weekly prediction model
- `backtest_results.json` — strategy backtest summary

---

##  How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
