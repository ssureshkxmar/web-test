import streamlit as st
import scipy.io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os

# Set page config for a professional look
st.set_page_config(
    page_title="Advanced Cardiac Digital Twin",
    page_icon="❤",
    layout="wide",
)

# Custom CSS for high-fidelity clinical appearance
st.markdown("""
    <style>
    .main {
        background-color: #020617;
        color: #f8fafc;
    }
    [data-testid="stMetricValue"] {
        color: #00d1ff;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.5rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #94a3b8;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-size: 0.8rem !important;
    }
    .stPlotlyChart {
        background: rgba(0,0,0,0.5);
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.02em;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data():
    file_path = st.query_params.get("file", "results/latest_analysis.mat")
    if os.path.exists(file_path):
        return scipy.io.loadmat(file_path)
    return None

data = load_data()

st.title("❤ Advanced ECG Analysis Digital Twin")
st.markdown("Automated Signal Acquisition and HRV Analysis")

if data is not None:
    # Extract data with safety checks
    ecg = data['ECG'].flatten()
    bpm = float(data['bpm'].item()) if hasattr(data['bpm'], 'item') else float(data['bpm'])
    
    # Use pre-calculated rhythm data
    peaks = data['peaks'].flatten().tolist() if 'peaks' in data else []
    intervals = data['intervals'].flatten().tolist() if 'intervals' in data else []
    
    # Safe extraction of HRV
    val_hrv = data.get('hrv', 0.0)
    try:
        hrv = float(val_hrv.item()) if hasattr(val_hrv, 'item') else float(val_hrv)
    except:
        hrv = 0.0
        
    # Safe extraction of Affected Region
    try:
        ar_raw = data.get('affected_region', ['Unknown'])
        if isinstance(ar_raw, (np.ndarray, list)) and len(ar_raw) > 0:
            affected_region = str(ar_raw[0])
        else:
            affected_region = str(ar_raw)
    except:
        affected_region = "Analyzing..."
    
    duration = len(ecg) / 500  # assuming 500Hz
    
    # 4 Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg BPM", f"{bpm:.1f}")
    with col2:
        st.metric("Peaks Detected", len(peaks))
    with col3:
        st.metric("HRV (SDNN)", f"{hrv:.2f}", help="Standard Deviation of Normal-to-Normal Intervals")
    with col4:
        st.metric("Duration", f"{duration:.1f} s")
        
    st.divider()
    
    # New: Affected Region Highlight
    st.markdown(f"""
    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 30px;">
        <h3 style="color: #ef4444; margin:0;">DETECTED REGION OF INTEREST</h3>
        <h1 style="color: white; font-size: 3em; margin: 10px 0;">{affected_region.upper()}</h1>
        <p style="color: #cbd5e1;">Based on Clinical Lead Deviation Analysis</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Section 1: ECG Signal Tracing
    st.subheader("🟦 ECG Signal Tracing (Neural Extraction)")
    
    fig_signal = go.Figure()
    fig_signal.add_trace(go.Scatter(
        y=ecg, 
        mode='lines', 
        name='ECG Signal', 
        line=dict(color='#00d1ff', width=2)
    ))
    fig_signal.add_trace(go.Scatter(
        x=peaks, 
        y=ecg[peaks], 
        mode='markers', 
        name='R-Peaks',
        marker=dict(color='#ef4444', size=10, symbol='circle')
    ))
    fig_signal.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Amplitude (mV)")
    )
    st.plotly_chart(fig_signal, use_container_width=True)

    # Section 2 & 3: Tachogram and Distribution
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        st.subheader("⏱ R-R TACHOGRAM")
        fig_tach = go.Figure()
        if len(intervals) > 0:
            fig_tach.add_trace(go.Scatter(
                x=list(range(1, len(intervals) + 1)),
                y=intervals, 
                mode='lines+markers', 
                name='Intervals',
                line=dict(color='#facc15', width=3),
                marker=dict(size=10, color='#facc15', line=dict(width=1, color='white'))
            ))
        fig_tach.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=40, r=40, t=20, b=40),
            xaxis=dict(title="Beat Interval #", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(title="Interval (ms)", showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )
        st.plotly_chart(fig_tach, use_container_width=True)

    with row2_col2:
        st.subheader("📊 DISTRIBUTION OF INTERVALS")
        fig_hist = go.Figure()
        if len(intervals) > 0:
            fig_hist.add_trace(go.Histogram(
                x=intervals, 
                nbinsx=15, 
                marker_color='#00d1ff',
                opacity=0.8
            ))
        fig_hist.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=40, r=40, t=20, b=40),
            xaxis=dict(title="Interval Duration (ms)", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(title="Frequency count", showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )
        st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("Awaiting ECG Digital Twin Data... Initialize a scan to begin analysis.")
    st.image("https://img.icons8.com/wired/64/00d1ff/electrocardiogram.png", width=100)
