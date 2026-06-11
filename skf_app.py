import streamlit as st
import pandas as pd
import requests
import os
import random
import base64
from datetime import datetime
from dotenv import load_dotenv
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────────
# External feature metadata: label, unit, icon
# ─────────────────────────────────────────────
FEATURE_META = {
    'Light_Vehicle_Production_Index': {
        'label': 'LV Production Index',
        'unit': 'Index',
        'icon': '🏭',
        'color': '#4FC3F7',
        'description': 'Global light-vehicle production activity index (base=100)'
    },
    'EV_Hybrid_Penetration_Pct': {
        'label': 'EV/Hybrid Penetration',
        'unit': '%',
        'icon': '⚡',
        'color': '#B39DDB',
        'description': 'Share of EV + Hybrid vehicles in total new registrations'
    },
    'GDP_Growth_Pct': {
        'label': 'GDP Growth',
        'unit': '%',
        'icon': '📈',
        'color': '#80CBC4',
        'description': 'Year-on-year GDP growth rate'
    },
    'Interest_Rate_Pct': {
        'label': 'Interest Rate',
        'unit': '%',
        'icon': '🏦',
        'color': '#BCAAA4',
        'description': 'Central bank benchmark interest rate'
    },
    'Steel_Price_Index': {
        'label': 'Steel Price Index',
        'unit': 'Index',
        'icon': '⚙️',
        'color': '#90CAF9',
        'description': 'Rolling steel commodity price index (base=100)'
    },
    'Energy_Logistics_Index': {
        'label': 'Energy & Logistics',
        'unit': 'Index',
        'icon': '🚚',
        'color': '#CE93D8',
        'description': 'Combined energy cost and logistics pressure index'
    },
}

NUMERIC_FEATURES = list(FEATURE_META.keys())

# ─────────────────────────────────────────────
# API Functions
# ─────────────────────────────────────────────

def predict_with_rpt(context_df, query_df):
    """Calls the RPT API to predict sales quantities based on the exogenous context."""

    api_token = os.getenv("RPT_API_TOKEN")
    if not api_token:
        st.error("API Token not found. Please set the RPT_API_TOKEN environment variable in a .env file.")
        return None, query_df

    url = "https://rpt.cloud.sap/api/predict"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    # --- Data Preparation ---
    context_df = context_df.copy()
    query_df = query_df.copy()

    cols_to_use = [
        'Month', 'OEM', 'Powertrain', 'Product_Category',
        'Light_Vehicle_Production_Index', 'EV_Hybrid_Penetration_Pct',
        'GDP_Growth_Pct', 'Interest_Rate_Pct', 'Steel_Price_Index',
        'Energy_Logistics_Index', 'Emission_Norms_Status',
        'OEM_Production_Status', 'Sales_Volume'
    ]

    context_df = context_df[cols_to_use] if not context_df.empty else pd.DataFrame(columns=cols_to_use)
    query_df = query_df[cols_to_use] if not query_df.empty else pd.DataFrame(columns=cols_to_use)

    if not context_df.empty:
        context_df['OEM'] = "Customer Segment: " + context_df['OEM'].astype(str)
        context_df['Powertrain'] = "Powertrain Type: " + context_df['Powertrain'].astype(str)
    if not query_df.empty:
        query_df['OEM'] = "Customer Segment: " + query_df['OEM'].astype(str)
        query_df['Powertrain'] = "Powertrain Type: " + query_df['Powertrain'].astype(str)

    context_rows = context_df.to_dict(orient='records') if not context_df.empty else []
    query_rows   = query_df.to_dict(orient='records')   if not query_df.empty   else []

    st.subheader("Data Preview & Debugging")
    with st.expander("Show Historical Data (Context) Sent to Model"):
        st.dataframe(context_df.sort_values(by=['Month', 'Product_Category']))

    payload = {"rows": context_rows + query_rows}
    with st.expander("Show Raw API Payload (JSON)"):
        st.json(payload)

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        return response.json(), query_df
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Failed: {e}")
        if e.response is not None:
            try:
                st.error("Server Response Details:")
                st.json(e.response.json())
            except Exception:
                st.warning("Server returned non-JSON error page:")
                st.code(e.response.text[:1000])
        return None, query_df


# ─────────────────────────────────────────────
# Correlation Insights Helper
# ─────────────────────────────────────────────

def get_correlation_ranking(hist_df):
    """Compute Pearson correlations of numeric external features with Sales_Volume."""
    corrs = {}
    for feat in NUMERIC_FEATURES:
        if feat in hist_df.columns and hist_df[feat].nunique() > 1:
            corr_val = hist_df[feat].astype(float).corr(hist_df['Sales_Volume'].astype(float))
            corrs[feat] = round(corr_val, 3)
    ranked = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    return ranked  # list of (feature, corr) sorted by |corr| desc


def render_correlation_section(hist_df, oem, pt, cat):
    """Render the full External Drivers & Correlation Insights panel."""

    st.markdown("---")
    st.header("📊 External Drivers & Correlation Insights")
    st.markdown(
        f"Analyzing how macro-economic and industry signals correlate with **{cat}** "
        f"sales for **{oem}** · **{pt}** powertrain across the 2025 dataset."
    )

    ranked = get_correlation_ranking(hist_df)

    if not ranked:
        st.warning("Not enough data to compute correlations for the selected variant.")
        return


    # ── 1. Dual-Axis Time-Series Overlay ───────────────────────────────────────
    st.subheader("📅 Sales vs. External Drivers Over Time")


    top_feat, top_corr = ranked[0]
    top_meta = FEATURE_META.get(top_feat, {'label': top_feat, 'color': '#4FC3F7', 'unit': '', 'icon': '📌'})

    second_feat_options = [f for f, _ in ranked]
    default_idx = 0
    sel_feat = st.selectbox(
        "Choose external feature to overlay with Sales Volume:",
        options=second_feat_options,
        format_func=lambda f: f"{FEATURE_META.get(f, {'icon':'📌','label':f})['icon']}  {FEATURE_META.get(f, {'label':f})['label']}",
        index=default_idx,
        key="feat_overlay_select"
    )
    sel_meta = FEATURE_META.get(sel_feat, {'label': sel_feat, 'color': '#4FC3F7', 'unit': ''})
    sel_corr = dict(ranked).get(sel_feat, 0.0)

    hist_sorted = hist_df.sort_values('Month')

    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

    # Sales volume - primary axis
    fig_dual.add_trace(
        go.Scatter(
            x=hist_sorted['Month'],
            y=hist_sorted['Sales_Volume'],
            name='Sales Volume',
            mode='lines+markers',
            line=dict(color='#4FC3F7', width=2.5),
            marker=dict(size=6),
            hovertemplate='Month: %{x}<br>Sales: %{y:,.0f} units<extra></extra>'
        ),
        secondary_y=False
    )

    # External feature - secondary axis
    fig_dual.add_trace(
        go.Scatter(
            x=hist_sorted['Month'],
            y=hist_sorted[sel_feat].astype(float),
            name=sel_meta['label'],
            mode='lines+markers',
            line=dict(color=sel_meta['color'], width=2, dash='dot'),
            marker=dict(size=5, symbol='diamond'),
            hovertemplate=f"Month: %{{x}}<br>{sel_meta['label']}: %{{y:.2f}} {sel_meta['unit']}<extra></extra>"
        ),
        secondary_y=True
    )

    direction_str = "positively" if sel_corr >= 0 else "negatively"
    fig_dual.update_layout(
        template='plotly_dark',
        height=420,
        title=dict(
            text=f"Sales Volume vs. {sel_meta['label']}  |  r = {sel_corr:+.3f} (correlated {direction_str})",
            font=dict(size=14)
        ),
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        margin=dict(l=10, r=10, t=60, b=40)
    )
    fig_dual.update_yaxes(title_text="Sales Volume (Units)", secondary_y=False,
                          gridcolor='#2a2a2a', color='#4FC3F7')
    fig_dual.update_yaxes(title_text=f"{sel_meta['label']} ({sel_meta['unit']})", secondary_y=True,
                          gridcolor='#2a2a2a', color=sel_meta['color'], showgrid=False)
    fig_dual.update_xaxes(title_text="Month", gridcolor='#2a2a2a')

    st.plotly_chart(fig_dual, use_container_width=True)


    # ── 5. Key Insight Text Box ────────────────────────────────────────────────
    top3 = ranked[:3]
    insight_parts = []
    for feat, corr in top3:
        m = FEATURE_META.get(feat, {'icon': '📌', 'label': feat})
        direction = "increases" if corr >= 0 else "decreases"
        insight_parts.append(f"{m['icon']} **{m['label']}** {direction} ({corr:+.3f})")

    st.info(
        f"**🧠 AI Insight for {cat} ({oem} · {pt}):** "
        f"The strongest drivers of sales are: {', '.join(insight_parts)}. "
        f"These signals are fed directly into the SAP RPT model as causal regressors, "
        f"allowing the AI to account for real-world market conditions in its forecast."
    )


# ─────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────

st.set_page_config(layout="wide", page_title="SKF AI Forecaster")

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_b64 = get_base64_image("bearing_image.png")
if img_b64:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_b64}" width="150" style="margin-right: 10px;" />
            <h1 style="margin: 0; padding: 0;">SKF Vertevo Demand Forecaster (RPT Demo)</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.title("SKF Vertevo Demand Forecaster (RPT Demo)")

@st.cache_data
def load_data(filepath="skf_sample_data_v3_variations.csv"):
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        # Shift all historical dates so the dataset ends on the PREVIOUS month
        df['Month'] = pd.to_datetime(df['Month'])
        max_date = df['Month'].max()
        target_last_date = pd.to_datetime(datetime.now().strftime('%Y-%m-01')) - pd.DateOffset(months=1)
        month_diff = (target_last_date.year - max_date.year) * 12 + (target_last_date.month - max_date.month)
        if month_diff != 0:
            df['Month'] = df['Month'] + pd.DateOffset(months=month_diff)
        df['Month'] = df['Month'].dt.strftime('%Y-%m')
        return df
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("Missing expected dataset: skf_sample_data_v3_variations.csv")
    st.stop()

# ── Sidebar Filters ────────────────────────────────────────────────────────────
st.sidebar.header("Select Demographic Variant")
sorted_oems = sorted(df["OEM"].unique())
selected_oem = st.sidebar.selectbox("OEM Customer", sorted_oems)

if selected_oem:
    sorted_pts = sorted(df[df["OEM"] == selected_oem]["Powertrain"].unique())
    selected_pt = st.sidebar.selectbox("Powertrain Segment", sorted_pts)

    sorted_cats = sorted(df["Product_Category"].unique())
    selected_cat = st.sidebar.selectbox("Product Category", sorted_cats)

    # Filter the historical slice for this variant
    mask = (
        (df['OEM'] == selected_oem) &
        (df['Powertrain'] == selected_pt) &
        (df['Product_Category'] == selected_cat)
    )
    historical_data = df.loc[mask].copy().sort_values('Month')

    # ── Correlation Insights Section (always visible) ──────────────────────────
    if not historical_data.empty:
        render_correlation_section(historical_data, selected_oem, selected_pt, selected_cat)

    # ── Forecast Section ───────────────────────────────────────────────────────
    st.markdown("---")
    st.sidebar.header("Generate Future DataFrame")
    prediction_period = st.sidebar.selectbox(
        "Select Forecast Horizon",
        ("Next 1 Month", "Next 3 Months", "Next 6 Months")
    )

    ranked_feats = get_correlation_ranking(historical_data)
    forecast_feat_options = [f for f, _ in ranked_feats] if ranked_feats else NUMERIC_FEATURES
    forecast_plot_feat = st.sidebar.selectbox(
        "Feature to overlay with Forecast:",
        options=forecast_feat_options,
        format_func=lambda f: f"{FEATURE_META.get(f, {'icon':'📌','label':f})['icon']}  {FEATURE_META.get(f, {'label':f})['label']}"
    )

    if st.sidebar.button("Generate & Predict"):
        st.header(f"🚀 Future Demand Forecast for {selected_cat}")
        st.markdown(f"**Customer Variant:** {selected_oem} | **Powertrain Variant:** {selected_pt}")
        
        # Use the user-selected feature to visualize
        top_feat = forecast_plot_feat
        top_corr = dict(ranked_feats).get(top_feat, 0.0) if ranked_feats else 0
        top_meta = FEATURE_META.get(top_feat, {'label': top_feat, 'color': '#B39DDB', 'unit': ''})


        months_ahead = int(prediction_period.split(" ")[1])

        # Build Future Query DataFrame
        last_row  = historical_data.iloc[-1]
        
        # Start predictions seamlessly from the month after the historical data ends
        current_date = pd.to_datetime(last_row['Month'] + '-01') + pd.DateOffset(months=1)

        # Initialize base values for simulation
        sim_lv = float(last_row['Light_Vehicle_Production_Index'])
        sim_ev = float(last_row['EV_Hybrid_Penetration_Pct'])
        sim_gdp = float(last_row['GDP_Growth_Pct'])
        sim_int = float(last_row['Interest_Rate_Pct'])
        sim_steel = float(last_row['Steel_Price_Index'])
        sim_energy = float(last_row['Energy_Logistics_Index'])

        future_rows = []
        for i in range(months_ahead):
            future_date = (current_date + pd.DateOffset(months=i)).strftime('%Y-%m')
            
            # Apply random walk to simulate realistic market movement
            sim_lv *= (1 + random.uniform(-0.025, 0.025))
            sim_ev *= (1 + random.uniform(0.005, 0.035))  # Stronger upward bias for EV
            sim_gdp *= (1 + random.uniform(-0.015, 0.015))
            sim_int *= (1 + random.uniform(-0.025, 0.005))  # Stronger downward bias for rates
            sim_steel *= (1 + random.uniform(-0.04, 0.04))
            sim_energy *= (1 + random.uniform(-0.03, 0.03))

            future_row = {
                'Month': future_date,
                'OEM': selected_oem,
                'Powertrain': selected_pt,
                'Product_Category': selected_cat,
                'Light_Vehicle_Production_Index': round(sim_lv, 2),
                'EV_Hybrid_Penetration_Pct':      round(sim_ev, 2),
                'GDP_Growth_Pct':                  round(sim_gdp, 2),
                'Interest_Rate_Pct':               round(sim_int, 2),
                'Steel_Price_Index':               round(sim_steel, 2),
                'Energy_Logistics_Index':          round(sim_energy, 2),
                'Emission_Norms_Status':           last_row['Emission_Norms_Status'],
                'OEM_Production_Status':           'Normal Production',
                'Sales_Volume':                    '[PREDICT]'
            }
            future_rows.append(future_row)

        future_df = pd.DataFrame(future_rows)

        with st.spinner("Calling SAP Rapid Prompt Tuning (RPT) API..."):
            prediction_result, query_df = predict_with_rpt(historical_data, future_df)

        if prediction_result and 'predictions' in prediction_result.get('prediction', {}):
            st.success("✅ RPT Prediction successful!")
            preds = prediction_result['prediction']['predictions']

            # Map predictions back
            query_df['Sales_Volume'] = query_df['Sales_Volume'].astype(object)
            for i, p in enumerate(preds):
                pred_vol = p.get('Sales_Volume', [{'prediction': 0}])[0]['prediction']
                query_df.loc[i, 'Sales_Volume'] = round(float(pred_vol), 0)

            # Find the best correlated feature to plot on the secondary axis
            # Forecast + Historical Chart
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            hist_plot_df = historical_data.sort_values(by='Month')
            # Historical Sales Volume
            fig.add_trace(go.Scatter(
                x=hist_plot_df['Month'],
                y=hist_plot_df['Sales_Volume'],
                mode='lines+markers',
                name='Historical Context (Sales)',
                line=dict(color='#4FC3F7', width=2)
            ), secondary_y=False)

            connected_future_df = pd.concat(
                [pd.DataFrame([hist_plot_df.iloc[-1]]), query_df], ignore_index=True
            )
            # Future Forecast Sales Volume
            fig.add_trace(go.Scatter(
                x=connected_future_df['Month'],
                y=connected_future_df['Sales_Volume'].astype(float),
                mode='lines+markers',
                name='RPT Forecast (Sales)',
                line=dict(color='#BA68C8', dash='dash', width=3),
                marker=dict(size=9, symbol='star')
            ), secondary_y=False)

            # Historical External Feature
            fig.add_trace(go.Scatter(
                x=hist_plot_df['Month'],
                y=hist_plot_df[top_feat].astype(float),
                mode='lines+markers',
                name=f"Historical {top_meta['label']}",
                line=dict(color=top_meta['color'], width=1.5, dash='dot')
            ), secondary_y=True)

            # Future External Feature Projection
            fig.add_trace(go.Scatter(
                x=connected_future_df['Month'],
                y=connected_future_df[top_feat].astype(float),
                mode='lines+markers',
                name=f"Projected {top_meta['label']}",
                line=dict(color=top_meta['color'], width=2.5, dash='dot'),
                marker=dict(symbol='triangle-up')
            ), secondary_y=True)

            fig.update_layout(
                title=f"Sales Trajectory & External Driver: {selected_cat} vs {top_meta['label']} (r={top_corr:+.3f})",
                xaxis_title="Timeline",
                template='plotly_dark',
                hovermode='x unified',
                height=420,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e0e0'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            fig.update_yaxes(title_text="Sales Volume (Units)", secondary_y=False, color='#4FC3F7')
            fig.update_yaxes(title_text=f"{top_meta['label']} ({top_meta['unit']})", secondary_y=True, color=top_meta['color'], showgrid=False)

            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Tabular Forecast")
            st.dataframe(
                query_df[[
                    'Month', 'Product_Category', 'OEM', 'Powertrain',
                    'Sales_Volume', 'EV_Hybrid_Penetration_Pct', 'Steel_Price_Index'
                ]],
                use_container_width=True
            )
        else:
            st.warning(
                "API Call Failed or RPT_API_TOKEN is missing. "
                "Generating simulated mock UI rendering..."
            )
            st.dataframe(
                query_df[['Month', 'Product_Category', 'OEM', 'Powertrain', 'Sales_Volume']]
            )
