import yfinance as yf
import pandas as pd
import ta
import joblib
import os
import google.generativeai as genai
from fpdf import FPDF
from scipy import stats

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
def get_red_flags(info):
    """Conducts a comprehensive institutional 10-point risk scan."""
    flags = []
    
    # 1. Profitability & Returns Risk
    if info.get("profitMargins") is not None and info.get("profitMargins") < 0:
        flags.append(("Negative Profit Margin", fmt_pct(info.get("profitMargins"))))
    if info.get("operatingMargins") is not None and info.get("operatingMargins") < 0:
        flags.append(("Negative Op Margin", fmt_pct(info.get("operatingMargins"))))
    if info.get("returnOnEquity") is not None and info.get("returnOnEquity") < 0:
        flags.append(("Negative ROE", fmt_pct(info.get("returnOnEquity"))))
        
    # 2. Growth Trajectory Risk
    if info.get("revenueGrowth") is not None and info.get("revenueGrowth") < 0:
        flags.append(("Declining Revenue", fmt_pct(info.get("revenueGrowth"))))
    if info.get("earningsGrowth") is not None and info.get("earningsGrowth") < 0:
        flags.append(("Declining Earnings", fmt_pct(info.get("earningsGrowth"))))
        
    # 3. Liquidity Risk (Short-term survival)
    if info.get("currentRatio") is not None and info.get("currentRatio") < 1.0:
        flags.append(("Low Liquidity (CR < 1)", fmt_rat(info.get("currentRatio"))))
    if info.get("quickRatio") is not None and info.get("quickRatio") < 0.8:
        flags.append(("Poor Quick Ratio", fmt_rat(info.get("quickRatio"))))
        
    # 4. Solvency Risk (Long-term survival)
    if info.get("debtToEquity") is not None and info.get("debtToEquity") > 150:
        flags.append(("High Debt/Equity", f"{info.get('debtToEquity'):.1f}%"))
        
    # 5. Cash Flow & Valuation Risk
    if info.get("freeCashflow") is not None and info.get("freeCashflow") < 0:
        flags.append(("Cash Burn (Neg FCF)", fmt_num(info.get("freeCashflow"))))
    if info.get("pegRatio") is not None and info.get("pegRatio") > 2.5:
        flags.append(("Overvalued (PEG > 2.5)", fmt_rat(info.get("pegRatio"))))
        
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
    hist['SMA_20'] = ta.trend.sma_indicator(close=hist['Close'], window=20)
    hist['SMA_50'] = ta.trend.sma_indicator(close=hist['Close'], window=50)
    return hist

def run_quant_models(latest_data):
    if not os.path.exists("bolt_quant_model_daily.pkl") or not os.path.exists("bolt_quant_model_weekly.pkl"):
        return "ERROR", "Models not found.", "ERROR", "Run train_model.py first."
    try:
        model_daily = joblib.load("bolt_quant_model_daily.pkl")
        model_weekly = joblib.load("bolt_quant_model_weekly.pkl")
        
        X_live = [[
            latest_data['Daily_Return'], latest_data['RSI'], latest_data['MACD'], 
            latest_data['BB_High_Ind'], latest_data['BB_Low_Ind'], 
            latest_data['SMA_20'], latest_data['SMA_50']
        ]]
        
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
    """Feeds technicals, ML predictions, and fundamental red flags into Gemini."""
    try:
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
# ==========================================
# 7. LIVE NEWS FEED (WITH RSS FALLBACK)
# ==========================================
import datetime
import urllib.request
import xml.etree.ElementTree as ET

def get_stock_news(ticker_input):
    """Fetches news via yfinance, with a bulletproof direct RSS fallback if the API fails."""
    formatted_news = []
    
    # --- ATTEMPT 1: Standard yfinance ---
    try:
        stock = yf.Ticker(ticker_input)
        news_data = stock.news
        
        if news_data:
            for article in news_data:
                title = article.get('title', '')
                link = article.get('link', '')
                
                if not title or not link:
                    continue # Skip broken articles
                    
                publisher = article.get('publisher', 'Yahoo Finance')
                pub_time_unix = article.get('providerPublishTime', 0)
                
                if pub_time_unix > 0:
                    pub_time = datetime.datetime.fromtimestamp(pub_time_unix)
                else:
                    pub_time = datetime.datetime.now()
                    
                formatted_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "time_obj": pub_time,
                    "time_str": pub_time.strftime("%b %d, %Y - %I:%M %p"),
                    "timestamp": pub_time.timestamp()
                })
    except Exception:
        pass # If yfinance fails, quietly move to the fallback

    # --- ATTEMPT 2: The Bulletproof RSS Fallback ---
    # If yfinance returned empty or broken data, scrape the XML feed directly!
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
                    # Convert RSS string date to Python datetime
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
            return [] # If both methods fail, return empty list safely

    # Finally, sort from Newest to Oldest
    formatted_news = sorted(formatted_news, key=lambda x: x['timestamp'], reverse=True)
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
# 9. ADVANCED CUSTOM METRICS (RAW FINANCIALS)
# ==========================================
def get_advanced_metrics(ticker_input, info):
    """Pulls raw accounting statements and calculates custom quant metrics."""
    try:
        stock = yf.Ticker(ticker_input)
        bs = stock.balance_sheet
        inc = stock.financials
        
        # If Yahoo Finance is missing the statements, exit safely
        if bs.empty or inc.empty:
            return None
            
        # Grab the most recent annual column (Index 0)
        recent_bs = bs.iloc[:, 0]
        recent_inc = inc.iloc[:, 0]
        
        # Helper function to safely find rows even if Yahoo changes the names
        def safe_extract(series, possible_keys):
            for key in possible_keys:
                if key in series.index and not pd.isna(series[key]):
                    return float(series[key])
            return 0.0

        # --- RAW DATA EXTRACTION ---
        net_income = safe_extract(recent_inc, ['Net Income', 'Net Income Common Stockholders'])
        revenue = safe_extract(recent_inc, ['Total Revenue', 'Operating Revenue'])
        ebit = safe_extract(recent_inc, ['EBIT', 'Operating Income'])
        
        total_assets = safe_extract(recent_bs, ['Total Assets'])
        total_equity = safe_extract(recent_bs, ['Stockholders Equity', 'Total Stockholder Equity', 'Total Equity Gross Minority Interest'])
        total_liab = safe_extract(recent_bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        current_assets = safe_extract(recent_bs, ['Current Assets'])
        current_liab = safe_extract(recent_bs, ['Current Liabilities'])
        retained_earnings = safe_extract(recent_bs, ['Retained Earnings'])
        
        market_cap = info.get('marketCap', 0.0)

        # --- 1. DUPONT ANALYSIS COMPONENTS ---
        net_profit_margin = (net_income / revenue) if revenue else 0
        asset_turnover = (revenue / total_assets) if total_assets else 0
        equity_multiplier = (total_assets / total_equity) if total_equity else 0
        dupont_roe = net_profit_margin * asset_turnover * equity_multiplier

        # --- 2. ALTMAN Z-SCORE (Bankruptcy Risk) ---
        # Formula: Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
        working_capital = current_assets - current_liab
        A = working_capital / total_assets if total_assets else 0
        B = retained_earnings / total_assets if total_assets else 0
        C = ebit / total_assets if total_assets else 0
        D = market_cap / total_liab if total_liab else 0
        E = revenue / total_assets if total_assets else 0
        
        z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
        
        if z_score > 2.99:
            z_zone = "Safe Zone 🟢"
        elif z_score > 1.81:
            z_zone = "Grey Zone 🟡"
        else:
            z_zone = "Distress Zone 🔴"

        return {
            "dupont": {
                "roe": dupont_roe,
                "net_margin": net_profit_margin,
                "asset_turnover": asset_turnover,
                "equity_multiplier": equity_multiplier
            },
            "altman": {
                "score": z_score,
                "zone": z_zone
            }
        }
    except Exception as e:
        return None

# ==========================================
# 9. ADVANCED CUSTOM METRICS (RAW FINANCIALS)
# ==========================================
def get_advanced_metrics(ticker_input, info):
    """Pulls raw accounting statements and calculates custom quant metrics."""
    try:
        stock = yf.Ticker(ticker_input)
        bs = stock.balance_sheet
        inc = stock.financials
        
        if bs.empty or inc.empty:
            return None
            
        recent_bs = bs.iloc[:, 0]
        recent_inc = inc.iloc[:, 0]
        
        def safe_extract(series, possible_keys):
            for key in possible_keys:
                if key in series.index and not pd.isna(series[key]):
                    return float(series[key])
            return 0.0

        # --- RAW DATA EXTRACTION ---
        net_income = safe_extract(recent_inc, ['Net Income', 'Net Income Common Stockholders'])
        revenue = safe_extract(recent_inc, ['Total Revenue', 'Operating Revenue'])
        ebit = safe_extract(recent_inc, ['EBIT', 'Operating Income'])
        tax_provision = safe_extract(recent_inc, ['Tax Provision', 'Income Tax Expense'])
        pretax_income = safe_extract(recent_inc, ['Pretax Income', 'Income Before Tax'])
        
        total_assets = safe_extract(recent_bs, ['Total Assets'])
        total_equity = safe_extract(recent_bs, ['Stockholders Equity', 'Total Stockholder Equity'])
        total_liab = safe_extract(recent_bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        current_assets = safe_extract(recent_bs, ['Current Assets'])
        current_liab = safe_extract(recent_bs, ['Current Liabilities'])
        retained_earnings = safe_extract(recent_bs, ['Retained Earnings'])
        total_debt_bs = safe_extract(recent_bs, ['Total Debt'])
        
        if total_debt_bs == 0: 
            total_debt_bs = info.get('totalDebt', 0.0)
            
        market_cap = info.get('marketCap', 0.0)

        # --- 1. DUPONT ANALYSIS ---
        net_profit_margin = (net_income / revenue) if revenue else 0
        asset_turnover = (revenue / total_assets) if total_assets else 0
        equity_multiplier = (total_assets / total_equity) if total_equity else 0
        dupont_roe = net_profit_margin * asset_turnover * equity_multiplier

        # --- 2. ALTMAN Z-SCORE ---
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

        # --- 3. LEVERED VS UNLEVERED BETA ---
        levered_beta = info.get('beta', 0.0)
        
        # Calculate Effective Tax Rate
        if pretax_income and pretax_income > 0:
            tax_rate = tax_provision / pretax_income
            tax_rate = max(0.0, min(tax_rate, 0.5)) # Cap between 0 and 50%
        else:
            tax_rate = 0.21 # Default corporate fallback
            
        # Market Debt-to-Equity
        d_e_ratio = (total_debt_bs / market_cap) if market_cap else 0.0
        
        if levered_beta:
            unlevered_beta = levered_beta / (1 + ((1 - tax_rate) * d_e_ratio))
        else:
            unlevered_beta = 0.0

        # ... (Keep all the math above exactly the same) ...

        return {
            "dupont": {"roe": dupont_roe, "net_margin": net_profit_margin, "asset_turnover": asset_turnover, "equity_multiplier": equity_multiplier},
            "altman": {"score": z_score, "zone": z_zone},
            "beta": {"levered": levered_beta, "unlevered": unlevered_beta, "tax_rate": tax_rate, "d_e_ratio": d_e_ratio},
            
            # 👇 THIS IS THE CRITICAL MISSING LINE 👇
            "raw_data": {"income_statement": recent_inc, "balance_sheet": recent_bs}
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