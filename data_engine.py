import yfinance as yf
import pandas as pd
import ta
import joblib
import os
import requests
import google.generativeai as genai
from fpdf import FPDF
from scipy import stats
import streamlit as st
import requests

# Create a session that mimics a real Chrome browser
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 1. SETUP & FORMATTING
# ==========================================
def configure_ai(api_key):
    genai.configure(api_key=api_key)

def fmt_num(value):
    if value is None or pd.isna(value): return "N/A"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000: return f"{value / 1_000_000_000_000:.2f} T"
    elif abs_value >= 1_000_000_000: return f"{value / 1_000_000_000:.2f} B"
    elif abs_value >= 1_000_000: return f"{value / 1_000_000:.2f} M"
    else: return f"{value:,.2f}"

def fmt_pct(value):
    if value is None or pd.isna(value): return "N/A"
    return f"{value * 100:.2f}%"

def fmt_rat(value):
    if value is None or pd.isna(value): return "N/A"
    return f"{value:.2f}"

# ==========================================
# 2. DATA FETCHING PIPELINE
# ==========================================
def fetch_stock_data(raw_ticker, market="Auto"):
    # If market is "Auto", the Smart Search already attached the .NS or .BO suffix!
    if market == "Auto":
        ticker_input = raw_ticker
    elif market == "India (NSE)": 
        ticker_input = f"{raw_ticker}.NS"
    elif market == "India (BSE)": 
        ticker_input = f"{raw_ticker}.BO"
    else: 
        ticker_input = raw_ticker

    stock = yf.Ticker(ticker_input)
    info = stock.info
    hist = stock.history(period="max")
    
    success = ("currentPrice" in info or "regularMarketPrice" in info or not hist.empty)
    return success, ticker_input, info, hist

# ==========================================
# 3. HEADER & TREND LOGIC
# ==========================================
def get_header_metrics(info, hist):
    current_price = hist["Close"].iloc[-1] if not hist.empty else info.get("currentPrice", 0)
    price_1mo = hist["Close"].iloc[-22] if len(hist) >= 22 else current_price
    price_3mo = hist["Close"].iloc[-66] if len(hist) >= 66 else current_price

    if current_price > price_3mo: trend = "Uptrend 📈"
    elif current_price < price_3mo: trend = "Downtrend 📉"
    else: trend = "Sideways ➖"

    monthly_return = ((current_price - price_1mo) / price_1mo) * 100 if price_1mo else 0
    low_52 = info.get("fiftyTwoWeekLow", current_price)
    high_52 = info.get("fiftyTwoWeekHigh", current_price)
    position = (current_price - low_52) / (high_52 - low_52) if high_52 != low_52 else 0.5

    if position > 0.8: zone = "Near 52W High 🔥"
    elif position < 0.2: zone = "Near 52W Low 🧊"
    else: zone = "Mid Range ⚖️"
    
    return current_price, trend, monthly_return, position, zone

# ==========================================
# 4. DEEP FUNDAMENTALS CATEGORIES
# ==========================================
# ==========================================
# 4. DEEP FUNDAMENTALS CATEGORIES
# ==========================================
# ==========================================
# 4. DEEP FUNDAMENTALS CATEGORIES (INDIA OPTIMIZED)
# ==========================================
def get_red_flags(info):
    """Conducts a massive 20-point institutional risk scan with Indian Market Fallbacks."""
    flags = []
    
    # --- 1. Profitability & Operations Risk ---
    if info.get("profitMargins") is not None and info.get("profitMargins") < 0:
        flags.append(("Negative Profit Margin", fmt_pct(info.get("profitMargins"))))
    if info.get("operatingMargins") is not None and info.get("operatingMargins") < 0:
        flags.append(("Negative Op Margin", fmt_pct(info.get("operatingMargins"))))
    if info.get("returnOnEquity") is not None and info.get("returnOnEquity") < 0:
        flags.append(("Negative ROE", fmt_pct(info.get("returnOnEquity"))))
    if info.get("returnOnAssets") is not None and info.get("returnOnAssets") < 0:
        flags.append(("Negative ROA (Inefficient)", fmt_pct(info.get("returnOnAssets"))))
        
    # --- 2. Growth & Future Trajectory Risk ---
    if info.get("revenueGrowth") is not None and info.get("revenueGrowth") < 0:
        flags.append(("Declining Revenue", fmt_pct(info.get("revenueGrowth"))))
    if info.get("earningsGrowth") is not None and info.get("earningsGrowth") < 0:
        flags.append(("Declining Earnings", fmt_pct(info.get("earningsGrowth"))))

    # --- 3. Liquidity Risk (Short-term survival) ---
    if info.get("currentRatio") is not None and info.get("currentRatio") < 1.0:
        flags.append(("Low Liquidity (CR < 1)", fmt_rat(info.get("currentRatio"))))
        
    # --- 4. Solvency Risk (Long-term survival) ---
    if info.get("debtToEquity") is not None and info.get("debtToEquity") > 150:
        flags.append(("High Debt/Equity", f"{info.get('debtToEquity'):.1f}%"))
        
    # 👇 INDIA OVERRIDE: Catch Vodafone Idea (Yahoo hides D/E if Equity is negative)
  # 👇 INDIA OVERRIDE: Catch Vodafone Idea (Yahoo hides D/E if Equity is negative)
    if info.get("bookValue") is not None and info.get("bookValue") < 0:
        bv = info.get("bookValue")
        debt = info.get("totalDebt")
        
        # Format the debt nicely if it exists, otherwise leave it blank
        debt_str = f" | Total Debt: {fmt_num(debt)}" if debt else ""
        
        flags.append(("Severe Solvency Risk", f"Book Value: {bv:.2f} per share{debt_str}"))
        
    # --- 5. Cash Flow & Earnings Quality Risk ---
    fcf = info.get("freeCashflow")
    ocf = info.get("operatingCashflow") # Used frequently in Indian reporting
    net_income = info.get("netIncomeToCommon")
    
    if fcf is not None and fcf < 0:
        flags.append(("Cash Burn (Neg FCF)", fmt_num(fcf)))
    # 👇 INDIA OVERRIDE: If FCF is missing, check Operating Cash Flow
    elif fcf is None and ocf is not None and ocf < 0:
        flags.append(("Cash Burn (Neg OCF)", fmt_num(ocf)))
        
    if fcf is not None and net_income is not None and net_income > 0 and fcf < 0:
        flags.append(("Poor Earnings Quality", "Profit > 0, but FCF < 0"))

    # --- 6. Valuation & Bubble Risk ---
    if info.get("pegRatio") is not None and info.get("pegRatio") > 2.5:
        flags.append(("Overvalued (PEG > 2.5)", fmt_rat(info.get("pegRatio"))))
    if info.get("trailingPE") is not None and info.get("trailingPE") > 60:
        flags.append(("Extreme Valuation (P/E)", f"{fmt_rat(info.get('trailingPE'))}x"))
    if info.get("priceToBook") is not None and info.get("priceToBook") > 10:
        flags.append(("High P/B Ratio", f"{fmt_rat(info.get('priceToBook'))}x"))

    # --- 7. Smart Money & Market Sentiment Risk ---
    if info.get("beta") is not None and info.get("beta") > 2.0:
        flags.append(("Extreme Volatility (Beta)", fmt_rat(info.get("beta"))))
    if info.get("heldPercentInstitutions") is not None and info.get("heldPercentInstitutions") < 0.05:
        flags.append(("Low Institutional Backing", f"{fmt_pct(info.get('heldPercentInstitutions'))}"))

    return flags

def get_ownership(info):
    try:
        # Check if info is actually a dictionary to prevent AttributeError
        if not isinstance(info, dict):
            return 0.0, 0.0, 1.0
            
        insiders = float(info.get('heldPercentInsiders', 0) or 0)
        institutions = float(info.get('heldPercentInstitutions', 0) or 0)
        public = max(0.0, 1.0 - insiders - institutions)
        return insiders, institutions, public
    except Exception as e:
        # If yfinance sends bad data, default to 100% public to prevent crashing
        return 0.0, 0.0, 1.0

def get_valuation(info):
    return {
        "Market Cap": fmt_num(info.get('marketCap')),
        "Enterprise Value (EV)": fmt_num(info.get('enterpriseValue')),
        "Trailing P/E": fmt_rat(info.get('trailingPE')),
        "Forward P/E": fmt_rat(info.get('forwardPE')),
        "PEG Ratio": fmt_rat(info.get('pegRatio')),
        "Price to Book (P/B)": fmt_rat(info.get('priceToBook')),
        "Price to Sales (P/S)": fmt_rat(info.get('priceToSalesTrailing12Months')),
        "EV / EBITDA": fmt_rat(info.get('enterpriseToEbitda'))
    }

def get_profitability(info):
    return {
        "Profit Margin": fmt_pct(info.get('profitMargins')),
        "Operating Margin": fmt_pct(info.get('operatingMargins')),
        "Return on Equity (ROE)": fmt_pct(info.get('returnOnEquity')),
        "Return on Assets (ROA)": fmt_pct(info.get('returnOnAssets')),
        "Gross Profit": fmt_num(info.get('grossProfits')),
        "EBITDA": fmt_num(info.get('ebitda')),
        "Net Income": fmt_num(info.get('netIncomeToCommon'))
    }

def get_financial_strength(info):
    return {
        "Total Cash": fmt_num(info.get('totalCash')),
        "Total Debt": fmt_num(info.get('totalDebt')),
        "Total Cash Per Share": fmt_rat(info.get('totalCashPerShare')),
        "Debt to Equity": fmt_rat(info.get('debtToEquity')),
        "Current Ratio": fmt_rat(info.get('currentRatio')),
        "Quick Ratio": fmt_rat(info.get('quickRatio')),
        "Book Value Per Share": fmt_rat(info.get('bookValue'))
    }

def get_growth(info):
    five_yr_div = info.get('fiveYearAvgDividendYield')
    five_yr_div_str = f"{five_yr_div}%" if five_yr_div else "N/A"
    
    return {
        "Revenue Growth (YoY)": fmt_pct(info.get('revenueGrowth')),
        "Earnings Growth (YoY)": fmt_pct(info.get('earningsGrowth')),
        "Trailing EPS": fmt_rat(info.get('trailingEps')),
        "Forward EPS": fmt_rat(info.get('forwardEps')),
        "Dividend Yield": fmt_pct(info.get('dividendYield')),
        "5-Year Avg Div Yield": five_yr_div_str,
        "Dividend Payout Ratio": fmt_pct(info.get('payoutRatio'))
    }

# ==========================================
# 5. TECHNICALS & QUANT AI
# ==========================================
def calculate_technicals(hist):
    hist['Daily_Return'] = hist['Close'].pct_change()
    hist['RSI'] = ta.momentum.RSIIndicator(close=hist['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=hist['Close'])
    hist['MACD'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(close=hist['Close'], window=20, window_dev=2)
    hist['BB_High_Ind'] = bb.bollinger_hband_indicator()
    hist['BB_Low_Ind'] = bb.bollinger_lband_indicator()
    
    # 👇 MATCH THE TRAINING DATA EXACTLY 👇
    sma_20 = ta.trend.sma_indicator(close=hist['Close'], window=20)
    hist['SMA_20_Pct'] = (hist['Close'] - sma_20) / sma_20
    
    sma_50 = ta.trend.sma_indicator(close=hist['Close'], window=50)
    hist['SMA_50_Pct'] = (hist['Close'] - sma_50) / sma_50
    return hist

def run_quant_models(latest_data):
    if not os.path.exists("bolt_quant_model_daily.pkl") or not os.path.exists("bolt_quant_model_weekly.pkl"):
        return "ERROR", "Models not found.", "ERROR", "Run train_model.py first."
    try:
        model_daily = joblib.load("bolt_quant_model_daily.pkl")
        model_weekly = joblib.load("bolt_quant_model_weekly.pkl")
        
        # 👇 FEED THE NEW FEATURES TO THE LIVE MODEL 👇
        X_live = [[
            latest_data['Daily_Return'], latest_data['RSI'], latest_data['MACD'], 
            latest_data['BB_High_Ind'], latest_data['BB_Low_Ind'], 
            latest_data['SMA_20_Pct'], latest_data['SMA_50_Pct']
        ]]
        
        # ... (keep your predict logic exactly the same) ...
        
        # Daily Predict
        p_day = model_daily.predict(X_live)[0]
        prob_day = model_daily.predict_proba(X_live)[0][p_day]
        sig_day = "BULLISH" if p_day == 1 else "BEARISH"
        str_day = f"{sig_day} ({(prob_day*100):.1f}% Prob)"
        
        # Weekly Predict
        p_week = model_weekly.predict(X_live)[0]
        prob_week = model_weekly.predict_proba(X_live)[0][p_week]
        sig_week = "BULLISH" if p_week == 1 else "BEARISH"
        str_week = f"{sig_week} ({(prob_week*100):.1f}% Prob)"
        
        return sig_day, str_day, sig_week, str_week
    except Exception as e:
        return "ERROR", "Model error.", "ERROR", "Model error."

# ==========================================
# GENERATIVE AI VERDICT
# ==========================================
import google.generativeai as genai

def generate_genai_verdict(info, trend, zone, rsi, macd, red_flags_text, str_day, str_week):
    try:
        # DO NOT re-configure the API key here
        model = genai.GenerativeModel("gemini-1.5-flash") # Use 1.5-flash
        # ... rest of your code
        model = genai.GenerativeModel("models/gemini-2.5-flash") # Or your chosen Gemini model
        
        ticker = info.get('symbol', 'the stock')
        name = info.get('longName', ticker)
        
        prompt = f"""
        You are an elite Wall Street quantitative analyst. Your job is to synthesize technical momentum, machine learning predictions, and fundamental risk into a final verdict for {name} ({ticker}).
        
        Here is the live data feed:
        - Long-Term Trend: {trend}
        - 52-Week Position: {zone}
        - RSI (14-Day Momentum): {rsi}
        - MACD: {macd}
        - Quant ML Prediction (Tomorrow): {str_day}
        - Quant ML Prediction (Next 5 Days): {str_week}
        - 🚨 Systemic Fundamental Red Flags: {red_flags_text}
        
        Write a concise, professional 3-part executive summary:
        
        **1. Momentum & ML Outlook:** Explain what the technicals (RSI/MACD) and the Machine Learning predictions are signaling.
        **2. Fundamental Risk Assessment:** Look at the Fundamental Red Flags. If it says "None", state that the balance sheet is clean. If there are red flags (like low liquidity, negative cash flow, or high debt), explicitly warn the user about what those specific risks mean for the company's survival.
        **3. Final AI Verdict:** Give a clear [BULLISH], [BEARISH], or [NEUTRAL / HOLD] verdict based on the combined data.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Analysis temporarily unavailable. Error: {e}"

import json
import os
def get_backtest_results():
    if os.path.exists("backtest_results.json"):
        with open("backtest_results.json", "r") as f:
            return json.load(f)
    return None

# ==========================================
# 6. MUTUAL FUND & INSTITUTIONAL HOLDINGS
# ==========================================
def get_institutional_holdings(ticker_input):
    try:
        stock = yf.Ticker(ticker_input)
        mf_df = stock.mutualfund_holders
        inst_df = stock.institutional_holders
        return mf_df, inst_df
    except Exception as e:
        return None, None
# 7. LIVE NEWS FEED (WITH RSS FALLBACK)
# ==========================================
import datetime
import urllib.request
import xml.etree.ElementTree as ET

@st.cache_data(ttl=900)
def get_stock_news(ticker_input):
    formatted_news = []
    
    # --- ATTEMPT 1: Try yfinance with our anti-bot session ---
    try:
        stock = yf.Ticker(ticker_input, session=session)
        raw_news = stock.news
        if raw_news:
            for item in raw_news:
                formatted_news.append({
                    "title": item.get("title", "No Title"),
                    "publisher": item.get("publisher", "Yahoo Finance"),
                    "link": item.get("link", "#"),
                    "timestamp": item.get("providerPublishTime", datetime.datetime.now().timestamp())
                })
    except Exception as e:
        pass # If Yahoo blocks the main feed, we stay quiet and fall back to RSS

    # --- ATTEMPT 2: The Bulletproof RSS Fallback ---
    if not formatted_news:
        try:
            # Build the direct Yahoo RSS URL
            base_ticker = ticker_input.split('.')[0] if '.' in ticker_input else ticker_input
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={base_ticker}&region=US&lang=en-US"
            
            # Mask as a standard web browser to prevent getting blocked
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
            
            for item in root.findall('./channel/item'):
                title = item.find('title').text if item.find('title') is not None else 'No Title'
                link = item.find('link').text if item.find('link') is not None else '#'
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                
                try:
                    pub_time = datetime.datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %z")
                except:
                    pub_time = datetime.datetime.now()
                    
                formatted_news.append({
                    "title": title,
                    "publisher": "Yahoo Finance (RSS)",
                    "link": link,
                    "time_obj": pub_time,
                    "time_str": pub_time.strftime("%b %d, %Y - %I:%M %p"),
                    "timestamp": pub_time.timestamp()
                })
        except Exception as e:
            return [] # If both methods fail, return an empty list safely so the app doesn't crash

    # Finally, sort from Newest to Oldest
    formatted_news = sorted(formatted_news, key=lambda x: x.get('timestamp', 0), reverse=True)
    return formatted_news
# ==========================================
# 8. AI NEWS SENTIMENT ANALYSIS
# ==========================================
def analyze_news_sentiment(news_list, ticker):
    if not news_list:
        return "No news available to analyze."
    
    # Grab the top 10 headlines to feed to the AI
    headlines = "\n".join([f"- {article['title']}" for article in news_list[:10]])
    
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    prompt = f"""
    You are an expert Wall Street financial analyst. Review these recent news headlines for the stock {ticker}:
    
    {headlines}
    
    Provide a highly concise, punchy analysis in exactly this format:
    
    **Overall Sentiment:** [Bullish 🟢 / Bearish 🔴 / Neutral ⚪]
    **The Core Story:** [1-2 sentences summarizing the main narrative driving this stock right now based on the headlines]
    **Noise Filter:** [Point out 1 or 2 headlines that are just macro-economic noise or irrelevant to {ticker}'s core business]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Analysis temporarily unavailable. Error: {e}"

# ==========================================
# 9. ADVANCED CUSTOM METRICS & MULTI-STAGE DCF INPUTS
# ==========================================
def get_advanced_metrics(ticker_input, info):
    """Pulls raw accounting statements ONCE and calculates all custom quant metrics."""
    try:
        stock = yf.Ticker(ticker_input)
        bs = stock.balance_sheet
        inc = stock.financials
        cf = stock.cashflow # 👈 Fetching Cash Flow here!

        if bs.empty or inc.empty or cf.empty:
            return None
            
        recent_bs = bs.iloc[:, 0]
        recent_inc = inc.iloc[:, 0]
        recent_cf = cf.iloc[:, 0]
        
        def safe_extract(series, possible_keys, default=0.0):
            if series is None or series.empty: return default
            for key in possible_keys:
                if key in series.index and not pd.isna(series[key]):
                    return float(series[key])
            return default

        # --- RAW DATA EXTRACTION ---
        # Income Statement
        net_income = safe_extract(recent_inc, ['Net Income', 'Net Income Common Stockholders'])
        revenue = safe_extract(recent_inc, ['Total Revenue', 'Operating Revenue'])
        ebit = safe_extract(recent_inc, ['EBIT', 'Operating Income', 'Pretax Income'])
        tax_provision = safe_extract(recent_inc, ['Tax Provision', 'Income Tax Expense'])
        pretax_income = safe_extract(recent_inc, ['Pretax Income', 'Income Before Tax'])
        
        # Cash Flow
        capex = abs(safe_extract(recent_cf, ['Capital Expenditure', 'Payments For Property Plant And Equipment']))
        depreciation = safe_extract(recent_cf, ['Depreciation And Amortization', 'Depreciation'])
        chg_wc = safe_extract(recent_cf, ['Change In Working Capital'])

        # Balance Sheet
        total_assets = safe_extract(recent_bs, ['Total Assets'])
        total_equity = safe_extract(recent_bs, ['Stockholders Equity', 'Total Stockholder Equity', 'Total Equity Gross Minority Interest'])
        total_liab = safe_extract(recent_bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        current_assets = safe_extract(recent_bs, ['Current Assets'])
        current_liab = safe_extract(recent_bs, ['Current Liabilities'])
        retained_earnings = safe_extract(recent_bs, ['Retained Earnings'])
        total_debt_bs = safe_extract(recent_bs, ['Total Debt', 'Long Term Debt'])
        cash = safe_extract(recent_bs, ['Cash And Cash Equivalents', 'Cash', 'Total Cash'])
        minority_int = safe_extract(recent_bs, ['Minority Interest'])
        
        if total_debt_bs == 0: 
            total_debt_bs = info.get('totalDebt', 0.0)
            
        market_cap = info.get('marketCap', 0.0)

        # --- 1. DAMODARAN DCF INPUTS ---
        tax_rate = (tax_provision / pretax_income) if pretax_income > 0 else 0.25
        tax_rate = max(0.0, min(tax_rate, 0.40)) # Cap tax rate for sanity
        ebit_after_tax = ebit * (1 - tax_rate)

        reinvestment = capex - depreciation + chg_wc
        reinvestment_rate = reinvestment / ebit_after_tax if ebit_after_tax > 0 else 0
        reinvestment_rate = max(0.0, min(reinvestment_rate, 1.0))

        invested_capital = total_debt_bs + total_equity - cash
        roc = ebit_after_tax / invested_capital if invested_capital > 0 else 0
        roc = max(0.01, min(roc, 0.50))
        expected_growth = roc * reinvestment_rate

        beta = info.get('beta', 1.0) or 1.0
        rf_rate = 0.065 if "NS" in ticker_input or "BO" in ticker_input else 0.04
        erp = 0.055
        cost_of_equity = rf_rate + (beta * erp)
        
        cost_of_debt = 0.08
        cost_of_debt_after_tax = cost_of_debt * (1 - tax_rate)
        
        total_capital = market_cap + total_debt_bs
        weight_e = market_cap / total_capital if total_capital > 0 else 0.8
        weight_d = total_debt_bs / total_capital if total_capital > 0 else 0.2
        wacc = (weight_e * cost_of_equity) + (weight_d * cost_of_debt_after_tax)
        
        shares = info.get('sharesOutstanding', 1)

        dcf_inputs = {
            "success": True if ebit > 0 else False,
            "ebit": ebit, "tax_rate": tax_rate, "ebit_after_tax": ebit_after_tax,
            "reinvestment_rate": reinvestment_rate, "roc": roc, "expected_growth": expected_growth,
            "wacc": wacc, "shares": shares, "total_debt": total_debt_bs, "cash": cash,
            "minority_int": minority_int, "rf_rate": rf_rate, "currency": info.get("currency", "INR")
        }

        # --- 2. DUPONT ANALYSIS ---
        net_profit_margin = (net_income / revenue) if revenue else 0
        asset_turnover = (revenue / total_assets) if total_assets else 0
        equity_multiplier = (total_assets / total_equity) if total_equity else 0
        dupont_roe = net_profit_margin * asset_turnover * equity_multiplier

        # --- 3. ALTMAN Z-SCORE ---
        working_capital = current_assets - current_liab
        A = working_capital / total_assets if total_assets else 0
        B = retained_earnings / total_assets if total_assets else 0
        C = ebit / total_assets if total_assets else 0
        D = market_cap / total_liab if total_liab else 0
        E = revenue / total_assets if total_assets else 0
        
        z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
        
        if z_score > 2.99: z_zone = "Safe Zone 🟢"
        elif z_score > 1.81: z_zone = "Grey Zone 🟡"
        else: z_zone = "Distress Zone 🔴"

        # --- 4. LEVERED VS UNLEVERED BETA ---
        d_e_ratio = (total_debt_bs / market_cap) if market_cap else 0.0
        unlevered_beta = beta / (1 + ((1 - tax_rate) * d_e_ratio)) if beta else 0.0

        # --- 5. THE MASTER PAYLOAD ---
        return {
            "dupont": {"roe": dupont_roe, "net_margin": net_profit_margin, "asset_turnover": asset_turnover, "equity_multiplier": equity_multiplier},
            "altman": {"score": z_score, "zone": z_zone},
            "beta": {"levered": beta, "unlevered": unlevered_beta, "tax_rate": tax_rate, "d_e_ratio": d_e_ratio},
            "dcf_inputs": dcf_inputs,  # The new data for the Valuation Tab
            "raw_data": {"income_statement": recent_inc, "balance_sheet": recent_bs, "cash_flow": recent_cf} # Notice cf is included now!
        }
    except Exception as e:
        return None

# ==========================================
# 10. PDF REPORT GENERATOR
# ==========================================
def generate_financials_pdf(ticker_input, info):
    """Generates a downloadable PDF of the raw financial statements."""
    try:
        stock = yf.Ticker(ticker_input)
        
        # 👇 Grab ALL THREE statements now
        inc = stock.financials
        bs = stock.balance_sheet
        cf = stock.cashflow 
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        
        company_name = info.get('longName', ticker_input)
        clean_name = company_name.encode('ascii', 'ignore').decode('ascii')
        
        pdf.cell(200, 10, txt=f"Financial Statements: {clean_name} ({ticker_input})", ln=True, align='C')
        pdf.ln(5)
        
        def add_table_to_pdf(df, title):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt=title, ln=True)
            pdf.set_font("Arial", size=9)
            
            if df is None or df.empty:
                pdf.cell(200, 10, txt="Data not available.", ln=True)
                pdf.ln(5)
                return
            
            latest_col = df.columns[0]
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(110, 8, txt="Accounting Line Item", border=1)
            pdf.cell(70, 8, txt=str(latest_col)[:10], border=1, ln=True, align='R')
            
            pdf.set_font("Arial", size=9)
            for index, row in df.head(30).iterrows():
                val = row[latest_col]
                val_str = f"{val:,.0f}" if not pd.isna(val) else "-"
                clean_idx = str(index).encode('ascii', 'ignore').decode('ascii')[:45]
                
                pdf.cell(110, 8, txt=clean_idx, border=1)
                pdf.cell(70, 8, txt=val_str, border=1, ln=True, align='R')
            pdf.ln(5)

        # 👇 Print all three tables to the PDF
        add_table_to_pdf(inc, "Income Statement (Latest Year)")
        add_table_to_pdf(bs, "Balance Sheet (Latest Year)")
        add_table_to_pdf(cf, "Cash Flow Statement (Latest Year)") 
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return None

# ==========================================
# 11. SMART TICKER SEARCH (MARKET AWARE)
# ==========================================
import urllib.parse
import json
import urllib.request

def resolve_ticker(query, market):
    """Converts a company name or ticker into the correct symbol for the chosen market."""
    query = query.strip().upper()
    
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=10&newsCount=0"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        quotes = data.get('quotes', [])
        
        # Filter results based on the Dropdown Market selection
        if market == "India (NSE)":
            for q in quotes:
                if q.get('symbol', '').endswith('.NS'): 
                    return q['symbol']
            # Fallback if search fails but they typed a valid ticker
            return f"{query}.NS" if not query.endswith(".NS") else query
            
        elif market == "India (BSE)":
            for q in quotes:
                if q.get('symbol', '').endswith('.BO'): 
                    return q['symbol']
            return f"{query}.BO" if not query.endswith(".BO") else query
            
        else: # US Market (NASDAQ/NYSE)
            for q in quotes:
                # US stocks typically don't have a dot suffix in Yahoo Finance
                if "." not in q.get('symbol', ''): 
                    return q['symbol']
            return quotes[0]['symbol'] if quotes else query
            
    except Exception as e:
        # Failsafe if the API is down
        if market == "India (NSE)" and not query.endswith(".NS"): return f"{query}.NS"
        if market == "India (BSE)" and not query.endswith(".BO"): return f"{query}.BO"
        return query

# ==========================================
# 10. STATISTICAL REGRESSION & CAPM
# ==========================================
def calculate_beta_regression(ticker_input, market):
    """Runs a 5-year monthly linear regression against a market benchmark."""
    try:
        # 1. Determine benchmark and macroeconomic rates based on market
        if "India" in market:
            benchmark_ticker = "^NSEI" # Nifty 50
            rf_rate = 0.07 # 7.0% Assumed Indian 10Y Gov Bond Yield
            market_premium = 0.06 # 6.0% Assumed Equity Risk Premium
        else:
            benchmark_ticker = "^GSPC" # S&P 500
            rf_rate = 0.042 # 4.2% Assumed US 10Y Treasury Yield
            market_premium = 0.055 # 5.5% Assumed US Equity Risk Premium

        # 2. Fetch 5 years of monthly close data
        stock = yf.Ticker(ticker_input)
        bench = yf.Ticker(benchmark_ticker)
        
        s_hist = stock.history(period="5y", interval="1mo")['Close'].dropna()
        b_hist = bench.history(period="5y", interval="1mo")['Close'].dropna()
        
        # 3. Align dates and calculate percentage returns
        df = pd.DataFrame({'Stock': s_hist, 'Market': b_hist}).dropna()
        returns = df.pct_change().dropna()
        
        if returns.empty: 
            return None
        
        x = returns['Market']
        y = returns['Stock']
        
        # 4. Run the Linear Regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        beta = slope
        r_squared = r_value ** 2
        
        # 5. Jensen's Alpha (Annualized for display)
        # Formula: Intercept - (Rf/12) * (1 - Beta)
        rf_monthly = rf_rate / 12
        jensens_alpha_monthly = intercept - (rf_monthly * (1 - beta))
        jensens_alpha_ann = jensens_alpha_monthly * 12
        
        # 6. CAPM Required Return
        required_return = rf_rate + (beta * market_premium)
        
        return {
            "beta": beta,
            "intercept": intercept,
            "r_squared": r_squared,
            "std_err": std_err,
            "jensens_alpha_ann": jensens_alpha_ann,
            "required_return": required_return,
            "rf_rate": rf_rate,
            "market_premium": market_premium,
            "benchmark": benchmark_ticker
        }
    except Exception as e:
        return None

# ==========================================
# 12. MULTI-SOURCE NEWS & CONSENSUS AI
# ==========================================

def get_gnews_feed(ticker_input):
    """Source: GNews API"""
    try:
        api_key = st.secrets.get("GNEWS_API_KEY")
        if not api_key: return []
        query = ticker_input.split('.')[0]
        url = f"https://gnews.io/api/v4/search?q={query}&token={api_key}&lang=en&max=5"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            return [{"title": a['title'], "source": a['source']['name'], "link": a['url'], "date": a['publishedAt'][:10]} for a in articles]
    except Exception: return []
    return []

def get_newsdata_feed(ticker_input):
    """Source: NewsData.io (Broad Search to guarantee results)"""
    try:
        api_key = st.secrets.get("NEWSDATA_API_KEY")
        if not api_key: 
            return []
            
        # Clean the ticker (e.g., AAPL.NS -> AAPL)
        query = ticker_input.split('.')[0]
        
        # Use the standard /news endpoint, which is fully supported on the Free tier
        url = "https://newsdata.io/api/1/news"
        
        # Using a params dictionary safely encodes the URL to prevent 0-result glitches
        params = {
            "apikey": api_key,
            "q": query,       # Broad keyword search
            "language": "en"
        }
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            return [{"title": r.get('title', 'No Title'), "source": r.get('source_id', 'NewsData').upper(), "link": r.get('link', '#'), "date": r.get('pubDate', '')[:10]} for r in results[:5]]
        else:
            # Prints to the app if you run out of credits or get blocked
            st.error(f"NewsData Error: {response.text}")
            return []
            
    except Exception as e: 
        return []

def get_stockdata_feed(ticker_input):
    """Source: StockData.org"""
    try:
        api_key = st.secrets.get("STOCKDATA_API_KEY")
        if not api_key: 
            return []
            
        # Strip the .NS or .BO suffix so the API understands it
        query = ticker_input.split('.')[0] 
        url = f"https://api.stockdata.org/v1/news/all?symbols={query}&filter_entities=true&language=en&api_token={api_key}"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            articles = response.json().get('data', [])
            return [{"title": a.get('title', 'No Title'), "source": a.get('source', 'StockData').upper(), "link": a.get('url', '#'), "date": a.get('published_at', '')[:10]} for a in articles[:5]]
            
        return [] # Fallback if the API returns a non-200 status code
        
    except Exception as e:
        st.error(f"StockData Error: {e}") 
        return []

import google.generativeai as genai
import streamlit as st

def get_ai_model():
    """Helper to ensure we always use the working connection."""
    # This matches exactly how your working Hybrid Verdict works
    return genai.GenerativeModel("gemini-1.5-flash")

# ==========================================
# NEW AI SENTIMENT FUNCTIONS (FIXED)
# ==========================================

def analyze_specific_news_sentiment(news_list, ticker, source_name):
    """Analyzes a single news source using the working 2.5-flash model."""
    if not news_list:
        return f"No news available from {source_name}."
    
    headlines = "\n".join([f"- {article['title']}" for article in news_list[:5]])
    
    # 👇 Match the exact working model string 👇
    model = genai.GenerativeModel("models/gemini-2.5-flash") 
    
    prompt = f"Analyze these {source_name} headlines for {ticker}. Provide: 1. Sentiment (Bullish/Bearish/Neutral) 2. A 2-sentence summary."
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"


def analyze_consensus_sentiment(all_news_payload, ticker):
    """Master Consensus AI using the working 2.5-flash model."""
    context = ""
    for src, arts in all_news_payload.items():
        context += f"\n--- {src} ---\n"
        if not arts:
            context += "No data.\n"
        else:
            for a in arts[:3]:
                context += f"- {a['title']}\n"
    
    # 👇 Match the exact working model string 👇
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    
    prompt = f"""
    Review these news sources for {ticker}:
    {context}
    
    Provide a 'Consensus Report':
    1. Information Asymmetry: Did regional sources catch news global sources missed?
    2. Master Narrative: Summarize the combined truth.
    3. Consensus Sentiment: [Bullish / Bearish / Neutral]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"
        
import requests
import numpy as np
from datetime import timedelta
import pandas as pd
import yfinance as yf
import streamlit as st
import time

import time

# ==========================================
# 13. MUTUAL FUND ENGINE (MFAPI.in)
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def get_mf_list():
    """Enterprise-grade fetcher with Retries and Bot-Bypass."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    url = "https://api.mfapi.in/mf"
    
    # Industry Standard: 3-Attempt Retry Loop
    for attempt in range(3): 
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    return data # Success! Return the 45,000 funds.
        except Exception as e:
            time.sleep(2) # Wait 2 seconds and try again if the connection drops
            continue
            
    # If all 3 attempts fail, return empty
    return []

@st.cache_data(ttl=86400, show_spinner=False)
def get_premium_mf_data(fund_name):
    """
    ENTERPRISE WATERFALL PIPELINE
    Tier 1: Groww Institutional API (Primary)
    Tier 2: Direct Google Web Scrape via BeautifulSoup (Fallback)
    """
    import requests
    import re
    import urllib.parse
    from bs4 import BeautifulSoup
    
    premium_data = {
        "AUM": "Data Unavailable",
        "Expense Ratio": "Data Unavailable",
        "Exit Load": "Data Unavailable",
        "Min. Investment": "Data Unavailable"
    }
    
    # --- SENIOR DEV TRICK: AGGRESSIVE NAME CLEANING ---
    # We slice the name to ONLY the first 4 words. 
    # "JM Large Cap Fund (Regular)" -> "JM Large Cap Fund"
    words = re.sub(r'\(.*?\)', '', fund_name).replace('-', ' ').split()
    short_name = " ".join(words[:4])
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    # ==========================================
    # TIER 1: THE GROWW API
    # ==========================================
    try:
        safe_query = urllib.parse.quote(short_name)
        search_url = f"https://groww.in/v1/api/search/v1/derived/scheme?available_for_investment=true&query={safe_query}&size=1"
        search_res = requests.get(search_url, headers=headers, timeout=5).json()
        
        if search_res.get('content'):
            search_id = search_res['content'][0].get('search_id')
            detail_url = f"https://groww.in/v1/api/data/mf/web/v3/scheme/search/{search_id}"
            detail_res = requests.get(detail_url, headers=headers, timeout=5).json()
            
            aum = detail_res.get('aum')
            er = detail_res.get('expense_ratio')
            el = detail_res.get('exit_load')
            sip = detail_res.get('min_sip_investment')
            
            # If we successfully got the data, return it instantly!
            if aum and er:
                premium_data["AUM"] = f"₹ {aum:,.2f} Cr"
                premium_data["Expense Ratio"] = f"{er}%"
                premium_data["Exit Load"] = str(el) if el else "Nil"
                premium_data["Min. Investment"] = f"₹ {sip} (SIP)" if sip else "₹ 500"
                return premium_data
    except Exception:
        pass # If Groww fails, we silently slide down to Tier 2

    # ==========================================
    # TIER 2: DIRECT GOOGLE SCRAPE
    # ==========================================
    try:
        google_query = urllib.parse.quote(f"{short_name} mutual fund AUM Expense Ratio moneycontrol")
        google_url = f"https://www.google.com/search?q={google_query}"
        
        # We disguise ourselves specifically to bypass Google's bot detection
        google_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        resp = requests.get(google_url, headers=google_headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        web_text = soup.get_text().lower()
        
        # Extract AUM using Regex
        aum_match = re.search(r'(?:aum|size|assets).*?(?:rs\.?|₹|inr|rupees)?\s*([\d,.]+)\s*(?:cr|crore|cror)', web_text)
        if aum_match and premium_data["AUM"] == "Data Unavailable":
            premium_data["AUM"] = f"₹ {aum_match.group(1)} Cr"
            
        # Extract Expense Ratio using Regex
        er_match = re.search(r'expense ratio.*?([\d.]+)\s*%', web_text)
        if er_match and premium_data["Expense Ratio"] == "Data Unavailable":
            premium_data["Expense Ratio"] = f"{er_match.group(1)}%"
            
        return premium_data
        
    except Exception as e:
        # If both fail, we return the honest "Data Unavailable" to maintain integrity.
        return premium_data

def get_mf_and_benchmark(scheme_code, benchmark_ticker="^NSEI"):
    """Fetches historical NAV and perfect-matches it with the NIFTY 50"""
    try:
        # 1. Fetch entire history from free API
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, None, "API Connection Failed"
            
        data = response.json()
        
        # 2. Convert to DataFrame
        df_mf = pd.DataFrame(data['data'])
        df_mf['date'] = pd.to_datetime(df_mf['date'], format='%d-%m-%Y')
        df_mf['nav'] = pd.to_numeric(df_mf['nav'], errors='coerce')
        df_mf.set_index('date', inplace=True)
        df_mf.sort_index(ascending=True, inplace=True)
        
        # 3. Get Benchmark Data (NIFTY 50)
        inception_date = df_mf.index.min()
        latest_date = df_mf.index.max()
        df_bench = yf.Ticker(benchmark_ticker).history(start=inception_date, end=latest_date + timedelta(days=1))
        
        if df_bench.index.tz is not None:
            df_bench.index = df_bench.index.tz_localize(None)
            
        # 4. Merge perfectly
        merged_df = pd.merge(df_mf[['nav']], df_bench[['Close']], left_index=True, right_index=True, how='inner')
        merged_df.columns = ['MF_NAV', 'Benchmark_Close']
        merged_df = merged_df.dropna()
        
        # 5. Fetch premium info & package meta data
        premium_info = get_premium_mf_data(data['meta'].get('scheme_name', ''))

        meta_dict = {
            "Fund Name": data['meta'].get('scheme_name', 'Unknown'),
            "Fund House (AMC)": data['meta'].get('fund_house', 'Unknown'),
            "Category": data['meta'].get('scheme_category', 'Unknown'),
            "Benchmark Index": "NIFTY 50 (^NSEI)",
            "Launch Date": inception_date.strftime('%d %b %Y'),
            "AUM": premium_info["AUM"],
            "Expense Ratio": premium_info["Expense Ratio"],
            "Exit Load": premium_info["Exit Load"],
            "Min. Investment": premium_info["Min. Investment"]
        }
        
        return merged_df, meta_dict, "Success"
    except Exception as e:
        return None, None, f"Error: {str(e)}"

def calculate_mf_metrics(merged_df, risk_free_rate=0.07):
    """Calculates Advanced Institutional Quantitative Metrics for Mutual Funds"""
    returns = merged_df.pct_change().dropna()
    fund_returns = returns['MF_NAV']
    bench_returns = returns['Benchmark_Close']
    
    years = len(merged_df) / 252 
    
    # 1. CAGR
    if years > 0:
        fund_cagr = (merged_df['MF_NAV'].iloc[-1] / merged_df['MF_NAV'].iloc[0]) ** (1/years) - 1
        bench_cagr = (merged_df['Benchmark_Close'].iloc[-1] / merged_df['Benchmark_Close'].iloc[0]) ** (1/years) - 1
    else:
        fund_cagr, bench_cagr = 0, 0
        
    # 2. Risk Metrics (Volatility, Beta, Alpha, Sharpe)
    fund_volatility = fund_returns.std() * np.sqrt(252)
    bench_volatility = bench_returns.std() * np.sqrt(252)
    
    cov_matrix = np.cov(fund_returns, bench_returns)
    beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1
    alpha = fund_cagr - (risk_free_rate + beta * (bench_cagr - risk_free_rate))
    sharpe = (fund_cagr - risk_free_rate) / fund_volatility if fund_volatility != 0 else 0
    
    # 3. ADVANCED: Sortino Ratio (Downside Risk Only)
    downside_returns = fund_returns[fund_returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (fund_cagr - risk_free_rate) / downside_std if downside_std != 0 else 0
    
    # 4. ADVANCED: Maximum Drawdown (Worst crash from peak)
    cum_returns = (1 + fund_returns).cumprod()
    rolling_max = cum_returns.cummax()
    drawdown = (cum_returns - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    bench_cum = (1 + bench_returns).cumprod()
    bench_rolling_max = bench_cum.cummax()
    bench_drawdown = (bench_cum - bench_rolling_max) / bench_rolling_max
    bench_max_drawdown = bench_drawdown.min()
    
    # 5. ADVANCED: Capture Ratios (How it performs in Bull vs Bear markets)
    up_days = bench_returns > 0
    down_days = bench_returns < 0
    
    fund_up_return = fund_returns[up_days].mean()
    bench_up_return = bench_returns[up_days].mean()
    up_capture = (fund_up_return / bench_up_return * 100) if bench_up_return != 0 else 100
    
    fund_down_return = fund_returns[down_days].mean()
    bench_down_return = bench_returns[down_days].mean()
    down_capture = (fund_down_return / bench_down_return * 100) if bench_down_return != 0 else 100

    # 6. Trailing Returns (Historical lookup)
    def get_trailing(days):
        if len(merged_df) > days:
            return (merged_df['MF_NAV'].iloc[-1] / merged_df['MF_NAV'].iloc[-days]) - 1
        return None
        
    trailing = {
        "1M": get_trailing(21),
        "6M": get_trailing(126),
        "1Y": get_trailing(252),
        "3Y": get_trailing(756),
        "5Y": get_trailing(1260)
    }

    # 7. THE SECRET SAUCE: RayTurnz Proprietary Score (Out of 10)
    score = 5.0 # Everyone starts at average
    
    # Alpha (+ up to 2.5 points)
    if alpha > 0.05: score += 2.5
    elif alpha > 0.02: score += 1.0
    elif alpha < -0.02: score -= 1.0
    
    # Sharpe/Sortino (+ up to 2 points)
    if sharpe > 1.2: score += 2.0
    elif sharpe > 0.8: score += 1.0
    elif sharpe < 0.5: score -= 1.0
    
    # Max Drawdown vs Benchmark (+ up to 1.5 points)
    dd_diff = max_drawdown - bench_max_drawdown # Positive means fund dropped LESS than market
    if dd_diff > 0.05: score += 1.5
    elif dd_diff > 0: score += 0.5
    elif dd_diff < -0.05: score -= 1.0
    
    # Capture Ratios (+ up to 2 points)
    if up_capture > 100 and down_capture < 100: score += 2.0
    elif up_capture > down_capture: score += 1.0
    elif down_capture > 110: score -= 1.0
    
    final_score = max(1.0, min(10.0, score)) # Cap between 1 and 10
    
    return {
        "CAGR": fund_cagr,
        "Benchmark CAGR": bench_cagr,
        "Beta": beta,
        "Alpha": alpha,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Volatility (Std Dev)": fund_volatility,
        "Max Drawdown": max_drawdown,
        "Up Capture": up_capture,
        "Down Capture": down_capture,
        "Trailing Returns": trailing,
        "Years of Data": years,
        "RayTurnz Score": final_score
    }

# ==========================================
# 13. MUTUAL FUND AI VERDICT
# ==========================================
import google.generativeai as genai

def generate_mf_verdict(all_metrics, all_meta):
    """
    Dynamic AI Wealth Manager:
    - If 1 fund: Reviews, suggests buy/hold, and lists better alternatives.
    - If 2-5 funds: Compares and picks the absolute winner.
    """
    if not all_metrics:
        return "No data available to analyze."

    try:
        # 1. Build the Data Context for the AI
        context = "Here is the quantitative data for the selected mutual fund(s):\n\n"
        for name, metrics in all_metrics.items():
            # Grab the category so Gemini knows what alternatives to suggest
            category = all_meta[name].get("Category", "Unknown Category")
            
            context += f"**{name}** (Category: {category})\n"
            context += f"- CAGR (Return): {metrics['CAGR']*100:.2f}%\n"
            context += f"- NIFTY 50 Benchmark CAGR: {metrics['Benchmark CAGR']*100:.2f}%\n"
            context += f"- Jensen's Alpha (Outperformance): {metrics['Alpha']*100:.2f}%\n"
            context += f"- Market Beta (Risk): {metrics['Beta']:.2f}\n"
            context += f"- Sharpe Ratio (Efficiency): {metrics['Sharpe Ratio']:.2f}\n"
            context += f"- Years Analyzed: {metrics['Years of Data']:.1f}\n\n"

        # Use the fast, reliable model
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # 2. DYNAMIC PROMPT ROUTING
        if len(all_metrics) == 1:
            # --- SCENARIO A: SINGLE FUND AUDIT ---
            prompt = f"""
            You are an elite Wall Street Wealth Manager. I am analyzing a SINGLE Indian mutual fund right now. 
            Data:
            {context}

            Please provide a structured 3-part review:
            1. **Performance Audit:** Analyze its Alpha (outperformance) and Sharpe Ratio. Is it actually beating the market efficiently?
            2. **Investment Verdict:** Should the user [INVEST], [HOLD], or [AVOID] it? Justify with the math.
            3. **Better Alternatives:** Based on its specific category, suggest 1 or 2 specific, well-known Indian mutual funds that are historically stronger alternatives to consider.
            Keep it highly professional, concise, and structured with bullet points.
            """
        else:
            # --- SCENARIO B: MULTI-FUND COMPARISON ---
            prompt = f"""
            You are an elite Wall Street Wealth Manager. I am comparing {len(all_metrics)} Indian mutual funds.
            Data:
            {context}

            Please provide a structured 3-part comparison verdict:
            1. **The Winner 🏆:** Explicitly name the absolute BEST fund out of the group.
            2. **Why It Won:** Justify your choice by comparing its Alpha, Sharpe Ratio, and CAGR against the losers.
            3. **Risk Warning:** Briefly mention if the winner takes on significantly more risk (Beta) to achieve those returns.
            Keep it highly professional, punchy, and structured. Speak directly to the investor.
            """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Advisor temporarily unavailable. Error: {e}"

# ==========================================
# 14. QUICK INTRINSIC VALUATION (For Fundamentals Tab)
# ==========================================
def calculate_intrinsic_value(info, current_price):
    """
    Calculates a quick Single-Stage DCF for the snapshot card.
    """
    try:
        fcf = info.get("freeCashflow")
        if fcf is None:
            ocf = info.get("operatingCashflow")
            if ocf is None or ocf <= 0:
                return "N/A", "Negative/Missing Cashflow", "gray"
            fcf = ocf 
            
        if fcf <= 0:
            return "N/A", "Negative Cashflow", "gray"

        cash = info.get("totalCash", 0) or 0
        debt = info.get("totalDebt", 0) or 0
        shares = info.get("sharesOutstanding")
        
        if not shares or shares == 0:
            return "N/A", "Missing Share Count", "gray"

        beta = info.get("beta", 1.0) or 1.0
        wacc = max(0.08, min(0.065 + (beta * (0.12 - 0.065)), 0.16))
        g = 0.03 
        
        if wacc <= g:
            wacc = g + 0.02

        terminal_value = (fcf * (1 + g)) / (wacc - g)
        equity_value = terminal_value + cash - debt
        
        if equity_value <= 0:
            return "N/A", "Debt Exceeds Value", "gray"
            
        intrinsic_value = equity_value / shares

        if current_price and current_price > 0:
            upside = ((intrinsic_value - current_price) / current_price) * 100
            
            if upside > 0:
                delta_str = f"Undervalued by {upside:.1f}%"
            else:
                delta_str = f"Overvalued by {abs(upside):.1f}%"
                
            currency = "₹" if "NS" in info.get("symbol", "") or "BO" in info.get("symbol", "") else "$"
            return f"{currency}{intrinsic_value:.2f}", delta_str, "gray"
            
        return f"{intrinsic_value:.2f}", "Fair Value Calculation", "gray"

    except Exception as e:
        return "Error", "Calculation Failed", "gray"