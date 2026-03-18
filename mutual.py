import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import data_engine 
import time

st.set_page_config(page_title="RayTurnz Mutual Fund Analyzer", layout="wide", page_icon="🏦")

# 👇 IMPORTING YOUR EXACT CSS FROM APP.PY 👇
st.markdown("""
<style>
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
    .bolt-title {
        background: -webkit-linear-gradient(45deg, #fe4a90, #2ab7ca);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5em; 
        margin-bottom: 0px;
        text-align: center; 
    }
    .bolt-subtitle {
        text-align: center; 
        font-size: 1.2em;
        color: gray;
        margin-bottom: 20px;
        font-weight: 600;
    }
    .bouncing-bg-container {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        z-index: 0; pointer-events: none; overflow: hidden; opacity: 0.2;
    }
    .bounce-x { animation: moveX 15s linear infinite alternate; position: absolute; }
    .bounce-y {
        animation: moveY 11s linear infinite alternate;
        font-family: monospace; font-size: 3rem; font-weight: 900;
        color: #fe4a90; white-space: nowrap;
    }
    @keyframes moveX { 0% { transform: translateX(0); } 100% { transform: translateX(calc(100vw - 600px)); } }
    @keyframes moveY { 0% { transform: translateY(0); } 100% { transform: translateY(calc(100vh - 100px)); } }
</style>
<div class="bouncing-bg-container"><div class="bounce-x"><div class="bounce-y">QUANTITATIVE ALPHA...</div></div></div>
""", unsafe_allow_html=True)

st.markdown('<p class="bolt-title">🏦 RayTurnz Mutual Fund Engine</p>', unsafe_allow_html=True)
st.markdown('<p class="bolt-subtitle">Compare, Analyze, and Find True Alpha</p>', unsafe_allow_html=True)
st.divider()

# --- 1. LOAD MASTER MUTUAL FUND LIST ---
@st.cache_data(ttl=86400)
def load_fund_choices():
    raw_list = data_engine.get_mf_list()
    # Create a dictionary mapping "Scheme Name" -> "Scheme Code"
    return {item['schemeName']: str(item['schemeCode']) for item in raw_list}

with st.spinner("📥 Downloading AMFI Master Mutual Fund Database..."):
    fund_dict = load_fund_choices()

if not fund_dict:
    st.error("Failed to load Mutual Fund list. Check your internet connection.")
    st.stop()

# --- 2. SEARCH AND COMPARE UI ---
st.write("### 🔍 Select Funds to Compare")
st.caption("You can select up to 3 mutual funds to compare against the NIFTY 50 benchmark.")

selected_names = st.multiselect(
    "Search by Fund Name (e.g., Parag Parikh, HDFC Small Cap)", 
    options=list(fund_dict.keys()),
    max_selections=3
)

if st.button("🚀 Run Deep Comparison", type="primary", disabled=len(selected_names)==0):
    with st.status("⚙️ Running Quantitative Models...", expanded=True) as status:
        
        all_fund_data = {}
        all_metrics = {}
        
        # --- 3. DATA FETCHING LOOP ---
        for name in selected_names:
            code = fund_dict[name]
            st.write(f"📡 Fetching lifetime history for: {name[:30]}...")
            
            merged_df, mf_name, msg = data_engine.get_mf_and_benchmark(code)
            
            if merged_df is not None:
                st.write(f"🧮 Calculating Alpha and Beta for {name[:30]}...")
                metrics = data_engine.calculate_mf_metrics(merged_df)
                
                all_fund_data[name] = merged_df
                all_metrics[name] = metrics
            else:
                st.error(f"Failed to fetch data for {name}: {msg}")
                
        status.update(label="Comparison Complete!", state="complete", expanded=False)

    # --- 4. THE DASHBOARD RESULTS ---
    if all_fund_data:
        st.divider()
        st.write("### 📈 Lifetime Growth Comparison (Rebased to ₹10,000)")
        st.caption("How much a ₹10,000 investment at the fund's inception would be worth today vs NIFTY 50.")
        
        # Build a unified chart
        fig = go.Figure()
        
        # We only need to plot the benchmark once. We will use the benchmark from the oldest fund.
        longest_fund_name = max(all_fund_data, key=lambda k: len(all_fund_data[k]))
        bench_data = all_fund_data[longest_fund_name]['Benchmark_Close']
        normalized_bench = (bench_data / bench_data.iloc[0]) * 10000
        fig.add_trace(go.Scatter(x=normalized_bench.index, y=normalized_bench, mode='lines', name='NIFTY 50 (Benchmark)', line=dict(color='white', width=2, dash='dot')))
        
        colors = ['#2ab7ca', '#fe4a90', '#ffcc00']
        
        for i, (name, df) in enumerate(all_fund_data.items()):
            # Normalize to 10,000
            normalized_nav = (df['MF_NAV'] / df['MF_NAV'].iloc[0]) * 10000
            
            # Shorten name for legend
            short_name = name[:40] + "..." if len(name) > 40 else name
            fig.add_trace(go.Scatter(x=normalized_nav.index, y=normalized_nav, mode='lines', name=short_name, line=dict(color=colors[i % len(colors)], width=2)))

        fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0), hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 5. THE QUANTITATIVE METRICS CARDS ---
        st.write("### 📊 Quantitative Fund Analysis")
        cols = st.columns(len(all_metrics))
        
        # Find the "Winner"
        best_fund = max(all_metrics, key=lambda k: all_metrics[k]['Sharpe Ratio'])
        
        for idx, (name, metrics) in enumerate(all_metrics.items()):
            with cols[idx]:
                with st.container(border=True):
                    # Crown the winner
                    if name == best_fund:
                        st.markdown("🏆 **RayTurnz Top Pick**")
                    else:
                        st.write("📈 **Fund Profile**")
                        
                    st.write(f"#### {name[:35]}")
                    st.caption(f"Analyzing {metrics['Years of Data']:.1f} years of historical data.")
                    st.divider()
                    
                    # CAGR Metric
                    cagr_val = metrics['CAGR'] * 100
                    bench_cagr_val = metrics['Benchmark CAGR'] * 100
                    st.metric("Compound Annual Growth (CAGR)", f"{cagr_val:.2f}%", f"{cagr_val - bench_cagr_val:.2f}% vs NIFTY 50")
                    
                    # Alpha & Beta row
                    st.write("**Risk & Outperformance**")
                    c1, c2 = st.columns(2)
                    
                    # Alpha: Higher is better
                    alpha = metrics['Alpha'] * 100
                    c1.metric("Jensen's Alpha", f"{alpha:.2f}%", help="The extra return generated by the manager above expected market returns.")
                    
                    # Beta: Around 1.0 is market risk. Lower means less volatile.
                    beta = metrics['Beta']
                    c2.metric("Market Beta", f"{beta:.2f}", help="1.0 = Market volatility. < 1.0 = Less risky. > 1.0 = More risky.")
                    
                    st.divider()
                    
                    # Sharpe Ratio
                    sharpe = metrics['Sharpe Ratio']
                    st.metric("Sharpe Ratio (Efficiency)", f"{sharpe:.2f}", help="Return generated per unit of risk. > 1.0 is Good, > 2.0 is Excellent.")