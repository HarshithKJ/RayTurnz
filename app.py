import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import json
import os
import time
from streamlit_option_menu import option_menu
import data_engine 

# 🚨 INITIALIZE AI KEY
data_engine.configure_ai(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="RayTurnz AI Stock Analyzer", layout="wide", page_icon="⚡")

# 👇 CUSTOM UI HELPER: Adaptive for both Light & Dark Mode 👇
def draw_glass_card(title, value, subtext="", color="#a3a8b8"):
    """Generates a sleek, glass-morphism metric card. 
    Notice: No hardcoded text colors for the value, allowing Streamlit to adapt to Light/Dark mode natively."""
    st.markdown(f"""
    <div style="background-color: rgba(128, 128, 128, 0.05); border-radius: 10px; padding: 15px; border: 1px solid rgba(128, 128, 128, 0.1); height: 100%; transition: transform 0.3s ease;">
        <p style="font-size: 13px; color: gray; margin-bottom: 5px; font-weight: 600;">{title}</p>
        <p style="font-size: 24px; font-weight: 700; margin-bottom: 0px; line-height: 1.2;">{value}</p>
        <p style="font-size: 12px; color: {color}; margin-top: 5px; margin-bottom: 0px;">{subtext}</p>
    </div>
    <br>
    """, unsafe_allow_html=True)

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

    /* Keep header accessible for settings, hide only the footer */
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
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
        opacity: 0.15; /* Lowered opacity so it doesn't clash in light mode */
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

# Centered adaptive title (Huge and visible in BOTH modes)
st.write("#")
st.markdown('<h1 style="text-align: center; font-size: 3.5rem; background: -webkit-linear-gradient(45deg, #fe4a90, #2ab7ca); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; margin-bottom: 0; padding-bottom: 0;">⚡ RayTurnz AI Stock Analyzer</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2em; color: gray; font-weight: 600; margin-top: -10px;">Your Smart AI Stock Decision Maker</p>', unsafe_allow_html=True)
st.divider()

# --- 1. PREPARE MUTUAL FUND DATA (ENTERPRISE CACHE ARCHITECTURE) ---
@st.cache_data(show_spinner=False)
def load_fund_choices():
    if os.path.exists("mf_database.json"):
        with open("mf_database.json", "r") as f:
            return json.load(f)
            
    raw_list = data_engine.get_mf_list()
    if raw_list and len(raw_list) > 0:
        fund_dict = {item['schemeName']: str(item['schemeCode']) for item in raw_list}
        with open("mf_database.json", "w") as f:
            json.dump(fund_dict, f)
        return fund_dict
        
    st.cache_data.clear()
    return {}

fund_dict = load_fund_choices()

# --- 2. DYNAMIC TOP NAVIGATION BAR ---
col_ex, col_srch, col_emp = st.columns([1, 2, 1])
with col_ex:
    market = st.selectbox("🌍 Select Market", ["India (NSE)", "India (BSE)", "US (NASDAQ/NYSE)", "Mutual Funds (India)"])

with col_srch:
    if market == "Mutual Funds (India)":
        search_query = st.multiselect("🔍 Search & Compare up to 5 Funds", options=list(fund_dict.keys()), max_selections=5)
    else:
        search_query = st.text_input("🔍 Search Company Name or Ticker (e.g., Wipro, ITC, Apple, AAPL)")

st.divider()

# --- 3. MUTUAL FUND WORLD (THE SPLIT) ---
if market == "Mutual Funds (India)" and search_query:
    with st.status("⚙️ Running Quantitative Models...", expanded=True) as status:
        all_fund_data = {}
        all_metrics = {}
        all_meta = {} 
        
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
        
        longest_fund_name = max(all_fund_data, key=lambda k: len(all_fund_data[k]))
        bench_data = all_fund_data[longest_fund_name]['Benchmark_Close']
        normalized_bench = (bench_data / bench_data.iloc[0]) * 10000
        fig.add_trace(go.Scatter(x=normalized_bench.index, y=normalized_bench, mode='lines', name='NIFTY 50 (Benchmark)', line=dict(color='gray', width=2, dash='dot')))
        
        colors = ['#2ab7ca', '#fe4a90', '#ffcc00', '#00ffaa', '#b366ff']
        for i, (name, df) in enumerate(all_fund_data.items()):
            normalized_nav = (df['MF_NAV'] / df['MF_NAV'].iloc[0]) * 10000
            short_name = name[:40] + "..." if len(name) > 40 else name
            fig.add_trace(go.Scatter(x=normalized_nav.index, y=normalized_nav, mode='lines', name=short_name, line=dict(color=colors[i % len(colors)], width=2)))

        fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0), hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### 📊 Institutional Quantitative Analysis")
        cols = st.columns(len(all_metrics))
        
        for idx, (name, metrics) in enumerate(all_metrics.items()):
            with cols[idx]:
                with st.container(border=True):
                    st.write(f"#### {name[:35]}")
                    
                    score = metrics.get('RayTurnz Score', 5.0)
                    if score >= 8: st.success(f"🏆 RayTurnz Score: {score:.1f} / 10")
                    elif score >= 5: st.warning(f"⚖️ RayTurnz Score: {score:.1f} / 10")
                    else: st.error(f"⚠️ RayTurnz Score: {score:.1f} / 10")
                    
                    with st.expander("📋 Fund Fundamentals & Fees"):
                        meta = all_meta[name]
                        for k, v in meta.items():
                            st.write(f"**{k}:** {v}")
                    st.divider()
                    
                    st.write("**Absolute Returns (Trailing)**")
                    t1, t2, t3 = st.columns(3)
                    t_ret = metrics.get('Trailing Returns', {})
                    
                    y1 = f"{t_ret.get('1Y')*100:.1f}%" if t_ret.get('1Y') else "N/A"
                    y3 = f"{t_ret.get('3Y')*100:.1f}%" if t_ret.get('3Y') else "N/A"
                    y5 = f"{t_ret.get('5Y')*100:.1f}%" if t_ret.get('5Y') else "N/A"
                    
                    with t1: draw_glass_card("1 Year", y1)
                    with t2: draw_glass_card("3 Year", y3)
                    with t3: draw_glass_card("5 Year", y5)

                    st.write("**Risk & Outperformance**")
                    draw_glass_card("Jensen's Alpha", f"{metrics.get('Alpha', 0)*100:.2f}%", "Skill over benchmark")
                    draw_glass_card("Market Beta", f"{metrics.get('Beta', 1):.2f}", "Sensitivity to market")
                    draw_glass_card("Sharpe Ratio", f"{metrics.get('Sharpe Ratio', 0):.2f}", "Risk-adjusted return")

                    st.write("**Institutional Downside Analysis**")
                    draw_glass_card("Max Drawdown", f"{metrics.get('Max Drawdown', 0)*100:.1f}%", "Worst historical crash", "#ff4b4b")
                    draw_glass_card("Sortino Ratio", f"{metrics.get('Sortino Ratio', 0):.2f}", "Downside risk efficiency")
                    st.caption(f"📈 Up Capture: {metrics.get('Up Capture', 100):.1f}% | 📉 Down Capture: {metrics.get('Down Capture', 100):.1f}%")

        st.divider()
        st.subheader("🤖 RayTurnz AI Wealth Advisor")
        with st.spinner("Analyzing quantitative metrics and drafting final verdict..."):
            ai_verdict = data_engine.generate_mf_verdict(all_metrics, all_meta)
            with st.container(border=True):
                st.markdown(ai_verdict)

    st.stop()


# --- 4. STOCK WORLD ---
if search_query:
    with st.status("⚡ Initializing RayTurnz AI Engine...", expanded=True) as status:
        st.write("🔍 Resolving company name...")
        raw_ticker = data_engine.resolve_ticker(search_query, market)
        st.write(f"✅ Auto-detected Ticker: **{raw_ticker}**")
        
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
        c_price, trend, m_return, pos, zone = data_engine.get_header_metrics(info, hist)

        col_name, col_price = st.columns([3, 1])
        with col_name:
            st.header(f"🏢 {info.get('longName', 'Company Name')} ({ticker_input})")
        with col_price:
            p_color = "#2ab7ca" if m_return >= 0 else "#ff4b4b"
            draw_glass_card("Current Price", f"{info.get('currency', 'INR')} {c_price:.2f}", f"{m_return:.2f}% (1M)", p_color)

        # Red Flags Block
        red_flags = data_engine.get_red_flags(info)
        red_flags_text = "None"
        
        if not red_flags:
            st.success("✅ **System Scan:** No major fundamental red flags detected.")
        else:
            st.error(f"⚠️ **Risk Alert:** The system detected {len(red_flags)} major red flags.")
            red_flags_text = ", ".join([f"{f[0]} ({f[1]})" for f in red_flags])
            
            cols_per_row = 4
            for i in range(0, len(red_flags), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(red_flags):
                        with cols[j]:
                            # Native styling handles Dark/Light Mode adaptiveness automatically
                            with st.container(border=True):
                                f_name, f_val = red_flags[i + j]
                                st.markdown(f'<p style="font-size: 14px; color: gray; margin-bottom: 0px; font-weight: 600; line-height: 1;">{f_name}</p>', unsafe_allow_html=True)
                                st.markdown(f'## {f_val}')
                                st.markdown(f'<p style="font-size: 14px; color: #ff4b4b; margin-top: -10px; font-weight: 500;">↑ Negative Indicator</p>', unsafe_allow_html=True)

        st.divider()

        if not hist.empty:
            latest = hist.iloc[-1]
            c_rsi, c_macd = latest['RSI'], latest['MACD']
        else:
            latest = None
            c_rsi, c_macd = None, None

        # --- MODERN WEBSITE NAVIGATION BAR ---
        # --- MODERN WEBSITE NAVIGATION BAR ---
        selected_tab = option_menu(
            menu_title=None, 
            options=["Overview", "Fundamentals", "Valuation", "Advanced Metrics", "AI Support", "Holdings", "News"], 
            icons=["activity", "briefcase", "cash-coin", "calculator", "robot", "bank", "newspaper"], 
            default_index=0, 
            orientation="horizontal",
            styles={
                "container": {
                    "padding": "8px!important", 
                    "background-color": "rgba(128, 128, 128, 0.08)", 
                    "border-radius": "15px", 
                    "margin-bottom": "25px",
                    "border": "1px solid rgba(128, 128, 128, 0.1)"
                },
                "icon": {
                    "font-size": "18px", # Larger icons
                }, 
                "nav-link": {
                    "font-size": "16px", # Larger text
                    "text-align": "center", 
                    "margin": "0px 5px", # Adds space between the tabs
                    "padding": "12px 15px", # Makes the tabs thicker and more clickable
                    "color": "gray", 
                    "font-weight": "700",
                    "border-radius": "10px", # Rounds the individual buttons
                    "--hover-color": "rgba(128, 128, 128, 0.15)", # Subtle hover effect
                    "transition": "all 0.2s ease-in-out"
                },
                "nav-link-selected": {
                    "background-color": "#2ab7ca", # Solid teal background
                    "color": "white", # Forces white text on the active tab
                    "font-weight": "800",
                    "box-shadow": "0 4px 15px rgba(42, 183, 202, 0.4)" # Adds a premium glow effect
                },
            }
        )

        if selected_tab == "Overview":
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
                        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
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

        elif selected_tab == "Fundamentals":
            st.write("### 💰 Deep Valuation & Intrinsic Math")
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            dcf_value, dcf_delta, dcf_color = data_engine.calculate_intrinsic_value(info, current_price)
            
            val_data = data_engine.get_valuation(info)
            trailing_pe = val_data.get("Trailing P/E", "N/A")
            forward_pe = val_data.get("Forward P/E", "N/A")
            peg = val_data.get("PEG Ratio", "N/A")

            val_col1, val_col2, val_col3, val_col4 = st.columns(4)
            with val_col1:
                dcf_hex = "#2ab7ca" if "Undervalued" in dcf_delta else "#ff4b4b" if "Overvalued" in dcf_delta else "gray"
                draw_glass_card("Intrinsic Value (DCF)", dcf_value, dcf_delta, dcf_hex)
            with val_col2:
                draw_glass_card("Trailing P/E", trailing_pe)
            with val_col3:
                draw_glass_card("Forward P/E", forward_pe)
            with val_col4:
                draw_glass_card("PEG Ratio", peg)
                
            st.divider()
                
            col_f1, col_f2 = st.columns(2)
            
            def render_fundamental_card(title, data_dict, hero_key):
                with st.container(border=True):
                    st.write(f"#### {title}")
                    if hero_key in data_dict:
                        draw_glass_card(hero_key, str(data_dict[hero_key]))
                    for k, v in data_dict.items():
                        if k != hero_key:
                            col_lbl, col_val = st.columns([3, 2])
                            col_lbl.caption(k)
                            col_val.markdown(f"**{v}**")

            with col_f1:
                prof_data = data_engine.get_profitability(info)
                render_fundamental_card("📊 Profitability", prof_data, "Profit Margin")
                
            with col_f2:
                fin_data = data_engine.get_financial_strength(info)
                render_fundamental_card("🏦 Financial Strength", fin_data, "Current Ratio")
                
            st.divider()
            gro_data = data_engine.get_growth(info)
            render_fundamental_card("🚀 Growth Trajectory", gro_data, "Revenue Growth")

        elif selected_tab == "Advanced Metrics":
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
                        draw_glass_card("Implied ROE", f"{dupont['roe']*100:.2f}%")
                        
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
                        z_color = "#2ab7ca" if "Safe" in altman['zone'] else "#ff4b4b" if "Distress" in altman['zone'] else "#ffcc00"
                        draw_glass_card("Z-Score", f"{altman['score']:.2f}", altman['zone'], z_color)
                        
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
                        draw_glass_card("Levered Beta", f"{beta_data['levered']:.2f}")
                        
                        delta_beta = beta_data['unlevered'] - beta_data['levered']
                        draw_glass_card("Unlevered Beta", f"{beta_data['unlevered']:.2f}", f"{delta_beta:.2f} Debt Impact")
                        
                        st.write("**Inputs Used:**")
                        st.write(f"- **Effective Tax Rate (T):** {beta_data['tax_rate']*100:.1f}%")
                        st.write(f"- **Market D/E Ratio:** {beta_data['d_e_ratio']:.2f}x")
                        
                st.divider()
                with st.expander("📄 Verify Raw Financial Statements (Source Data)"):
                    col_raw1, col_raw2 = st.columns(2)
                    with col_raw1:
                        st.write("#### Income Statement")
                        st.dataframe(adv_metrics['raw_data']['income_statement'], use_container_width=True)
                    with col_raw2:
                        st.write("#### Balance Sheet")
                        st.dataframe(adv_metrics['raw_data']['balance_sheet'], use_container_width=True)
                
                st.divider()
                st.write("### 📈 Statistical Regression & CAPM Analysis")
                
                with st.spinner("Running statistical regression..."):
                    reg_data = data_engine.calculate_beta_regression(ticker_input, market)
                    
                if reg_data:
                    col_reg1, col_reg2 = st.columns(2)
                    beta = reg_data['beta']
                    se = reg_data['std_err']
                    r2 = reg_data['r_squared']
                    
                    with col_reg1:
                        with st.container(border=True):
                            st.write("#### Performance vs Market (Jensen's Alpha)")
                            st.latex(r"$$ \alpha = Intercept - \frac{R_f}{n}(1 - \beta) $$")
                            alpha = reg_data['jensens_alpha_ann'] * 100
                            a_color = "#2ab7ca" if alpha > 0 else "#ff4b4b"
                            draw_glass_card("Annualized Jensen's Alpha", f"{alpha:.2f}%", "Outperformed" if alpha > 0 else "Underperformed", a_color)
                            
                        with st.container(border=True):
                            st.write("#### Risk Decomposition ($R^2$)")
                            st.write(f"**Market Risk (Systematic):** {r2 * 100:.1f}%")
                            st.write(f"**Firm-Specific Risk (Idiosyncratic):** {(1 - r2) * 100:.1f}%")
                            
                    with col_reg2:
                        with st.container(border=True):
                            st.write("#### Beta Estimate Ranges")
                            st.write(f"**Historical Beta:** {beta:.2f}")
                            st.write(f"**67% Probability Range:** {(beta - se):.2f} to {(beta + se):.2f}")
                            st.write(f"**95% Probability Range:** {(beta - 2*se):.2f} to {(beta + 2*se):.2f}")
                            
                        with st.container(border=True):
                            st.write("#### Required Return (CAPM)")
                            st.latex(r"$$ E(R) = R_f + \beta \times Market Premium $$")
                            req_ret = reg_data['required_return'] * 100
                            draw_glass_card("Cost of Equity (Required Return)", f"{req_ret:.2f}%")
                            st.caption(f"Inputs: Risk-Free Rate = {reg_data['rf_rate']*100:.1f}%, Risk Premium = {reg_data['market_premium']*100:.1f}%")
                            
            else:
                st.info("Raw financial statements are currently unavailable for this ticker to calculate advanced metrics.")

        elif selected_tab == "Valuation":
            st.write("### 🧮 Multi-Stage Intrinsic Valuation Calculator")
            st.caption("Based on Aswath Damodaran's Free Cash Flow to Firm (FCFF) methodology. Adjust the assumptions below to see how the valuation changes dynamically.")
            
            with st.spinner("Extracting raw accounting statements to build model..."):
                # We use the master function we just built!
                adv_metrics = data_engine.get_advanced_metrics(ticker_input, info)
                
            if adv_metrics and adv_metrics.get("dcf_inputs", {}).get("success"):
                dcf_inputs = adv_metrics["dcf_inputs"]
                
                # 1. THE INTERACTIVE CALCULATOR (Assumptions)
                st.write("#### 1. Core Assumptions (Editable)")
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                
                # Safe clamping to prevent Streamlit slider crashes
                safe_wacc = max(1.0, min(dcf_inputs["wacc"]*100, 50.0))
                safe_growth = max(-50.0, min(dcf_inputs["expected_growth"]*100, 100.0))
                safe_reinv = max(-100.0, min(dcf_inputs["reinvestment_rate"]*100, 200.0))
                safe_term = max(0.0, min(dcf_inputs["rf_rate"]*100, 10.0))

                with col_i1:
                    user_wacc = st.number_input("Cost of Capital (WACC) %", min_value=1.0, max_value=50.0, value=float(safe_wacc), step=0.5) / 100
                with col_i2:
                    user_growth = st.number_input("Expected Growth (Y1-Y5) %", min_value=-50.0, max_value=100.0, value=float(safe_growth), step=0.5) / 100
                with col_i3:
                    user_reinv = st.number_input("Reinvestment Rate %", min_value=-100.0, max_value=200.0, value=float(safe_reinv), step=1.0) / 100
                with col_i4:
                    user_term_growth = st.number_input("Terminal Growth Rate %", min_value=0.0, max_value=10.0, value=float(safe_term), step=0.5) / 100

                # 2. RUNNING THE 10-YEAR MATH
                years = list(range(1, 11))
                ebit_t, reinv_t, fcff_t, pv_t = [], [], [], []
                
                curr_ebit = dcf_inputs["ebit_after_tax"]
                cum_discount = 1.0
                sum_pv = 0.0
                
                for year in years:
                    # High growth for first 5 years, linearly decaying to terminal growth by year 10
                    if year <= 5:
                        g = user_growth
                    else:
                        g = user_growth - ((user_growth - user_term_growth) / 5) * (year - 5)
                        
                    curr_ebit = curr_ebit * (1 + g)
                    ebit_t.append(curr_ebit)
                    
                    # Reinvestment
                    reinv = curr_ebit * user_reinv
                    reinv_t.append(reinv)
                    
                    # Free Cash Flow to Firm
                    fcff = curr_ebit - reinv
                    fcff_t.append(fcff)
                    
                    # Present Value
                    cum_discount = cum_discount * (1 + user_wacc)
                    pv = fcff / cum_discount
                    pv_t.append(pv)
                    sum_pv += pv
                    
                # Terminal Value Math
                term_roc = user_wacc # In stable growth, ROC approaches Cost of Capital
                term_reinv_rate = user_term_growth / term_roc if term_roc > 0 else 0
                term_ebit = ebit_t[-1] * (1 + user_term_growth)
                term_fcff = term_ebit * (1 - term_reinv_rate)
                
                terminal_value = term_fcff / (user_wacc - user_term_growth) if user_wacc > user_term_growth else 0
                pv_terminal = terminal_value / cum_discount if terminal_value > 0 else 0

                # 3. DISPLAY THE DAMODARAN TABLE
                st.write("#### 2. 10-Year Cash Flow Projection")
                df_dcf = pd.DataFrame({
                    "Year": years,
                    "EBIT(1-t)": ebit_t,
                    "Reinvestment": reinv_t,
                    "FCFF": fcff_t,
                    "Present Value": pv_t
                })
                
                # Format for display
                curr_sym = dcf_inputs["currency"]
                df_display = df_dcf.copy()
                for col in ["EBIT(1-t)", "Reinvestment", "FCFF", "Present Value"]:
                    df_display[col] = df_display[col].apply(lambda x: f"{curr_sym} {x:,.0f}")
                
                st.dataframe(df_display.set_index("Year"), use_container_width=True)

                # 4. THE FINAL BRIDGE (Enterprise to Equity)
                st.write("#### 3. Valuation Bridge")
                col_b1, col_b2 = st.columns([1, 1])
                
                with col_b1:
                    with st.container(border=True):
                        st.markdown(f"**PV of FCFF (Years 1-10):** {curr_sym} {sum_pv:,.0f}")
                        st.markdown(f"**PV of Terminal Value:** {curr_sym} {pv_terminal:,.0f}")
                        st.divider()
                        value_op_assets = sum_pv + pv_terminal
                        st.markdown(f"#### Value of Operating Assets: {curr_sym} {value_op_assets:,.0f}")
                
                with col_b2:
                    with st.container(border=True):
                        st.markdown(f"**(+) Cash & Equivalents:** {curr_sym} {dcf_inputs['cash']:,.0f}")
                        st.markdown(f"**(-) Total Debt:** {curr_sym} {dcf_inputs['total_debt']:,.0f}")
                        st.markdown(f"**(-) Minority Interest:** {curr_sym} {dcf_inputs['minority_int']:,.0f}")
                        st.divider()
                        value_equity = value_op_assets + dcf_inputs['cash'] - dcf_inputs['total_debt'] - dcf_inputs['minority_int']
                        st.markdown(f"#### Value of Equity: {curr_sym} {value_equity:,.0f}")
                        
                # 5. THE FINAL VERDICT
                value_per_share = value_equity / dcf_inputs["shares"] if dcf_inputs["shares"] > 0 else 0
                current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                
                st.write("### 🎯 Final Intrinsic Value")
                col_v1, col_v2, col_v3 = st.columns(3)
                
                with col_v1:
                    draw_glass_card("Calculated Value / Share", f"{curr_sym} {value_per_share:,.2f}")
                with col_v2:
                    draw_glass_card("Current Market Price", f"{curr_sym} {current_price:,.2f}")
                with col_v3:
                    if current_price > 0 and value_per_share > 0:
                        upside = ((value_per_share - current_price) / current_price) * 100
                        if upside > 0:
                            draw_glass_card("Valuation Gap", f"Undervalued by {upside:.1f}%", "", "#2ab7ca")
                        else:
                            draw_glass_card("Valuation Gap", f"Overvalued by {abs(upside):.1f}%", "", "#ff4b4b")
                    else:
                        draw_glass_card("Valuation Gap", "N/A")

                # 👇 NEW: ACADEMIC METHODOLOGY DISCLAIMER 👇
                st.divider()
                st.markdown("""
                <div style="font-size: 12px; color: gray; line-height: 1.5; padding: 10px; background-color: rgba(128, 128, 128, 0.05); border-radius: 8px;">
                <b>* Methodology Notes:</b><br>
                1. <b>Cost of Debt:</b> Estimated at a flat 8% borrowing rate rather than dynamically pulled from corporate credit/bond ratings.<br>
                2. <b>Constant WACC:</b> Cost of Capital (WACC) is held constant across the 10-year projection to maintain interactive slider stability, rather than gradually decaying to a mature rate.<br>
                3. <b>Options Dilution:</b> Final Equity Value is divided directly by Outstanding Shares without subtracting the theoretical value of unexercised Employee Stock Options (options pool data is restricted).
                </div>
                """, unsafe_allow_html=True)

            else:
                st.error("🚨 **Valuation Failed:** This company either has negative operating income (EBIT) or missing raw financial statements...")

        elif selected_tab == "AI Support":
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
            col_ta1, col_ta2, col_ta3 = st.columns(3)
            with col_ta1:
                rsi_status = "Neutral"
                r_color = "gray"
                if c_rsi is not None and not pd.isna(c_rsi):
                    if c_rsi > 70: rsi_status, r_color = "Overbought ⚠️", "#ff4b4b"
                    elif c_rsi < 30: rsi_status, r_color = "Oversold 🟢", "#2ab7ca"
                draw_glass_card("Current RSI (14-Day)", f"{c_rsi:.2f}" if c_rsi is not None and not pd.isna(c_rsi) else "N/A", rsi_status, r_color)
            with col_ta2:
                draw_glass_card("Current MACD", f"{c_macd:.2f}" if c_macd is not None and not pd.isna(c_macd) else "N/A")
            with col_ta3:
                draw_glass_card("Current 52-Week Zone", zone)

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
                        draw_glass_card("Accuracy", backtest_data['daily']['accuracy'])
                        c_day = "#2ab7ca" if backtest_data['daily']['beat'] else "#ff4b4b"
                        draw_glass_card("Strategy Return", backtest_data['daily']['return'], "Beat Market" if backtest_data['daily']['beat'] else "Underperformed", c_day)
                with col_b2:
                    with st.container(border=True):
                        st.write("**Weekly Strategy Test**")
                        draw_glass_card("Accuracy", backtest_data['weekly']['accuracy'])
                        c_wk = "#2ab7ca" if backtest_data['weekly']['beat'] else "#ff4b4b"
                        draw_glass_card("Strategy Return", backtest_data['weekly']['return'], "Beat Market" if backtest_data['weekly']['beat'] else "Underperformed", c_wk)
                
                try:
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

        elif selected_tab == "Holdings":
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
                    fig_mf.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Percentage of Company Owned", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
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
                    fig_inst.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Percentage of Company Owned", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    if val_col in ['pctHeld', '% Out']:
                        fig_inst.update_layout(xaxis_tickformat=".2%")
                        
                    st.plotly_chart(fig_inst, use_container_width=True)
                else:
                    st.info("No Institutional holding data available for this specific stock on Yahoo Finance.")

        elif selected_tab == "News":
            st.write("### 📰 Multi-API Live News & AI Consensus")
            st.caption(f"Cross-verifying Yahoo, NewsData, GNews, and StockData for {ticker_input}.")
            
            with st.spinner("Fetching data from all endpoints..."):
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
            
            st.info("🧠 **Information Asymmetry Check:** Let AI cross-verify all sources for a consensus verdict.")
            if st.button("✨ Generate Master AI Consensus Report", type="primary", use_container_width=True):
                with st.spinner("AI is analyzing and comparing all sources..."):
                    ai_summary = data_engine.analyze_consensus_sentiment(all_news_payload, ticker_input)
                    with st.container(border=True):
                        st.markdown(ai_summary)
            
            st.divider()

            st.write("### 🌐 Global News Terminal")
            col_y, col_g, col_n, col_s = st.columns(4)

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

            render_news_column(col_y, "Yahoo Finance", y_news, "💹")
            render_news_column(col_g, "Google News", g_news, "🔍")
            render_news_column(col_n, "NewsData.io", n_news, "📡")
            render_news_column(col_s, "StockData", s_news, "🏛️")