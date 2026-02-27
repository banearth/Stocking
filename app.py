import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import get_stock_data, calculate_indicators, predict_trend, run_strategy, calculate_strategy_performance, generate_tactical_panel, get_options_data, generate_raw_data_report

st.set_page_config(page_title="美股投资分析工具", layout="wide")

st.markdown("""
<style>
    .stMetric {
        background-color: #111827;
        color: #f9fafb;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #4b5563;
    }
    [data-testid="stMetricLabel"] {
        color: #cbd5f5;
    }
    [data-testid="stMetricValue"] {
        color: #f8fafc;
        font-weight: 700;
    }
    [data-testid="stMetricDelta"] {
        color: #a7f3d0;
    }
    .stDataFrame {
        border: 1px solid #374151;
        background-color: #111827;
        color: #e5e7eb;
    }
    .tactical-box {
        padding: 20px; border-radius: 10px; background-color: #262730; color: white; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 【V3醒目标记】
st.title("📈 核心资产实战决策面板 [V3.1 宏观自适应版]")
st.markdown("系统内置**状态机路由**与**动态防守脚本**，抛弃机械打分，专为趋势跟踪与长线波段定制定向策略。")

st.sidebar.header("用户输入")

st.sidebar.markdown("**港股示例：** 0700.HK (腾讯), 9988.HK (阿里), HSTECH.HK (恒生科技)")
hk_presets = {
    "无 (手动输入)": "",
    "恒生科技 (HSTECH - 替代ETF:3033)": "3033.HK",
    "恒生指数 (HSI)": "^HSI",
    "腾讯控股 (0700)": "0700.HK",
    "阿里巴巴 (9988)": "9988.HK",
    "美团 (3690)": "3690.HK",
    "小米 (1810)": "1810.HK"
}
selected_preset = st.sidebar.selectbox("快速选择港股", list(hk_presets.keys()))
if hk_presets[selected_preset]:
    ticker = hk_presets[selected_preset]
else:
    ticker = st.sidebar.text_input("输入股票代码 (例如: AAPL, U, GLD)", "U").upper()
period_map = {
    "1个月": "1mo", "3个月": "3mo", "6个月": "6mo", 
    "1年": "1y", "2年": "2y", "5年": "5y", "最大": "max"
}
selected_period_label = st.sidebar.selectbox("选择时间范围", list(period_map.keys()), index=3)
period = period_map[selected_period_label]

st.sidebar.subheader("技术指标开关")
show_sma = st.sidebar.checkbox("简单移动平均线 (SMA)", True)
show_ema = st.sidebar.checkbox("指数移动平均线 (EMA)", False)
show_rsi = st.sidebar.checkbox("相对强弱指数 (RSI)", False)
show_macd = st.sidebar.checkbox("MACD 指标", False)
show_bollinger = st.sidebar.checkbox("布林带 (Bollinger Bands)", False)

if ticker:
    with st.spinner(f"正在加载 {ticker} 的数据..."):
        df, info = get_stock_data(ticker, period=period)
        
    if df is not None and not df.empty:
        df = calculate_indicators(df)
        options_data = None 
        
        with st.spinner("正在探知期权情绪底牌 (V3远期侦测)..."):
             options_data = get_options_data(ticker)

        # ================= 改造后的战术面板 UI =================
        st.subheader("🎯 实战战术面板 (V3 引擎驱动)")
        tactical_panel = generate_tactical_panel(df, options_data, info)
        
        if tactical_panel:
            col_state, col_action = st.columns([1, 1.5])
            
            with col_state:
                st.markdown(f"""
                <div class="tactical-box" style="background-color: #1E3A8A;">
                    <h3 style="margin-top:0; color: #93C5FD;">📍 当前运行状态</h3>
                    <h2 style="color: white;">{tactical_panel['state_title']}</h2>
                    <p style="opacity: 0.9;">{tactical_panel['state_desc']}</p>
                    <hr style="border-color: #3B82F6;">
                    <p style="margin-bottom:0;"><b>🔥 情绪探针：</b>{tactical_panel['emotion']}</p>
                </div>
                """, unsafe_allow_html=True)
                
            with col_action:
                st.markdown(f"""
                <div class="tactical-box" style="background-color: #064E3B;">
                    <h3 style="margin-top:0; color: #6EE7B7;">⚔️ 机器执行脚本</h3>
                    <p><b>📈 向上阻力位：</b> <span style="font-size: 1.2em; color: white;">${tactical_panel['resistance']:.2f}</span></p>
                    <p><b>📉 向下支撑位：</b> <span style="font-size: 1.2em; color: white;">${tactical_panel['support']:.2f}</span></p>
                    <hr style="border-color: #059669;">
                    <ul style="opacity: 0.9;">
                        {''.join([f'<li style="margin-bottom: 5px;">{act}</li>' for act in tactical_panel['actions']])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("数据不足，无法生成战术指令。")
            
        st.divider()

        # 显示股票基本信息
        col1, col2, col3, col4 = st.columns(4)
        current_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
        change = current_price - prev_close
        pct_change = (change / prev_close) * 100
        
        col1.metric("当前价格", f"${current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        if info:
            market_cap = info.get('marketCap')
            if market_cap and isinstance(market_cap, (int, float)):
                col2.metric("总市值", f"${market_cap:,.0f}")
            else:
                col2.metric("总市值", "N/A")
            # [V3] ETF 过滤显示
            if info.get('quoteType', 'EQUITY') == 'ETF':
                 col3.metric("市盈率 (PE)", "N/A (ETF)")
            else:
                 col3.metric("市盈率 (PE)", f"{info.get('trailingPE', 'N/A')}")
            
            # [V3] 动态重算 52周最高
            col4.metric("52周最高(动态重算)", f"${df.tail(252)['High'].max():.2f}")

        # 下面的 Tabs UI 全完保留你的原始代码，没动
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 行情走势", "📈 技术指标详解", "🔮 趋势预测", "⚔️ 策略回测", "💰 期权分析", "📝 纯数据导出"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='股价'))
            if show_sma:
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1.5), name='SMA 20'))
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='royalblue', width=1.5), name='SMA 50'))
            if show_ema:
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='cyan', width=1), name='EMA 12'))
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='magenta', width=1), name='EMA 26'))
            if show_bollinger and 'BB_Upper' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='gray', width=1, dash='dash'), name='布林带上轨'))
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='gray', width=1, dash='dash'), name='布林带下轨', fill='tonexty', fillcolor='rgba(128,128,128,0.1)'))
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, xaxis_title="日期", yaxis_title="价格 (USD)", hovermode="x unified", template="plotly_white", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            col_tech1, col_tech2 = st.columns(2)
            with col_tech1:
                if show_rsi:
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple', width=2)))
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                    fig_rsi.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), template="plotly_white")
                    st.plotly_chart(fig_rsi, use_container_width=True)
            with col_tech2:
                if show_macd:
                    fig_macd = go.Figure()
                    fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD 快线', line=dict(color='blue', width=1.5)))
                    fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='信号线', line=dict(color='orange', width=1.5)))
                    colors = ['green' if val >= 0 else 'red' for val in (df['MACD'] - df['Signal_Line'])]
                    fig_macd.add_trace(go.Bar(x=df.index, y=df['MACD'] - df['Signal_Line'], name='MACD 柱', marker_color=colors))
                    fig_macd.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), template="plotly_white")
                    st.plotly_chart(fig_macd, use_container_width=True)

        with tab3:
            future_df, slope = predict_trend(df)
            if future_df is not None:
                trend_color = "green" if slope > 0 else "red"
                fig_pred = go.Figure()
                fig_pred.add_trace(go.Scatter(x=df.index, y=df['Close'], name='历史价格', line=dict(color='gray', width=1)))
                fig_pred.add_trace(go.Scatter(x=future_df.index, y=future_df['Predicted_Close'], name='预测趋势', line=dict(dash='dot', color='red', width=2)))
                fig_pred.update_layout(title=f"预测斜率: {slope:.2f}", height=500, template="plotly_white", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig_pred, use_container_width=True)

        with tab4:
            strategies = {
                'SMA金叉策略': 'sma',
                'RSI均值回归': 'rsi',
                'MACD趋势策略': 'macd',
                '布林带突破': 'bollinger'
            }
            results = []
            signals_dict = {}
            for name, code in strategies.items():
                sig = run_strategy(df, code)
                if sig is not None:
                    perf = calculate_strategy_performance(df, sig)
                    if perf:
                        results.append({
                            '策略名称': name,
                            '总收益率 (%)': f"{perf['total_return']:.2f}%",
                            '最终资产': f"${perf['final_value']:.2f}",
                            '交易次数': perf['trades']
                        })
                        signals_dict[name] = sig
            if results:
                st.table(pd.DataFrame(results))
                st.divider()
                col_sel1, col_sel2 = st.columns([1, 3])
                with col_sel1:
                    selected_strat = st.selectbox("选择要可视化的策略", list(strategies.keys()))
                current_sig = signals_dict.get(selected_strat)
                if current_sig is not None:
                    buy_signals = current_sig[current_sig['Position'] == 1.0]
                    sell_signals = current_sig[current_sig['Position'] == -1.0]
                    fig_strat = go.Figure()
                    fig_strat.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='股价'))
                    if selected_strat == 'SMA金叉策略':
                        fig_strat.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name='SMA 20', line=dict(color='orange', width=1)))
                        fig_strat.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA 50', line=dict(color='blue', width=1)))
                    elif selected_strat == '布林带突破':
                         if 'BB_Upper' in df.columns:
                            fig_strat.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='上轨', line=dict(color='gray', dash='dash')))
                            fig_strat.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='下轨', line=dict(color='gray', dash='dash'), fill='tonexty'))
                    fig_strat.add_trace(go.Scatter(x=buy_signals.index, y=df.loc[buy_signals.index]['Close'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', color='#00CC96', size=15, line=dict(width=1, color='black')), name='买入信号'))
                    fig_strat.add_trace(go.Scatter(x=sell_signals.index, y=df.loc[sell_signals.index]['Close'] * 1.02, mode='markers', marker=dict(symbol='triangle-down', color='#EF553B', size=15, line=dict(width=1, color='black')), name='卖出信号'))
                    fig_strat.update_layout(height=600, title=f"{selected_strat} 买卖点展示", template="plotly_white", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig_strat, use_container_width=True)
            else:
                st.warning("数据不足，无法计算策略表现。")

        with tab5:
            if options_data:
                st.subheader(f"📊 期权情绪分析 (到期日: {options_data['expiration_date']}) [V3远期]")
                col_opt1, col_opt2, col_opt3 = st.columns(3)
                pcr = options_data['pcr']
                col_opt1.metric("PCR", f"{pcr:.2f}")
                col_opt2.metric("Call Vol", f"{options_data['total_call_vol']:,}")
                col_opt3.metric("Put Vol", f"{options_data['total_put_vol']:,}")
                col_call_table, col_put_table = st.columns(2)
                with col_call_table:
                    st.dataframe(options_data['top_calls'][['contractSymbol', 'strike', 'volume', 'lastPrice']], hide_index=True)
                with col_put_table:
                    st.dataframe(options_data['top_puts'][['contractSymbol', 'strike', 'volume', 'lastPrice']], hide_index=True)

        with tab6:
            if st.button("生成数据报告"):
                raw_report = generate_raw_data_report(df, info, options_data)
                st.code(raw_report, language="text")
    else:
        st.error("数据加载失败。")
