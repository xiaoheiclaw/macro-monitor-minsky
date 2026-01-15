"""
Indicator System Dashboard - Streamlit Web UI
==============================================

实时三层风险指标系统 Dashboard，包含：
1. 系统状态总览
2. Structure/Crack/Trend 三层详情
3. 历史趋势图表

Usage:
    streamlit run dashboard_app.py
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Path setup
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from system_orchestrator import SystemOrchestrator, FACTOR_NAMES, MODULE_NAMES
from core import FuelScore, CrackScore, TrendScore
from config import FUEL_WEIGHTS_IC, FUEL_WEIGHTS_AUC, STATE_MULTIPLIERS, CRACK_PENALTIES, TREND_PENALTIES

# ==============================================================================
# Factor Explanations (经济含义)
# ==============================================================================

FUEL_FACTOR_EXPLANATIONS = {
    'V1': '【企业短期债务占比】企业短债/总债务。高位=依赖滚动再融资，利率上升时脆弱',
    'V2': '【银行未保险存款】未保险存款/总存款。高位=储户挤兑风险（如SVB）',
    'V4': '【利息保障倍数ICR】EBIT/利息支出。低位=企业现金流无法覆盖利息，违约风险',
    'V5': '【家庭偿债比TDSP】(房贷+消费贷利息)/可支配收入。高位=家庭财务压力，消费萎缩',
    'V7': '【Shiller市盈率CAPE】股价/10年通胀调整后平均盈利。高位=估值泡沫，均值回归风险',
    'V8': '【保证金债务比率】券商保证金贷款/股市总市值。高位=杠杆过高，Margin Call风险',
}

CRACK_FACTOR_EXPLANATIONS = {
    'V1': '【短期债务ΔZ】企业短债占比的Z-score变化率。ΔZ>0.5σ=再融资依赖加速恶化',
    'V2': '【未保险存款ΔZ】银行未保险存款的Z-score变化率。ΔZ>0.5σ=挤兑风险快速累积',
    'V4': '【利息覆盖ΔZ】ICR的Z-score变化率(反向)。ΔZ>0.5σ=企业盈利恶化加速',
    'V5': '【家庭偿债ΔZ】TDSP的Z-score变化率。ΔZ>0.5σ=家庭财务压力急剧上升',
    'V7': '【CAPE估值ΔZ】Shiller P/E的Z-score变化率。ΔZ>0.5σ=估值泡沫加速膨胀',
    'V8': '【保证金ΔZ】Margin Debt的Z-score变化率。ΔZ>0.5σ=杠杆快速堆积',
}

TREND_MODULE_EXPLANATIONS = {
    'A': '【期权隐含波动】VIX(股市恐慌指数)、VIX Term Structure(期限结构倒挂=短期恐慌)、SKEW(尾部风险溢价)、MOVE(债市波动率)。综合反映市场对未来波动的预期',
    'B': '【货币市场利差】EFFR-SOFR(联邦基金vs担保隔夜利率)、GCF-IORB(回购利率vs准备金利率)。利差扩大=银行间流动性紧张，资金成本上升',
    'C': '【信用风险溢价】HY Spread(高收益债利差)、IG Spread(投资级债利差)、HY-IG差(信用质量分化)。利差扩大=违约预期上升，信用收缩',
    'D': '【ETF资金流向】LQD(投资级债ETF)流出=机构抛售债券、TLT(长期国债ETF)流入=避险需求。资金流向确认市场风险偏好变化',
}

# ==============================================================================
# Page Config
# ==============================================================================

st.set_page_config(
    page_title="Indicator System Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .state-normal { color: #4CAF50; }
    .state-cautious { color: #FFC107; }
    .state-defensive { color: #FF9800; }
    .state-crisis { color: #F44336; }
    .stMetric > div { background-color: #262730; border-radius: 5px; padding: 10px; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_state_color(state: str) -> str:
    """获取状态对应的颜色"""
    colors = {
        'NORMAL': '#4CAF50',      # Green
        'CAUTIOUS': '#FFC107',    # Yellow
        'DEFENSIVE': '#FF9800',   # Orange
        'CRISIS': '#F44336',      # Red
        'HOLD': '#4CAF50',
        'DE-RISK': '#FFC107',
        'HEDGE': '#FF9800',
        'EXIT': '#F44336',
        'CALM': '#4CAF50',
        'WATCH': '#FFC107',
        'ALERT': '#FF9800',
        'CRITICAL': '#F44336',
        'STABLE': '#4CAF50',
        'EARLY_CRACK': '#FFC107',
        'WIDENING_CRACK': '#FF9800',
        'BREAKING': '#F44336',
        'INSUFFICIENT_DATA': '#9E9E9E',
    }
    return colors.get(state, '#9E9E9E')


def make_gauge_chart(value: float, max_val: float, title: str,
                     thresholds: list = None) -> go.Figure:
    """创建仪表盘图表"""
    if thresholds is None:
        thresholds = [0.3, 0.6, 0.8]

    # 根据值确定颜色
    if value / max_val < thresholds[0]:
        bar_color = '#4CAF50'
    elif value / max_val < thresholds[1]:
        bar_color = '#FFC107'
    elif value / max_val < thresholds[2]:
        bar_color = '#FF9800'
    else:
        bar_color = '#F44336'

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, max_val], 'tickwidth': 1},
            'bar': {'color': bar_color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, max_val * thresholds[0]], 'color': 'rgba(76, 175, 80, 0.3)'},
                {'range': [max_val * thresholds[0], max_val * thresholds[1]], 'color': 'rgba(255, 193, 7, 0.3)'},
                {'range': [max_val * thresholds[1], max_val * thresholds[2]], 'color': 'rgba(255, 152, 0, 0.3)'},
                {'range': [max_val * thresholds[2], max_val], 'color': 'rgba(244, 67, 54, 0.3)'},
            ],
        }
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
    )
    return fig


def make_bar_chart(components: dict, title: str, max_val: float = 100,
                   explanations: dict = None) -> go.Figure:
    """创建因子条形图，带悬停解释"""
    if not components:
        return go.Figure()

    # 按权重排序
    sorted_items = sorted(components.items(), key=lambda x: -x[1].get('weight', 0))

    factors = [item[0] for item in sorted_items]
    values = [item[1].get('value', 0) for item in sorted_items]
    weights = [item[1].get('weight', 0) * 100 for item in sorted_items]
    names = [item[1].get('name', item[0]) for item in sorted_items]

    # 构建悬停文本（包含解释）
    hover_texts = []
    for f, v, w, n in zip(factors, values, weights, names):
        explanation = explanations.get(f, '') if explanations else ''
        hover_text = f"<b>{f} ({n})</b><br>"
        hover_text += f"Value: {v:.1f}<br>"
        hover_text += f"Weight: {w:.1f}%<br>"
        if explanation:
            hover_text += f"<br><i>{explanation}</i>"
        hover_texts.append(hover_text)

    # 根据值确定颜色
    colors = []
    for v in values:
        ratio = v / max_val if max_val > 0 else 0
        if ratio < 0.3:
            colors.append('#4CAF50')
        elif ratio < 0.6:
            colors.append('#FFC107')
        elif ratio < 0.8:
            colors.append('#FF9800')
        else:
            colors.append('#F44336')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[f"{f} ({n})" for f, n in zip(factors, names)],
        x=values,
        orientation='h',
        marker_color=colors,
        text=[f"{v:.1f} ({w:.1f}%)" for v, w in zip(values, weights)],
        textposition='auto',
        hovertext=hover_texts,
        hoverinfo='text',
    ))

    fig.update_layout(
        title=title,
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        xaxis={'range': [0, max_val], 'showgrid': True, 'gridcolor': 'rgba(255,255,255,0.1)'},
        yaxis={'showgrid': False},
    )
    return fig


def make_crack_bar_chart(components: dict, explanations: dict = None) -> go.Figure:
    """创建 Crack 因子条形图，带悬停解释"""
    if not components:
        return go.Figure()

    sorted_items = sorted(components.items(), key=lambda x: -x[1].get('weight', 0))

    factors = [item[0] for item in sorted_items]
    signals = [item[1].get('signal', 0) for item in sorted_items]
    weights = [item[1].get('weight', 0) * 100 for item in sorted_items]
    names = [item[1].get('name', item[0]) for item in sorted_items]

    # 构建悬停文本（包含解释）
    hover_texts = []
    for f, s, w, n in zip(factors, signals, weights, names):
        explanation = explanations.get(f, '') if explanations else ''
        hover_text = f"<b>{f} ({n})</b><br>"
        hover_text += f"ΔZ: {s:+.2f}σ<br>"
        hover_text += f"Weight: {w:.1f}%<br>"
        if explanation:
            hover_text += f"<br><i>{explanation}</i>"
        hover_texts.append(hover_text)

    # 根据信号强度确定颜色
    colors = []
    for s in signals:
        if s < 0.3:
            colors.append('#4CAF50')
        elif s < 0.5:
            colors.append('#FFC107')
        elif s < 1.0:
            colors.append('#FF9800')
        else:
            colors.append('#F44336')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[f"{f} ({n})" for f, n in zip(factors, names)],
        x=signals,
        orientation='h',
        marker_color=colors,
        text=[f"{s:+.2f}σ ({w:.1f}%)" for s, w in zip(signals, weights)],
        textposition='auto',
        hovertext=hover_texts,
        hoverinfo='text',
    ))

    # Calculate x-axis range to show both positive and negative values
    min_signal = min(signals) if signals else 0
    max_signal = max(signals) if signals else 2.0
    x_min = min(-0.5, min_signal - 0.2)  # Allow some padding for negative values
    x_max = max(2.0, max_signal + 0.2)

    fig.update_layout(
        title="Crack Components (ΔZ)",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        xaxis={'range': [x_min, x_max], 'showgrid': True, 'gridcolor': 'rgba(255,255,255,0.1)', 'title': 'σ'},
        yaxis={'showgrid': False},
    )
    return fig


def make_module_bar_chart(module_heat: dict, explanations: dict = None) -> go.Figure:
    """创建模块热度条形图，带悬停解释"""
    if not module_heat:
        return go.Figure()

    modules = list(module_heat.keys())
    heats = list(module_heat.values())
    names = [MODULE_NAMES.get(m, m) for m in modules]

    # 构建悬停文本（包含解释）
    hover_texts = []
    for m, h, n in zip(modules, heats, names):
        explanation = explanations.get(m, '') if explanations else ''
        hover_text = f"<b>Module {m} ({n})</b><br>"
        hover_text += f"Heat: {h:.2f}<br>"
        if explanation:
            hover_text += f"<br><i>{explanation}</i>"
        hover_texts.append(hover_text)

    colors = []
    for h in heats:
        if h < 0.3:
            colors.append('#4CAF50')
        elif h < 0.6:
            colors.append('#FFC107')
        elif h < 0.8:
            colors.append('#FF9800')
        else:
            colors.append('#F44336')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[f"{m} ({n})" for m, n in zip(modules, names)],
        x=heats,
        orientation='h',
        marker_color=colors,
        text=[f"{h:.2f}" for h in heats],
        textposition='outside',
        textfont=dict(color='white'),
        hovertext=hover_texts,
        hoverinfo='text',
    ))

    fig.update_layout(
        title="Module Heat (0-1)",
        height=250,
        margin=dict(l=10, r=50, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        xaxis={'range': [0, 1.0], 'showgrid': True, 'gridcolor': 'rgba(255,255,255,0.1)', 'title': 'Heat'},
        yaxis={'showgrid': False},
        bargap=0.3,
    )
    return fig


# ==============================================================================
# Cached Data Loading Functions
# ==============================================================================

@st.cache_data(ttl=300)
def get_system_status(use_lagged: bool = True) -> dict:
    """
    Compute and cache system status (5 minute TTL).

    Returns cached result to avoid recomputation on every page refresh.
    """
    orch = SystemOrchestrator(use_lagged=use_lagged, verbose=False)
    return orch.compute_portfolio_action()


@st.cache_data(ttl=300)
def get_system_status_v2(use_lagged: bool = True) -> dict:
    """
    Compute and cache v2 system status with rule engine (5 minute TTL).

    Returns:
        v2 output including triggered_rule, layered risk_budget, escalation_triggers
    """
    orch = SystemOrchestrator(use_lagged=use_lagged, verbose=False)
    return orch.compute_portfolio_action_v2()


@st.cache_data(ttl=300)
def get_fuel_comparison() -> dict:
    """Get cached IC vs AUC comparison for current values."""
    fuel = FuelScore()
    return fuel.compute_both_schemes()


@st.cache_data(ttl=3600)
def load_history_data(start_date: str = '2000-01-01', end_date: str = None) -> dict:
    """加载历史数据（缓存1小时）"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    history = {
        'fuel': None,
        'fuel_both': None,  # IC vs AUC comparison
        'crack': None,
        'trend': None,
        'spx': None,
    }

    # Load Trend history
    try:
        sys.path.insert(0, str(PROJECT_ROOT / 'trend'))
        from trend_score.trend_score import TrendScore
        ts = TrendScore()
        trend_history = ts.compute_history(start_date=start_date, end_date=end_date, freq='D')
        history['trend'] = trend_history
    except Exception as e:
        st.warning(f"Failed to load Trend history: {e}")

    # Load Fuel history - compute both IC and AUC schemes using new FuelScore module
    try:
        fuel = FuelScore()
        fuel_both_df = fuel.compute_history_both_schemes(start_date=start_date, end_date=end_date)
        history['fuel_both'] = fuel_both_df

        # Also set fuel for backward compatibility (use IC as default)
        if len(fuel_both_df) > 0:
            fuel_df = fuel_both_df[['fuel_score_ic']].copy()
            fuel_df.columns = ['fuel_score']
            history['fuel'] = fuel_df
    except Exception as e:
        st.warning(f"Failed to compute Fuel history: {e}")
        # Fallback to CSV if compute fails
        fuel_csv = PROJECT_ROOT / 'structure' / 'aggregation' / 'ic_return' / 'fuel_score_data.csv'
        if fuel_csv.exists():
            try:
                fuel_df = pd.read_csv(fuel_csv, index_col=0, parse_dates=True)
                fuel_df = fuel_df[(fuel_df.index >= start_date) & (fuel_df.index <= end_date)]
                history['fuel'] = fuel_df
            except Exception as e2:
                st.warning(f"Failed to load Fuel CSV fallback: {e2}")

    # Load Crack history (from saved CSV if available)
    crack_csv = PROJECT_ROOT / 'crack' / 'crack_score_data.csv'
    if crack_csv.exists():
        try:
            crack_df = pd.read_csv(crack_csv, index_col=0, parse_dates=True)
            # 过滤日期范围
            crack_df = crack_df[(crack_df.index >= start_date) & (crack_df.index <= end_date)]
            history['crack'] = crack_df
        except Exception as e:
            st.warning(f"Failed to load Crack history: {e}")

    # Load SPX (S&P 500) data
    try:
        import yfinance as yf
        spx = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
        if len(spx) > 0:
            spx_series = spx['Close'].squeeze()
            spx_series.index = pd.to_datetime(spx_series.index)
            history['spx'] = spx_series
    except Exception as e:
        st.warning(f"Failed to load SPX data: {e}")

    return history


def make_trend_history_chart(trend_df: pd.DataFrame, spx_series: pd.Series = None) -> go.Figure:
    """创建 TrendScore 历史图表（含 SPX 对照）"""
    if trend_df is None or len(trend_df) == 0:
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=('TrendScore History with S&P 500', 'State Distribution'),
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )

    # TrendScore line
    valid_data = trend_df[trend_df['trend_state'] != 'INSUFFICIENT_DATA'].copy()

    fig.add_trace(
        go.Scatter(
            x=valid_data.index,
            y=valid_data['trend_heat_score'],
            mode='lines',
            name='TrendScore',
            line=dict(color='#2196F3', width=1.5),
        ),
        row=1, col=1, secondary_y=False
    )

    # SPX on secondary axis
    if spx_series is not None and len(spx_series) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx_series.index,
                y=spx_series,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.6)', width=1, dash='dot'),
            ),
            row=1, col=1, secondary_y=True
        )

    # Add threshold lines
    thresholds = {'CRITICAL': 0.65, 'ALERT': 0.45, 'WATCH': 0.25}
    colors = {'CRITICAL': '#F44336', 'ALERT': '#FF9800', 'WATCH': '#FFC107'}
    for name, val in thresholds.items():
        fig.add_hline(y=val, line_dash="dash", line_color=colors[name],
                      annotation_text=name, row=1, col=1)

    # Crisis annotations
    crises = [
        ('2000-03-01', '2002-10-01', 'Dot-com'),
        ('2007-10-01', '2009-03-01', 'GFC'),
        ('2020-02-01', '2020-04-01', 'COVID'),
        ('2022-01-01', '2022-10-01', '2022 Bear'),
    ]
    for start, end, name in crises:
        if start >= str(valid_data.index.min())[:10]:
            fig.add_vrect(
                x0=start, x1=end,
                fillcolor="rgba(244, 67, 54, 0.1)",
                line_width=0,
                row=1, col=1
            )

    # State color bar
    state_colors = {
        'CALM': '#4CAF50',
        'WATCH': '#FFC107',
        'ALERT': '#FF9800',
        'CRITICAL': '#F44336',
        'INSUFFICIENT_DATA': '#9E9E9E',
    }

    for state, color in state_colors.items():
        state_data = trend_df[trend_df['trend_state'] == state]
        if len(state_data) > 0:
            fig.add_trace(
                go.Scatter(
                    x=state_data.index,
                    y=[state] * len(state_data),
                    mode='markers',
                    marker=dict(color=color, size=3),
                    name=state,
                    showlegend=False,
                ),
                row=2, col=1
            )

    fig.update_layout(
        height=500,
        margin=dict(l=10, r=60, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis2={'showgrid': True, 'gridcolor': 'rgba(255,255,255,0.1)'},
    )

    fig.update_yaxes(title_text="TrendScore", showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[0, 1], row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="S&P 500", showgrid=False, row=1, col=1, secondary_y=True)

    return fig


def make_fuel_history_chart(fuel_df: pd.DataFrame, spx_series: pd.Series = None) -> go.Figure:
    """创建 FuelScore 历史图表（含 SPX 对照）"""
    if fuel_df is None or len(fuel_df) == 0:
        return go.Figure()

    # 查找 fuel_score 列
    score_col = None
    for col in ['fuel_score', 'FuelScore', 'total_fuel']:
        if col in fuel_df.columns:
            score_col = col
            break

    if score_col is None:
        return go.Figure()

    # 使用次坐标轴
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 主轴：FuelScore
    fig.add_trace(
        go.Scatter(
            x=fuel_df.index,
            y=fuel_df[score_col],
            mode='lines',
            name='FuelScore',
            line=dict(color='#FF9800', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(255, 152, 0, 0.2)',
        ),
        secondary_y=False
    )

    # 次轴：SPX
    if spx_series is not None and len(spx_series) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx_series.index,
                y=spx_series,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.6)', width=1, dash='dot'),
            ),
            secondary_y=True
        )

    # Threshold lines
    fig.add_hline(y=80, line_dash="dash", line_color='#F44336', annotation_text='EXTREME HIGH', secondary_y=False)
    fig.add_hline(y=60, line_dash="dash", line_color='#FF9800', annotation_text='HIGH', secondary_y=False)
    fig.add_hline(y=40, line_dash="dash", line_color='#FFC107', annotation_text='NEUTRAL', secondary_y=False)
    fig.add_hline(y=20, line_dash="dash", line_color='#4CAF50', annotation_text='LOW', secondary_y=False)

    fig.update_layout(
        title='FuelScore History (0-100) with S&P 500',
        height=350,
        margin=dict(l=10, r=60, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )

    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="FuelScore", showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[0, 100], secondary_y=False)
    fig.update_yaxes(title_text="S&P 500", showgrid=False, secondary_y=True)

    return fig


def make_fuel_comparison_chart(fuel_both_df: pd.DataFrame, spx_series: pd.Series = None) -> go.Figure:
    """
    创建 FuelScore IC vs AUC 权重对比图

    Args:
        fuel_both_df: DataFrame with columns fuel_score_ic, fuel_score_auc
        spx_series: S&P 500 price series for overlay

    Returns:
        Plotly figure with IC (blue) and AUC (coral) FuelScore lines
    """
    if fuel_both_df is None or len(fuel_both_df) == 0:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # IC 权重 FuelScore (蓝色)
    if 'fuel_score_ic' in fuel_both_df.columns:
        fig.add_trace(
            go.Scatter(
                x=fuel_both_df.index,
                y=fuel_both_df['fuel_score_ic'],
                mode='lines',
                name='FuelScore (IC)',
                line=dict(color='steelblue', width=1.5),
            ),
            secondary_y=False
        )

    # AUC 权重 FuelScore (珊瑚色)
    if 'fuel_score_auc' in fuel_both_df.columns:
        fig.add_trace(
            go.Scatter(
                x=fuel_both_df.index,
                y=fuel_both_df['fuel_score_auc'],
                mode='lines',
                name='FuelScore (AUC)',
                line=dict(color='coral', width=1.5),
            ),
            secondary_y=False
        )

    # SPX 次坐标轴 (灰色虚线)
    if spx_series is not None and len(spx_series) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx_series.index,
                y=spx_series,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
            ),
            secondary_y=True
        )

    # Threshold lines
    fig.add_hline(y=80, line_dash="dash", line_color='rgba(244, 67, 54, 0.5)', annotation_text='EXTREME', secondary_y=False)
    fig.add_hline(y=60, line_dash="dash", line_color='rgba(255, 152, 0, 0.5)', annotation_text='HIGH', secondary_y=False)
    fig.add_hline(y=40, line_dash="dash", line_color='rgba(255, 193, 7, 0.5)', annotation_text='NEUTRAL', secondary_y=False)

    # Crisis annotations
    crises = [
        ('2000-03-01', '2002-10-01', 'Dot-com'),
        ('2007-10-01', '2009-03-01', 'GFC'),
        ('2020-02-01', '2020-04-01', 'COVID'),
        ('2022-01-01', '2022-10-01', '2022 Bear'),
    ]
    min_date = str(fuel_both_df.index.min())[:10] if len(fuel_both_df) > 0 else '2000-01-01'
    for start, end, name in crises:
        if start >= min_date:
            fig.add_vrect(
                x0=start, x1=end,
                fillcolor="rgba(244, 67, 54, 0.1)",
                line_width=0,
            )

    fig.update_layout(
        title='FuelScore Comparison: IC vs AUC Weights',
        height=400,
        margin=dict(l=10, r=60, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )

    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="FuelScore (0-100)", showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[0, 100], secondary_y=False)
    fig.update_yaxes(title_text="S&P 500", showgrid=False, secondary_y=True)

    return fig


def make_crack_history_chart(crack_df: pd.DataFrame, spx_series: pd.Series = None) -> go.Figure:
    """创建 CrackScore 历史图表（含 SPX 对照）"""
    if crack_df is None or len(crack_df) == 0:
        return go.Figure()

    # 查找 crack_score 列
    score_col = None
    for col in ['crack_score', 'CrackScore', 'total_crack']:
        if col in crack_df.columns:
            score_col = col
            break

    if score_col is None:
        return go.Figure()

    # 使用次坐标轴
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 主轴：CrackScore
    fig.add_trace(
        go.Scatter(
            x=crack_df.index,
            y=crack_df[score_col],
            mode='lines',
            name='CrackScore',
            line=dict(color='#9C27B0', width=1.5),
        ),
        secondary_y=False
    )

    # 次轴：SPX
    if spx_series is not None and len(spx_series) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx_series.index,
                y=spx_series,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.6)', width=1, dash='dot'),
            ),
            secondary_y=True
        )

    # Threshold lines
    fig.add_hline(y=1.0, line_dash="dash", line_color='#F44336', annotation_text='BREAKING', secondary_y=False)
    fig.add_hline(y=0.5, line_dash="dash", line_color='#FF9800', annotation_text='WIDENING', secondary_y=False)
    fig.add_hline(y=0.3, line_dash="dash", line_color='#FFC107', annotation_text='EARLY_CRACK', secondary_y=False)

    fig.update_layout(
        title='CrackScore History (σ) with S&P 500',
        height=350,
        margin=dict(l=10, r=60, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )

    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="CrackScore (σ)", showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[0, 2.5], secondary_y=False)
    fig.update_yaxes(title_text="S&P 500", showgrid=False, secondary_y=True)

    return fig


def make_combined_history_chart(history: dict) -> go.Figure:
    """创建三层组合历史图表（含 SPX 对照）- 顺序：Fuel → Crack → Trend"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.35, 0.35, 0.30],
        subplot_titles=('FuelScore (0-100) with S&P 500', 'CrackScore (σ) with S&P 500', 'TrendScore (0-1) with S&P 500'),
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]]
    )

    spx = history.get('spx')

    # Row 1: FuelScore
    if history.get('fuel') is not None:
        fuel_df = history['fuel']
        score_col = next((c for c in ['fuel_score', 'FuelScore', 'total_fuel'] if c in fuel_df.columns), None)
        if score_col:
            fig.add_trace(
                go.Scatter(
                    x=fuel_df.index,
                    y=fuel_df[score_col],
                    mode='lines',
                    name='FuelScore',
                    line=dict(color='#FF9800', width=1.2),
                ),
                row=1, col=1, secondary_y=False
            )

    # SPX for row 1
    if spx is not None and len(spx) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx.index,
                y=spx,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
                showlegend=True,
            ),
            row=1, col=1, secondary_y=True
        )

    # Row 2: CrackScore
    if history.get('crack') is not None:
        crack_df = history['crack']
        score_col = next((c for c in ['crack_score', 'CrackScore', 'total_crack'] if c in crack_df.columns), None)
        if score_col:
            fig.add_trace(
                go.Scatter(
                    x=crack_df.index,
                    y=crack_df[score_col],
                    mode='lines',
                    name='CrackScore',
                    line=dict(color='#9C27B0', width=1.2),
                ),
                row=2, col=1, secondary_y=False
            )

    # SPX for row 2
    if spx is not None and len(spx) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx.index,
                y=spx,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
                showlegend=False,
            ),
            row=2, col=1, secondary_y=True
        )

    # Row 3: TrendScore
    if history.get('trend') is not None:
        trend_df = history['trend']
        valid_data = trend_df[trend_df['trend_state'] != 'INSUFFICIENT_DATA']
        fig.add_trace(
            go.Scatter(
                x=valid_data.index,
                y=valid_data['trend_heat_score'],
                mode='lines',
                name='TrendScore',
                line=dict(color='#2196F3', width=1.2),
            ),
            row=3, col=1, secondary_y=False
        )

    # SPX for row 3
    if spx is not None and len(spx) > 0:
        fig.add_trace(
            go.Scatter(
                x=spx.index,
                y=spx,
                mode='lines',
                name='S&P 500',
                line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
                showlegend=False,
            ),
            row=3, col=1, secondary_y=True
        )

    # Crisis annotations
    crises = [
        ('2000-03-01', '2002-10-01', 'Dot-com'),
        ('2007-10-01', '2009-03-01', 'GFC'),
        ('2020-02-01', '2020-04-01', 'COVID'),
        ('2022-01-01', '2022-10-01', '2022'),
    ]
    for start, end, name in crises:
        for row in [1, 2, 3]:
            fig.add_vrect(
                x0=start, x1=end,
                fillcolor="rgba(244, 67, 54, 0.1)",
                line_width=0,
                row=row, col=1
            )

    fig.update_layout(
        height=700,
        margin=dict(l=10, r=60, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )

    # Update axes
    for i in range(1, 4):
        fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', row=i, col=1, secondary_y=False)
        fig.update_yaxes(showgrid=False, row=i, col=1, secondary_y=True)

    # Y-axis ranges: Row 1=FuelScore, Row 2=CrackScore, Row 3=TrendScore
    fig.update_yaxes(range=[0, 100], row=1, col=1, secondary_y=False)   # FuelScore
    fig.update_yaxes(range=[0, 2.5], row=2, col=1, secondary_y=False)   # CrackScore
    fig.update_yaxes(range=[0, 1], row=3, col=1, secondary_y=False)     # TrendScore

    return fig


# ==============================================================================
# Main App
# ==============================================================================

def main():
    # Sidebar
    with st.sidebar:
        st.title("Controls")

        # Data update button
        if st.button("🔄 Update All Data", use_container_width=True):
            with st.spinner("Updating data..."):
                orch = SystemOrchestrator(verbose=False)
                result = orch.update_all_data()
                st.success("Data updated!")
                st.json(result)

        st.divider()

        # Rule Engine Version Selection
        st.subheader("🔧 Rule Engine")
        use_v2 = st.toggle(
            "Use v2 Rule Engine",
            value=True,
            help="v2: 8条优先级规则 + 分层Risk Budget | v1: 静态状态表"
        )
        st.session_state['use_v2'] = use_v2

        st.divider()

        # Weight Scheme Selection
        st.subheader("⚙️ FuelScore Settings")
        weight_scheme = st.radio(
            "Weight Scheme",
            options=['ic', 'auc'],
            format_func=lambda x: 'IC (Return)' if x == 'ic' else 'AUC (MDD)',
            help="IC: Based on 12M return correlation | AUC: Based on MDD prediction"
        )
        st.session_state['weight_scheme'] = weight_scheme

        # Weight recalculation button
        if st.button("🔄 Recalculate Weights", use_container_width=True):
            with st.spinner("Recalculating IC/AUC weights..."):
                try:
                    from validation import WeightOptimizer
                    from data.loader import DataLoader
                    optimizer = WeightOptimizer(DataLoader())
                    ic_w = optimizer.compute_ic_weights()
                    auc_w = optimizer.compute_auc_weights()
                    report_path = optimizer.generate_report()
                    st.success(f"Weights recalculated! Report: {report_path}")
                    st.json({'IC Weights': ic_w, 'AUC Weights': auc_w})
                except Exception as e:
                    st.error(f"Failed to recalculate weights: {e}")

        st.divider()

        # Settings
        st.subheader("Settings")
        use_lagged = st.checkbox("Use Lagged Data", value=True,
                                  help="Use release-lag adjusted data for Structure/Crack layers")

        # 时间范围滑块
        st.subheader("Time Range")

        # 快捷按钮
        quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
        if quick_col1.button("1Y", use_container_width=True):
            st.session_state['history_start'] = datetime.now() - timedelta(days=365)
        if quick_col2.button("3Y", use_container_width=True):
            st.session_state['history_start'] = datetime.now() - timedelta(days=365*3)
        if quick_col3.button("5Y", use_container_width=True):
            st.session_state['history_start'] = datetime.now() - timedelta(days=365*5)
        if quick_col4.button("All", use_container_width=True):
            st.session_state['history_start'] = datetime(2000, 1, 1)

        # 获取默认值
        default_start = st.session_state.get('history_start', datetime(2015, 1, 1))
        default_end = datetime.now()

        # 日期选择器（替代slider，更可靠）
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            history_start = st.date_input(
                "Start Date",
                value=default_start,
                min_value=datetime(2000, 1, 1),
                max_value=datetime.now(),
                key="history_start_input"
            )
        with date_col2:
            history_end = st.date_input(
                "End Date",
                value=default_end,
                min_value=datetime(2000, 1, 1),
                max_value=datetime.now(),
                key="history_end_input"
            )

        # 转换为 datetime 对象
        history_start = datetime.combine(history_start, datetime.min.time())
        history_end = datetime.combine(history_end, datetime.min.time())

        st.divider()

        # About
        st.subheader("About")
        st.markdown("""
        **Indicator System v1.0**

        Three-layer risk monitoring:
        - **Structure**: Macro vulnerability (FuelScore)
        - **Crack**: Marginal deterioration (CrackScore)
        - **Trend**: Real-time pressure (TrendScore)
        """)

    # Main content
    st.title("📊 Indicator System Dashboard")
    st.caption(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load current data (cached for 5 minutes)
    use_v2 = st.session_state.get('use_v2', True)

    try:
        if use_v2:
            result = get_system_status_v2(use_lagged=use_lagged)
        else:
            result = get_system_status(use_lagged=use_lagged)
    except Exception as e:
        st.error(f"Failed to compute system output: {e}")
        return

    # ====================
    # System Status Row
    # ====================
    st.header("System Status")

    if use_v2:
        # v2: Display triggered rule and layered risk budget
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            state = result['system_state']
            state_color = get_state_color(state)
            st.metric(
                "System State",
                state,
                help="Overall system state: NORMAL/CAUTIOUS/DEFENSIVE/CRISIS"
            )

        with col2:
            action_info = result.get('action', {})
            action = action_info.get('posture', 'HOLD') if isinstance(action_info, dict) else action_info
            st.metric(
                "Action",
                action,
                help="Recommended action: HOLD/DE-RISK/HEDGE/EXIT"
            )

        with col3:
            risk_budget = result.get('risk_budget', {})
            final_rb = risk_budget.get('final_risk_budget', 0) if isinstance(risk_budget, dict) else risk_budget
            st.metric(
                "Risk Budget",
                f"{final_rb:.2f}",
                help="Layered risk budget: base × state_mult × crack_penalty × trend_penalty"
            )

        with col4:
            st.metric(
                "Confidence",
                result.get('confidence', 'N/A'),
                help="Data quality confidence: LOW/MEDIUM/HIGH"
            )

        # Triggered Rule (v2)
        triggered_rule = result.get('triggered_rule', {})
        rule_id = triggered_rule.get('rule_id', 'N/A')
        rule_name = triggered_rule.get('name', 'N/A')
        st.info(f"**Triggered Rule:** [{rule_id}] {rule_name}")

        # Risk Budget Breakdown (v2)
        if isinstance(risk_budget, dict) and 'base_from_fuel' in risk_budget:
            st.markdown("##### Risk Budget Breakdown")
            rb_cols = st.columns(5)
            with rb_cols[0]:
                st.metric("Base (Fuel)", f"{risk_budget.get('base_from_fuel', 0):.3f}")
            with rb_cols[1]:
                st.metric("State Mult", f"{risk_budget.get('state_multiplier', 1):.2f}")
            with rb_cols[2]:
                st.metric("Crack Penalty", f"{risk_budget.get('crack_penalty', 1):.2f}")
            with rb_cols[3]:
                st.metric("Trend Penalty", f"{risk_budget.get('trend_penalty', 1):.2f}")
            with rb_cols[4]:
                st.metric("Final", f"{risk_budget.get('final_risk_budget', 0):.3f}")

        # Recommendations (v2)
        action_info = result.get('action', {})
        if isinstance(action_info, dict) and 'recommendation' in action_info:
            recs = action_info['recommendation']
            if recs:
                with st.expander("📋 Recommendations", expanded=False):
                    for rec in recs:
                        st.markdown(f"- {rec}")

    else:
        # v1: Original display
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            state = result['system_state']
            st.metric(
                "System State",
                state,
                help="Overall system state: NORMAL/CAUTIOUS/DEFENSIVE/CRISIS"
            )

        with col2:
            action = result['action']
            st.metric(
                "Action",
                action,
                help="Recommended action: HOLD/DE-RISK/HEDGE/EXIT"
            )

        with col3:
            st.metric(
                "Risk Budget",
                f"{result['risk_budget']:.2f}",
                help="Recommended risk budget (0.35-1.15)"
            )

        with col4:
            st.metric(
                "Confidence",
                result['confidence'],
                help="Data quality confidence: LOW/MEDIUM/HIGH"
            )

        # Reason (v1)
        st.info("**Reason:** " + "; ".join(result['reason']))

    # Escalation Triggers (v2 only)
    if use_v2:
        escalation = result.get('escalation_triggers', {})
        if escalation:
            # Check if there are any triggers to display
            has_upgrade = any([
                escalation.get('to_crisis_if', []),
                escalation.get('to_defensive_if', []),
                escalation.get('to_cautious_if', [])
            ])
            has_downgrade = bool(escalation.get('downgrade_rules', []))

            if has_upgrade or has_downgrade:
                with st.expander("⚠️ Escalation Triggers", expanded=False):
                    upgrade_col, downgrade_col = st.columns(2)

                    with upgrade_col:
                        st.markdown("**Upgrade Conditions:**")
                        if escalation.get('to_crisis_if'):
                            st.markdown("*→ CRISIS:*")
                            for cond in escalation['to_crisis_if']:
                                st.markdown(f"  - {cond}")
                        if escalation.get('to_defensive_if'):
                            st.markdown("*→ DEFENSIVE:*")
                            for cond in escalation['to_defensive_if']:
                                st.markdown(f"  - {cond}")
                        if escalation.get('to_cautious_if'):
                            st.markdown("*→ CAUTIOUS:*")
                            for cond in escalation['to_cautious_if']:
                                st.markdown(f"  - {cond}")

                    with downgrade_col:
                        st.markdown("**Downgrade Conditions:**")
                        for cond in escalation.get('downgrade_rules', []):
                            st.markdown(f"- {cond}")

    st.divider()

    # ====================
    # Three Layer Details
    # ====================

    tab1, tab2, tab3 = st.tabs(["⛽ Fuel (FuelScore)", "🔧 Crack (CrackScore)", "📈 Trend (TrendScore)"])

    # Structure Tab
    with tab1:
        structure = result['structure']

        col1, col2 = st.columns([1, 2])

        with col1:
            st.plotly_chart(
                make_gauge_chart(
                    structure['fuel_score'], 100,
                    f"FuelScore: {structure['fuel_signal']}",
                    thresholds=[0.2, 0.4, 0.6, 0.8]
                ),
                use_container_width=True
            )
            st.caption(f"Date: {structure['date']} | Risk Budget: {structure['risk_budget']:.2f}")
            st.caption(f"Notes: {structure['notes']}")

            # Show IC vs AUC comparison for current values (cached)
            try:
                fuel_both = get_fuel_comparison()
                ic_score = fuel_both['ic']['fuel_score']
                auc_score = fuel_both['auc']['fuel_score']
                st.markdown("---")
                st.markdown("**Weight Scheme Comparison**")
                ic_col, auc_col = st.columns(2)
                with ic_col:
                    st.metric("IC Weight", f"{ic_score:.1f}", help="Based on 12M return correlation")
                with auc_col:
                    st.metric("AUC Weight", f"{auc_score:.1f}", help="Based on MDD prediction")
            except Exception:
                pass

        with col2:
            st.plotly_chart(
                make_bar_chart(structure['fuel_components'], "Fuel Components", 100,
                              explanations=FUEL_FACTOR_EXPLANATIONS),
                use_container_width=True
            )
            st.caption("💡 悬停查看因子经济含义")

    # Crack Tab
    with tab2:
        crack = result['crack']

        col1, col2 = st.columns([1, 2])

        with col1:
            st.plotly_chart(
                make_gauge_chart(
                    crack['crack_score'], 2.0,
                    f"CrackScore: {crack['crack_state']}",
                    thresholds=[0.15, 0.25, 0.5]  # 0.3σ, 0.5σ, 1.0σ
                ),
                use_container_width=True
            )
            st.caption(f"Date: {crack['date']} | Dominant: {crack['dominant_crack'] or 'N/A'}")

        with col2:
            st.plotly_chart(
                make_crack_bar_chart(crack['crack_components'],
                                    explanations=CRACK_FACTOR_EXPLANATIONS),
                use_container_width=True
            )
            st.caption("💡 悬停查看因子经济含义")

    # Trend Tab
    with tab3:
        trend = result['trend']

        col1, col2 = st.columns([1, 2])

        with col1:
            heat = trend['trend_heat'] if not np.isnan(trend['trend_heat']) else 0
            st.plotly_chart(
                make_gauge_chart(
                    heat, 1.0,
                    f"TrendScore: {trend['trend_state']}",
                    thresholds=[0.25, 0.45, 0.65]
                ),
                use_container_width=True
            )
            quality = trend['data_quality']
            st.caption(f"Date: {trend['date']}")
            st.caption(f"Quality: {quality.get('quality_level', 'N/A')} ({quality.get('coverage_modules', 0)}/4 modules)")
            st.caption(f"Dominant Module: {trend['dominant_module'] or 'N/A'}")

        with col2:
            st.plotly_chart(
                make_module_bar_chart(trend['module_heat'],
                                     explanations=TREND_MODULE_EXPLANATIONS),
                use_container_width=True
            )
            st.caption("💡 悬停查看模块经济含义")

    st.divider()

    # ====================
    # Historical Charts
    # ====================

    st.header("Historical Trends")

    # Load history with date range
    history = load_history_data(
        start_date=history_start.strftime('%Y-%m-%d'),
        end_date=history_end.strftime('%Y-%m-%d')
    )
    spx = history.get('spx')

    # FuelScore IC vs AUC Comparison Chart (shows both weight schemes)
    if history.get('fuel_both') is not None and len(history['fuel_both']) > 0:
        st.subheader("FuelScore: IC vs AUC Weight Comparison")
        st.caption("Blue = IC weights (Return correlation) | Coral = AUC weights (MDD prediction)")
        st.plotly_chart(
            make_fuel_comparison_chart(history['fuel_both'], spx),
            use_container_width=True
        )

    st.divider()

    # Individual charts - 每个图占一整行，顺序：Fuel → Crack → Trend
    if history.get('fuel') is not None:
        st.plotly_chart(
            make_fuel_history_chart(history['fuel'], spx),
            use_container_width=True
        )

    if history.get('crack') is not None:
        st.plotly_chart(
            make_crack_history_chart(history['crack'], spx),
            use_container_width=True
        )

    if history.get('trend') is not None:
        st.plotly_chart(
            make_trend_history_chart(history['trend'], spx),
            use_container_width=True
        )

    # ====================
    # Raw Data
    # ====================

    version_label = "v2 Rule Engine" if use_v2 else "v1 State Table"
    with st.expander(f"View Raw JSON Output ({version_label})"):
        st.json(result)


if __name__ == "__main__":
    main()
