import streamlit as st
import pandas as pd
import plotly.express as px
import data_engine 
import time

# 🚨 INITIALIZE AI KEY
data_engine.configure_ai(api_key=st.secrets["GEMINI_API_KEY"])

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

# --- 1. PREPARE MUTUAL FUND DATA ---
import plotly.graph_objects as go # Needed for the MF charts

@st.cache_data(ttl=86400)
def load_fund_choices():
    raw_list = data_engine.get_mf_list()
    if raw_list:
        return {item['schemeName']: str(item['schemeCode']) for item in raw_list}
    return {}

fund_dict = load_fund_choices()

# --- 2. DYNAMIC TOP NAVIGATION BAR ---
col_ex, col_srch, col_emp = st.columns([1, 2, 1])
with col_ex:
    market = st.selectbox("🌍 Select Market", ["India (NSE)", "India (BSE)", "US (NASDAQ/NYSE)", "Mutual Funds (India)"])

with col_srch:
    if market == "Mutual Funds (India)":
        # Search bar magically turns into a dropdown when Mutual Funds is selected!
       search_query = st.multiselect("🔍 Search & Compare up to 5 Funds", options=list(fund_dict.keys()), max_selections=5)
    else:
        # Standard stock search bar
        search_query = st.text_input("🔍 Search Company Name or Ticker (e.g., Wipro, ITC, Apple, AAPL)")

st.divider()

# --- 3. MUTUAL FUND WORLD (THE SPLIT) ---
if market == "Mutual Funds (India)" and search_query:
    with st.status("⚙️ Running Quantitative Models...", expanded=True) as status:
        all_fund_data = {}
        all_metrics = {}
        all_meta = {} # Holds the premium Fund Details
        
        for name in search_query:
            code = fund_dict[name]
            st.write(f"📡 Fetching lifetime history for: {name[:30]}...")
            
            merged_df, mf_meta, msg = data_engine.get_mf_and_benchmark(code)
            
            if merged_df is not None:
                st.write(f"🧮 Calculating Alpha and Beta for {name[:30]}...")
                all_fund_data[name] = merged_df
                all_metrics[name] = data_engine.calculate_mf_metrics(merged_df)
                all_meta[name] = mf_meta 
            else:
                st.error(f"Failed to fetch data for {name}: {msg}")
        status.update(label="Comparison Complete!", state="complete", expanded=False)

    if all_fund_data:
        st.divider()
        st.write("### 📈 Lifetime Growth Comparison (Rebased to ₹10,000)")
        fig = go.Figure()
        
        # Benchmark Line
        longest_fund_name = max(all_fund_data, key=lambda k: len(all_fund_data[k]))
        bench_data = all_fund_data[longest_fund_name]['Benchmark_Close']
        normalized_bench = (bench_data / bench_data.iloc[0]) * 10000
        fig.add_trace(go.Scatter(x=normalized_bench.index, y=normalized_bench, mode='lines', name='NIFTY 50 (Benchmark)', line=dict(color='white', width=2, dash='dot')))
        
        # 5 Custom Colors for up to 5 funds
        colors = ['#2ab7ca', '#fe4a90', '#ffcc00', '#00ffaa', '#b366ff']
        for i, (name, df) in enumerate(all_fund_data.items()):
            normalized_nav = (df['MF_NAV'] / df['MF_NAV'].iloc[0]) * 10000
            short_name = name[:40] + "..." if len(name) > 40 else name
            fig.add_trace(go.Scatter(x=normalized_nav.index, y=normalized_nav, mode='lines', name=short_name, line=dict(color=colors[i % len(colors)], width=2)))

        fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0), hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### 📊 Institutional Quantitative Analysis")
        cols = st.columns(len(all_metrics))
        
        for idx, (name, metrics) in enumerate(all_metrics.items()):
            with cols[idx]:
                with st.container(border=True):
                    st.write(f"#### {name[:35]}")
                    
                    # --- 1. THE RAYTURNZ SCORE ---
                    score = metrics.get('RayTurnz Score', 5.0)
                    if score >= 8: st.success(f"🏆 RayTurnz Score: {score:.1f} / 10")
                    elif score >= 5: st.warning(f"⚖️ RayTurnz Score: {score:.1f} / 10")
                    else: st.error(f"⚠️ RayTurnz Score: {score:.1f} / 10")
                    
                    # --- 2. FUNDAMENTALS EXPANDER ---
                    with st.expander("📋 Fund Fundamentals & Fees"):
                        meta = all_meta[name]
                        for k, v in meta.items():
                            st.write(f"**{k}:** {v}")
                    st.divider()
                    
                    # --- 3. ABSOLUTE RETURNS (Trailing) ---
                    st.write("**Absolute Returns (Trailing)**")
                    t1, t2, t3 = st.columns(3)
                    t_ret = metrics.get('Trailing Returns', {})
                    
                    # Safely grab the trailing returns (some new funds might not have 5 years of data)
                    y1 = f"{t_ret.get('1Y')*100:.1f}%" if t_ret.get('1Y') else "N/A"
                    y3 = f"{t_ret.get('3Y')*100:.1f}%" if t_ret.get('3Y') else "N/A"
                    y5 = f"{t_ret.get('5Y')*100:.1f}%" if t_ret.get('5Y') else "N/A"
                    
                    t1.metric("1 Year", y1)
                    t2.metric("3 Year", y3)
                    t3.metric("5 Year", y5)
                    st.divider()

                    # --- 4. RISK & OUTPERFORMANCE ---
                    st.write("**Risk & Outperformance**")
                    st.metric("Jensen's Alpha", f"{metrics.get('Alpha', 0)*100:.2f}%", help="Skill of the manager over the benchmark.")
                    st.metric("Market Beta", f"{metrics.get('Beta', 1):.2f}", help="Sensitivity to market crashes. 1.0 is equal to the market.")
                    st.metric("Sharpe Ratio", f"{metrics.get('Sharpe Ratio', 0):.2f}", help="Risk-adjusted efficiency.")
                    st.divider()

                    # --- 5. DOWNSIDE & DRAWDOWN ANALYSIS ---
                    st.write("**Institutional Downside Analysis**")
                    st.metric("Max Drawdown", f"{metrics.get('Max Drawdown', 0)*100:.1f}%", help="The absolute worst crash this fund has ever experienced.")
                    st.metric("Sortino Ratio", f"{metrics.get('Sortino Ratio', 0):.2f}", help="Risk-adjusted return penalizing ONLY downside volatility.")
                    st.caption(f"📈 Up Capture: {metrics.get('Up Capture', 100):.1f}% | 📉 Down Capture: {metrics.get('Down Capture', 100):.1f}%")

        # --- 6. DYNAMIC AI WEALTH ADVISOR ---
        st.divider()
        st.subheader("🤖 RayTurnz AI Wealth Advisor")
        
        with st.spinner("Analyzing quantitative metrics and drafting final verdict..."):
            ai_verdict = data_engine.generate_mf_verdict(all_metrics, all_meta)
            with st.container(border=True):
                st.markdown(ai_verdict)

    # THE BRICK WALL
    st.stop()


# --- 4. STOCK WORLD ---
# Because of the st.stop() above, the code below ONLY runs if the user searches for a Stock!
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
            
            # 👇 Helper function to build professional, aligned cards
            def render_fundamental_card(title, data_dict, hero_key):
                with st.container(border=True):
                    st.write(f"### {title}")
                    
                    # 1. Pop out the most important metric at the top
                    if hero_key in data_dict:
                        st.metric(label=hero_key, value=data_dict[hero_key])
                        st.divider()
                    
                    # 2. Align the rest of the metrics in a clean 2-column grid
                    for k, v in data_dict.items():
                        if k != hero_key:
                            col_lbl, col_val = st.columns([3, 2])
                            col_lbl.caption(k)
                            col_val.markdown(f"**{v}**")

            # 👇 Applying the new UI to your data
            with col_f1:
                val_data = data_engine.get_valuation(info)
                render_fundamental_card("💰 Valuation", val_data, "Trailing P/E")
                
                prof_data = data_engine.get_profitability(info)
                render_fundamental_card("📊 Profitability", prof_data, "Profit Margin")
                
            with col_f2:
                fin_data = data_engine.get_financial_strength(info)
                render_fundamental_card("🏦 Financial Strength", fin_data, "Current Ratio")
                
                gro_data = data_engine.get_growth(info)
                render_fundamental_card("🚀 Growth", gro_data, "Revenue Growth")

        with tab3:
            st.write("### 🔬 Advanced Custom Metrics")
            st.caption("Calculated in real-time by scraping raw Income Statements and Balance Sheets.")
            
            with st.spinner("Sourcing raw financial statements..."):
                adv_metrics = data_engine.get_advanced_metrics(ticker_input, info)
                
            if adv_metrics:
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
                        
                        delta_beta = beta_data['unlevered'] - beta_data['levered']
                        st.metric("Unlevered Beta (Asset)", f"{beta_data['unlevered']:.2f}", f"{delta_beta:.2f} Debt Impact", delta_color="inverse")
                        
                        st.write("**Inputs Used:**")
                        st.write(f"- **Effective Tax Rate (T):** {beta_data['tax_rate']*100:.1f}%")
                        st.write(f"- **Market D/E Ratio:** {beta_data['d_e_ratio']:.2f}x")
                        
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
                try:
                    market_val = float(backtest_data['market_return'].replace('%', ''))
                    weekly_val = float(backtest_data['weekly']['return'].replace('%', ''))
# --- DYNAMIC ACTIONABLE VERDICT ---
                    st.divider()
                    st.write("### 🎯 Final Quant Verdict (Live Action)")
                    
                    if sig_week == "BULLISH":
                        st.success(f"**ACTION: BUY / ACCUMULATE**\n\n**Data-Driven Reasoning:** The Live Machine Learning model is projecting a **{str_week}** trend for the upcoming 5 days. Based on the historical backtest metrics above, the weekly predictive layer successfully filters out daily noise to identify statistically favorable entry points.")
                    elif sig_week == "BEARISH":
                        st.error(f"**ACTION: SELL / REDUCE EXPOSURE**\n\n**Data-Driven Reasoning:** The Live Machine Learning model is projecting a **{str_week}** trend for the upcoming 5 days. Historical backtesting indicates a high probability of downside risk. It is recommended to protect capital right now.")
                    else:
                        st.warning("**ACTION: HOLD / WAIT**\n\n**Data-Driven Reasoning:** The quantitative models are currently showing weak or conflicting probability distributions. It is mathematically safer to wait for a definitive breakout or breakdown.")

                except Exception as e:
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
            st.write("### 📰 Multi-API Live News & AI Consensus")
            st.caption(f"Cross-verifying Yahoo, NewsData, GNews, and StockData for {ticker_input}.")
            
            with st.spinner("Fetching data from all endpoints..."):
                # Fetch all 4 sources
                y_news = data_engine.get_stock_news(ticker_input) 
                n_news = data_engine.get_newsdata_feed(ticker_input)
                g_news = data_engine.get_gnews_feed(ticker_input)
                s_news = data_engine.get_stockdata_feed(ticker_input)
                
                all_news_payload = {
                    "Yahoo Finance": y_news, 
                    "NewsData.io": n_news, 
                    "GNews": g_news,
                    "StockData": s_news
                }
            
            # --- MASTER AI BUTTON ---
            st.info("🧠 **Information Asymmetry Check:** Let AI cross-verify all sources for a consensus verdict.")
            if st.button("✨ Generate Master AI Consensus Report", type="primary", use_container_width=True):
                with st.spinner("AI is analyzing and comparing all sources..."):
                    ai_summary = data_engine.analyze_consensus_sentiment(all_news_payload, ticker_input)
                    with st.container(border=True):
                        st.markdown(ai_summary)
            
            st.divider()

            # --- 4-COLUMN DASHBOARD LAYOUT ---
            st.write("### 🌐 Global News Terminal")
            
            # Create 4 equal columns
            col_y, col_g, col_n, col_s = st.columns(4)

            # Define a helper to render a news column
            def render_news_column(col, title, news_list, icon):
                with col:
                    st.markdown(f"#### {icon} {title}")
                    if not news_list:
                        st.caption("No data found.")
                    else:
                        with st.container(height=600, border=True):
                            for n in news_list:
                                st.markdown(f"**[{n.get('title', 'No Title')}]({n.get('link', '#')})**")
                                st.caption(f"📅 {n.get('date', 'Today')}")
                                st.divider()

            # Map the 4 API sources to the 4 columns
            render_news_column(col_y, "Yahoo Finance", y_news, "💹")
            render_news_column(col_g, "Google News", g_news, "🔍")
            render_news_column(col_n, "NewsData.io", n_news, "📡")
            render_news_column(col_s, "StockData", s_news, "🏛️")