import streamlit as st
import pandas as pd
import plotly.express as px
import data_engine 
import time

# 🔐 PRODUCTION-GRADE SECURITY
# This pulls the key from .streamlit/secrets.toml securely
if "GEMINI_API_KEY" in st.secrets:
    data_engine.configure_ai(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 Configuration Error: GEMINI_API_KEY not found in secrets.")

st.set_page_config(page_title="RayTurnz AI Stock Analyzer", layout="wide", page_icon="⚡")

# 👇 CUSTOM CSS INJECTION FOR ANIMATIONS 👇
st.markdown("""
<style>
    /* Smooth hover effect for metric boxes */
    div[data-testid="metric-container"] {
        background-color: rgba(128, 128, 128, 0.05);
        border-radius: 10px;
        padding: 10px;
        transition: all 0.3s ease;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        border-color: #2ab7ca;
    }
    
    /* Make the title pop AND center it */
    .bolt-title {
        background: -webkit-linear-gradient(45deg, #fe4a90, #2ab7ca);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5em; 
        margin-bottom: 0px;
        text-align: center; 
    }
    
    /* Center the subtitle too */
    .bolt-subtitle {
        text-align: center; 
        font-size: 1.2em;
        color: gray;
        margin-bottom: 20px;
        font-weight: 600;
    }
    
    /* Styling the tabs to look more modern */
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        transition: all 0.2s ease-in-out;
    }
    button[data-baseweb="tab"]:hover {
        color: #2ab7ca !important;
    }

    /* --- THE BOUNCING DVD ANIMATION --- */
    .bouncing-bg-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 0;
        pointer-events: none;
        overflow: hidden;
        opacity: 0.3;
    }
    .bounce-x {
        animation: moveX 15s linear infinite alternate;
        position: absolute;
    }
    .bounce-y {
        animation: moveY 11s linear infinite alternate;
        font-family: monospace;
        font-size: 3rem;
        font-weight: 900;
        color: #2ab7ca;
        white-space: nowrap;
    }
    @keyframes moveX {
        0% { transform: translateX(0); }
        100% { transform: translateX(calc(100vw - 600px)); }
    }
    @keyframes moveY {
        0% { transform: translateY(0); }
        100% { transform: translateY(calc(100vh - 100px)); }
    }
</style>

<div class="bouncing-bg-container">
    <div class="bounce-x">
        <div class="bounce-y">LIVE ANALYSIS...</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Generate the Centered HTML text
st.markdown('<p class="bolt-title">⚡ RayTurnz AI Stock Analyzer</p>', unsafe_allow_html=True)
st.markdown('<p class="bolt-subtitle">Your Smart AI Stock Decision Maker</p>', unsafe_allow_html=True)
st.divider()

col_ex, col_srch, col_emp = st.columns([1, 2, 1])
with col_ex:
    market = st.selectbox("🌍 Select Market", ["India (NSE)", "India (BSE)", "US (NASDAQ/NYSE)"])
with col_srch:
    search_query = st.text_input("🔍 Search Company Name or Ticker (e.g., Wipro, ITC, Apple, AAPL)")

st.divider()

if search_query:
    with st.status("⚡ Initializing RayTurnz AI Engine...", expanded=True) as status:
        
        # 1. Convert name to ticker while respecting the market dropdown!
        st.write("🔍 Resolving company name...")
        raw_ticker = data_engine.resolve_ticker(search_query, market)
        st.write(f"✅ Auto-detected Ticker: **{raw_ticker}**")
        
        # 2. Fetch the data (we pass market="Auto" because raw_ticker already has the .NS or .BO attached now)
        st.write("📡 Connecting to global market feeds...")
        success, ticker_input, info, hist = data_engine.fetch_stock_data(raw_ticker, market="Auto")
        
        if success:
            st.write("🧮 Calculating momentum indicators...")
            hist = data_engine.calculate_technicals(hist)
            
            st.write("🧠 Querying institutional holding records...")
            time.sleep(0.5) 
            
            status.update(label="Analysis Complete!", state="complete", expanded=False)
            st.toast(f"Successfully loaded data for {ticker_input}!", icon="✅")
        else:
            status.update(label="Data Fetch Failed", state="error", expanded=False)

    if not success:
        st.error(f"⚠️ Could not fetch data for {raw_ticker} in the {market} market.")
    else:
        # 👇 EVERYTHING BELOW HERE IS INSIDE THE 'ELSE' BLOCK 👇
        c_price, trend, m_return, pos, zone = data_engine.get_header_metrics(info, hist)

        col_name, col_price = st.columns([3, 1])
        with col_name:
            st.header(f"🏢 {info.get('longName', 'Company Name')} ({ticker_input})")
        with col_price:
            # 👇 Notice how this is perfectly indented now!
            st.metric("Current Price", f"{info.get('currency', 'INR')} {c_price:.2f}", f"{m_return:.2f}% (1M)")

        # 👇 New Auto-Wrapping Red Flags Block 👇
        red_flags = data_engine.get_red_flags(info)
        red_flags_text = "None"
        
        if not red_flags:
            st.success("✅ **System Scan:** No major fundamental red flags detected.")
        else:
            st.error(f"⚠️ **Risk Alert:** The system detected {len(red_flags)} major red flags.")
            
            # Create a string of flags for the Gemini AI prompt later
            red_flags_text = ", ".join([f"{f[0]} ({f[1]})" for f in red_flags])
            
            # Dynamically wrap the UI metrics into rows of 4
            cols_per_row = 4
            for i in range(0, len(red_flags), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(red_flags):
                        f_name, f_val = red_flags[i + j]
                        with cols[j]:
                            st.metric(label=f_name, value=f_val, delta="Negative Indicator", delta_color="inverse")

        st.divider()

        # --- SAFE TECHNICALS CHECK ---
        if not hist.empty:
            latest = hist.iloc[-1]
            c_rsi, c_macd = latest['RSI'], latest['MACD']
        else:
            latest = None
            c_rsi, c_macd = None, None

        # --- TABS DECLARATION ---
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Market Overview", "💼 Deep Fundamentals", "🔬 Advanced Metrics", "🤖 AI Decision Support", "🏦 Fund Holdings", "📰 Live News"])

        with tab1:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                with st.container(border=True):
                    st.write("### 👥 Ownership & Holdings")
                    ins, inst, pub = data_engine.get_ownership(info)
                    st.write(f"**Promoter / Insider:** {data_engine.fmt_pct(ins)}")
                    st.write(f"**Institutions:** {data_engine.fmt_pct(inst)}")

                    if ins > 0 or inst > 0:
                        df_holdings = pd.DataFrame({"Category": ["Promoters", "Institutions", "Public"], "Holding": [ins, inst, pub]})
                        fig = px.pie(df_holdings, values="Holding", names="Category", hole=0.6, color_discrete_sequence=px.colors.sequential.Teal)
                        fig.update_traces(textposition='inside', textinfo='percent+label', showlegend=False, hoverinfo="label+percent")
                        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
                        st.plotly_chart(fig, use_container_width=True)

            with col_t2:
                with st.container(border=True):
                    st.write("### 📊 Interactive Price Action")
                    
                    if not hist.empty:
                        chart_tabs = st.tabs(["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "Max"])
                        
                        def display_dynamic_chart(df_series, label):
                            if len(df_series) >= 2:
                                t_val = "Uptrend 📈" if df_series.iloc[-1] > df_series.iloc[0] else "Downtrend 📉"
                            else:
                                t_val = "Sideways ➖"
                            st.write(f"Trend ({label})\n### {t_val}")
                            st.line_chart(df_series, height=250, use_container_width=True)

                        with chart_tabs[0]: display_dynamic_chart(hist['Close'].tail(21), "1M")
                        with chart_tabs[1]: display_dynamic_chart(hist['Close'].tail(63), "3M")
                        with chart_tabs[2]: display_dynamic_chart(hist['Close'].tail(126), "6M")
                        with chart_tabs[3]: display_dynamic_chart(hist['Close'].tail(252), "1Y")
                        with chart_tabs[4]: display_dynamic_chart(hist['Close'].tail(504), "2Y")
                        with chart_tabs[5]: display_dynamic_chart(hist['Close'].tail(756), "3Y")
                        with chart_tabs[6]: display_dynamic_chart(hist['Close'].tail(1260), "5Y")
                        with chart_tabs[7]: display_dynamic_chart(hist['Close'], "Max")

        with tab2:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                with st.container(border=True):
                    st.write("### 💰 Valuation")
                    val_data = data_engine.get_valuation(info)
                    for k, v in val_data.items(): st.write(f"**{k}:** {v}")
                with st.container(border=True):
                    st.write("### 📊 Profitability")
                    prof_data = data_engine.get_profitability(info)
                    for k, v in prof_data.items(): st.write(f"**{k}:** {v}")
            with col_f2:
                with st.container(border=True):
                    st.write("### 🏦 Financial Strength")
                    fin_data = data_engine.get_financial_strength(info)
                    for k, v in fin_data.items(): st.write(f"**{k}:** {v}")
                with st.container(border=True):
                    st.write("### 🚀 Growth")
                    gro_data = data_engine.get_growth(info)
                    for k, v in gro_data.items(): st.write(f"**{k}:** {v}")
        with tab3:
            st.write("### 🔬 Advanced Custom Metrics")
            st.caption("Calculated in real-time by scraping raw Income Statements and Balance Sheets.")
            
            with st.spinner("Sourcing raw financial statements..."):
                adv_metrics = data_engine.get_advanced_metrics(ticker_input, info)
                
            if adv_metrics:
                # Switched to 3 columns to fit Beta!
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1:
                    with st.container(border=True):
                        st.write("#### 📊 DuPont Analysis")
                        st.caption("Deconstructs Return on Equity to see *how* returns are generated.")
                        
                        st.markdown(r"$$ROE = \frac{Net Income}{Sales} \times \frac{Sales}{Assets} \times \frac{Assets}{Equity}$$")
                        
                        dupont = adv_metrics['dupont']
                        st.metric("Implied ROE", f"{dupont['roe']*100:.2f}%")
                        
                        st.write("**The 3 Pillars:**")
                        st.write(f"- **Net Profit Margin:** {dupont['net_margin']*100:.2f}% *(Profitability)*")
                        st.write(f"- **Asset Turnover:** {dupont['asset_turnover']:.2f}x *(Efficiency)*")
                        st.write(f"- **Equity Multiplier:** {dupont['equity_multiplier']:.2f}x *(Leverage)*")
                        
                with col_m2:
                    with st.container(border=True):
                        st.write("#### 🚨 Altman Z-Score")
                        st.caption("A credit-strength test that predicts bankruptcy risk.")
                        
                        st.markdown(r"$$Z = 1.2X_1 + 1.4X_2 + 3.3X_3 + 0.6X_4 + 1.0X_5$$")
                        
                        altman = adv_metrics['altman']
                        st.metric("Z-Score", f"{altman['score']:.2f}", altman['zone'], delta_color="off")
                        
                        st.write("**Score Guide:**")
                        st.write("- **> 2.99:** Safe Zone (Financially Sound)")
                        st.write("- **1.81 - 2.99:** Grey Zone (Caution)")
                        st.write("- **< 1.81:** Distress Zone (High Risk)")
                        
                with col_m3:
                    with st.container(border=True):
                        st.write("#### 📈 Volatility (Beta)")
                        st.caption("Strips out the impact of debt to show pure asset volatility.")
                        
                        st.markdown(r"$$\beta_U = \frac{\beta_L}{1 + ((1 - T) \times \frac{D}{E})}$$")
                        
                        beta_data = adv_metrics['beta']
                        st.metric("Levered Beta (Reported)", f"{beta_data['levered']:.2f}")
                        
                        # Show if debt is inflating the risk
                        delta_beta = beta_data['unlevered'] - beta_data['levered']
                        st.metric("Unlevered Beta (Asset)", f"{beta_data['unlevered']:.2f}", f"{delta_beta:.2f} Debt Impact", delta_color="inverse")
                        
                        st.write("**Inputs Used:**")
                        st.write(f"- **Effective Tax Rate (T):** {beta_data['tax_rate']*100:.1f}%")
                        st.write(f"- **Market D/E Ratio:** {beta_data['d_e_ratio']:.2f}x")
                        st.write(f"- **Effective Tax Rate (T):** {beta_data['tax_rate']*100:.1f}%")
                        st.write(f"- **Market D/E Ratio:** {beta_data['d_e_ratio']:.2f}x")
                        
                # 👇 PASTE EVERYTHING BELOW THIS LINE 👇
                
                # --- RAW FINANCIALS DROP-DOWN ---
                st.divider()
                with st.expander("📄 Verify Raw Financial Statements (Source Data)"):
                    st.write("This is the raw accounting data extracted directly from the company's latest annual filings.")
                    col_raw1, col_raw2 = st.columns(2)
                    with col_raw1:
                        st.write("#### Income Statement")
                        st.dataframe(adv_metrics['raw_data']['income_statement'], use_container_width=True)
                    with col_raw2:
                        st.write("#### Balance Sheet")
                        st.dataframe(adv_metrics['raw_data']['balance_sheet'], use_container_width=True)
                
                # --- NEW REGRESSION & CAPM SECTION ---
                st.divider()
                st.write("### 📈 Statistical Regression & CAPM Analysis")
                st.caption(f"5-Year Monthly linear regression against market index.")
                
                with st.spinner("Running statistical regression..."):
                    reg_data = data_engine.calculate_beta_regression(ticker_input, market)
                    
                if reg_data:
                    col_reg1, col_reg2 = st.columns(2)
                    
                    beta = reg_data['beta']
                    se = reg_data['std_err']
                    r2 = reg_data['r_squared']
                    
                    with col_reg1:
                        with st.container(border=True):
                            st.write("#### 1. Performance vs Market (Jensen's Alpha)")
                            st.caption("How well did the stock do relative to the market?")
                            st.latex(r"$$ \alpha = Intercept - \frac{R_f}{n}(1 - \beta) $$")
                            
                            alpha = reg_data['jensens_alpha_ann'] * 100
                            st.metric("Annualized Jensen's Alpha", f"{alpha:.2f}%", 
                                      "Outperformed Expectations" if alpha > 0 else "Underperformed Expectations", 
                                      delta_color="normal" if alpha > 0 else "inverse")
                            
                        with st.container(border=True):
                            st.write("#### 2. Risk Decomposition ($R^2$)")
                            st.caption("What proportion of risk is attributable to the market vs. firm-specific?")
                            st.write(f"**Market Risk (Systematic):** {r2 * 100:.1f}%")
                            st.write(f"**Firm-Specific Risk (Idiosyncratic):** {(1 - r2) * 100:.1f}%")
                            
                    with col_reg2:
                        with st.container(border=True):
                            st.write("#### 3. Beta Estimate Ranges")
                            st.caption("Historical estimate of beta and probability ranges.")
                            
                            st.write(f"**Historical Beta:** {beta:.2f}")
                            st.write(f"**67% Probability Range:** {(beta - se):.2f} to {(beta + se):.2f}")
                            st.write(f"**95% Probability Range:** {(beta - 2*se):.2f} to {(beta + 2*se):.2f}")
                            st.caption(f"Standard Error = {se:.4f}")
                            
                        with st.container(border=True):
                            st.write("#### 4. Required Return (CAPM)")
                            st.caption("Based on this beta, what is the required return?")
                            st.latex(r"$$ E(R) = R_f + \beta \times Market Premium $$")
                            
                            req_ret = reg_data['required_return'] * 100
                            st.metric("Cost of Equity (Required Return)", f"{req_ret:.2f}%")
                            st.caption(f"Inputs: Risk-Free Rate = {reg_data['rf_rate']*100:.1f}%, Risk Premium = {reg_data['market_premium']*100:.1f}%")
                            
            else:
                st.info("Raw financial statements are currently unavailable for this ticker to calculate advanced metrics.")

        with tab4:
            st.write("### ⚙️ 1. Historical Quant Model Prediction")
            st.caption("Data Source: Random Forest ML algorithms trained on historical patterns.")
            
            if latest is not None:
                sig_day, str_day, sig_week, str_week = data_engine.run_quant_models(latest)
            else:
                sig_day, str_day, sig_week, str_week = "N/A", "Not enough data", "N/A", "Not enough data"
            
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                with st.container(border=True):
                    st.write("#### Next Day Prediction")
                    if sig_day == "BULLISH": st.success(f"📈 {str_day}")
                    elif sig_day == "BEARISH": st.error(f"📉 {str_day}")
                    else: st.warning(str_day)
            with col_q2:
                with st.container(border=True):
                    st.write("#### Next Week Prediction")
                    if sig_week == "BULLISH": st.success(f"📈 {str_week}")
                    elif sig_week == "BEARISH": st.error(f"📉 {str_week}")
                    else: st.warning(str_week)

            st.divider()

            st.write("### 🧮 2. Live Technical Analysis")
            st.caption(f"Data Source: Real-time momentum calculations for {ticker_input}.")
            
            col_ta1, col_ta2, col_ta3 = st.columns(3)
            with col_ta1:
                rsi_status = "Neutral"
                if c_rsi is not None and not pd.isna(c_rsi):
                    if c_rsi > 70: rsi_status = "Overbought ⚠️"
                    elif c_rsi < 30: rsi_status = "Oversold 🟢"
                st.metric("Current RSI (14-Day)", f"{c_rsi:.2f}" if c_rsi is not None and not pd.isna(c_rsi) else "N/A", rsi_status, delta_color="off")
            with col_ta2:
                st.metric("Current MACD", f"{c_macd:.2f}" if c_macd is not None and not pd.isna(c_macd) else "N/A")
            with col_ta3:
                st.metric("Current 52-Week Zone", zone)

            st.divider()

            st.write("### 🤖 3. Generative AI Synthesis")
            st.caption("Explainability Layer: Gemini AI synthesizes all indicators into a strategy.")
            
            with st.container(border=True):
                if st.button("✨ Generate Hybrid AI Verdict", type="primary", use_container_width=True):
                    with st.spinner("Executing Final AI Analysis..."):
                        result = data_engine.generate_genai_verdict(info, trend, zone, c_rsi, c_macd, red_flags_text, str_day, str_week)
                        st.markdown(result)
                        
            st.divider()
            
            st.write("### 🛡️ 4. Historical Backtest Validation")
            st.caption(f"Market Benchmark: NIFTY 50 (2022-Present).")
            
            backtest_data = data_engine.get_backtest_results()
            if backtest_data:
                st.caption(f"**Standard Buy & Hold Return:** {backtest_data.get('market_return', 'N/A')}")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    with st.container(border=True):
                        st.write("**Daily Strategy Test**")
                        st.metric("Accuracy", backtest_data['daily']['accuracy'])
                        color_day = "normal" if backtest_data['daily']['beat'] else "inverse"
                        st.metric("Strategy Return", backtest_data['daily']['return'], delta="Beat Market" if backtest_data['daily']['beat'] else "Underperformed", delta_color=color_day)
                with col_b2:
                    with st.container(border=True):
                        st.write("**Weekly Strategy Test**")
                        st.metric("Accuracy", backtest_data['weekly']['accuracy'])
                        color_week = "normal" if backtest_data['weekly']['beat'] else "inverse"
                        st.metric("Strategy Return", backtest_data['weekly']['return'], delta="Beat Market" if backtest_data['weekly']['beat'] else "Underperformed", delta_color=color_week)
                
                st.write("#### 🧠 What does this mean for you?")
                try:
                    market_val = float(backtest_data['market_return'].replace('%', ''))
                    weekly_val = float(backtest_data['weekly']['return'].replace('%', ''))
                    
                    if weekly_val > market_val:
                        explanation = f"**Victory!** The AI's weekly strategy actively traded and made **{weekly_val:.2f}%**, beating the lazy 'Buy & Hold' approach. It successfully timed the market to maximize your profits."
                    elif weekly_val > 0:
                        explanation = f"**Safe but Cautious:** The AI made a solid **{weekly_val:.2f}%** profit, but just buying and holding would have made you **{market_val:.2f}%**. Why? The AI acts like a protective shield—when the market looks risky, it sells and holds cash. In a massive bull run, this cautious approach misses some upside, but it protects you from painful crashes."
                    else:
                        explanation = "**Warning:** The AI struggled in this specific market condition and lost money. This proves why AI should be a *helper*, not a replacement for your own judgment."
                        
                    st.info(f"💡 {explanation}\n\n**Key Takeaway:** Notice how the **Weekly** accuracy is much better than the **Daily**. Predicting what a stock will do tomorrow is basically a coin flip (too much random noise), but predicting the next 5 days allows the AI to catch real, profitable trends!")
                except:
                    pass
            else:
                st.warning("⚠️ Run `python train_model.py` to generate backtest results!")

        with tab5:
            st.write("### 🏦 Smart Money Tracker (Mutual Funds & Institutions)")
            st.caption("Data Source: Top institutional and mutual fund holders reported via Yahoo Finance.")
            
            mf_df, inst_df = data_engine.get_institutional_holdings(ticker_input)
            
            col_mf1, col_mf2 = st.columns(2)
            
            with col_mf1:
                st.write("#### 📈 Top 10 Mutual Fund Holders")
                if mf_df is not None and not mf_df.empty and 'Holder' in mf_df.columns:
                    val_col = 'pctHeld' if 'pctHeld' in mf_df.columns else '% Out' if '% Out' in mf_df.columns else 'Shares'
                    top_mf = mf_df.head(10).copy()
                    top_mf['Short_Name'] = top_mf['Holder'].apply(lambda x: str(x)[:35] + '...' if len(str(x)) > 35 else str(x))
                    
                    fig_mf = px.bar(top_mf, x=val_col, y='Short_Name', orientation='h', color_discrete_sequence=['#2ab7ca'])
                    fig_mf.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Percentage of Company Owned", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=350)
                    if val_col in ['pctHeld', '% Out']:
                        fig_mf.update_layout(xaxis_tickformat=".2%")
                        
                    st.plotly_chart(fig_mf, use_container_width=True)
                else:
                    st.info("No Mutual Fund holding data available for this specific stock on Yahoo Finance.")
                    
            with col_mf2:
                st.write("#### 🏛️ Top 10 Institutional Holders")
                if inst_df is not None and not inst_df.empty and 'Holder' in inst_df.columns:
                    val_col = 'pctHeld' if 'pctHeld' in inst_df.columns else '% Out' if '% Out' in inst_df.columns else 'Shares'
                    top_inst = inst_df.head(10).copy()
                    top_inst['Short_Name'] = top_inst['Holder'].apply(lambda x: str(x)[:35] + '...' if len(str(x)) > 35 else str(x))
                    
                    fig_inst = px.bar(top_inst, x=val_col, y='Short_Name', orientation='h', color_discrete_sequence=['#fe4a90'])
                    fig_inst.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Percentage of Company Owned", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=350)
                    if val_col in ['pctHeld', '% Out']:
                        fig_inst.update_layout(xaxis_tickformat=".2%")
                        
                    st.plotly_chart(fig_inst, use_container_width=True)
                else:
                    st.info("No Institutional holding data available for this specific stock on Yahoo Finance.")

        with tab6:
            st.write("### 📰 Live Market News & AI Sentiment")
            st.caption(f"Real-time news feed for {ticker_input}. Let the AI filter the noise.")
            
            with st.spinner("Fetching global news feeds..."):
                news_feed = data_engine.get_stock_news(ticker_input)
                
            if news_feed:
                # --- NEW FEATURE: AI SENTIMENT BUTTON ---
                st.info("🧠 **Information Overload?** Let RayTurnz AI read these headlines and generate a quick sentiment summary.")
                if st.button("✨ Generate AI News Report", type="primary", use_container_width=True):
                    with st.spinner("AI is reading the news..."):
                        ai_summary = data_engine.analyze_news_sentiment(news_feed, ticker_input)
                        with st.container(border=True):
                            st.markdown(ai_summary)
                
                st.divider()
                
                # --- UPGRADED UI: CLEANER NEWS CARDS ---
                st.write("#### 🗞️ Latest Headlines")
                
                # Use a cleaner layout, avoiding the massive clunky boxes
                for i, article in enumerate(news_feed[:15]): # Limit to top 15 for a clean look
                    # Alternate colors slightly by using columns
                    col_icon, col_text = st.columns([1, 15])
                    
                    with col_icon:
                        st.markdown("📰" if i == 0 else "▫️")
                        
                    with col_text:
                        st.markdown(f"**[{article['title']}]({article['link']})**")
                        st.caption(f"**{article['publisher']}** • {article['time_str']}")
                    
                    # Add a subtle divider between articles instead of full borders
                    st.markdown("<hr style='margin: 0px 0px 15px 0px; opacity: 0.2;'>", unsafe_allow_html=True)
                    
            else:
                st.info("No recent news articles found for this ticker at the moment.")