import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

def get_stock_data(ticker, period="1y", interval="1d"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty: return None, None
        df.index = df.index.tz_localize(None)
        info = stock.info
        return df, info
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None

def calculate_indicators(df):
    if df is None or df.empty: return df
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['Close'].rolling(window=20).std()
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['Close'].rolling(window=20).std()
    return df

def predict_trend(df, future_days=30):
    if df is None or len(df) < 50: return None, None
    df_copy = df.copy()
    df_copy['Date_Ordinal'] = df_copy.index.map(pd.Timestamp.toordinal)
    X = df_copy[['Date_Ordinal']].values
    y = df_copy['Close'].values
    model = LinearRegression()
    model.fit(X, y)
    last_date = df_copy.index[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, future_days + 1)]
    future_ordinals = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
    predictions = model.predict(future_ordinals)
    future_df = pd.DataFrame({'Date': future_dates, 'Predicted_Close': predictions})
    future_df.set_index('Date', inplace=True)
    return future_df, model.coef_[0]

def run_strategy(df, strategy_type='sma'):
    if df is None: return None
    signals = pd.DataFrame(index=df.index)
    signals['Signal'] = 0.0
    if strategy_type == 'sma':
        valid_idx = (df['SMA_20'].notna()) & (df['SMA_50'].notna())
        signals.loc[valid_idx, 'Signal'] = np.where(df.loc[valid_idx, 'SMA_20'] > df.loc[valid_idx, 'SMA_50'], 1.0, 0.0)
    elif strategy_type == 'rsi':
        current_signal = 0.0
        signal_list = []
        for rsi in df['RSI']:
            if rsi < 30: current_signal = 1.0
            elif rsi > 70: current_signal = 0.0
            signal_list.append(current_signal)
        signals['Signal'] = signal_list
    elif strategy_type == 'macd':
        valid_idx = (df['MACD'].notna()) & (df['Signal_Line'].notna())
        signals.loc[valid_idx, 'Signal'] = np.where(df.loc[valid_idx, 'MACD'] > df.loc[valid_idx, 'Signal_Line'], 1.0, 0.0)
    elif strategy_type == 'bollinger':
        current_signal = 0.0
        signal_list = []
        for i in range(len(df)):
            close = df['Close'].iloc[i]
            lower = df['BB_Lower'].iloc[i]
            upper = df['BB_Upper'].iloc[i]
            if pd.isna(lower) or pd.isna(upper):
                signal_list.append(0.0)
                continue
            if close < lower: current_signal = 1.0
            elif close > upper: current_signal = 0.0
            signal_list.append(current_signal)
        signals['Signal'] = signal_list
    signals['Position'] = signals['Signal'].diff()
    return signals

def calculate_strategy_performance(df, signals):
    if signals is None or df is None: return None
    initial_capital = 10000.0
    balance = initial_capital
    position = 0
    backtest_df = pd.DataFrame({'Close': df['Close'], 'Position': signals['Position']})
    trades = 0
    for date, row in backtest_df.iterrows():
        price = row['Close']
        action = row['Position']
        if action == 1.0:
            if balance > 0:
                position = balance / price
                balance = 0
                trades += 1
        elif action == -1.0:
            if position > 0:
                balance = position * price
                position = 0
                trades += 1
    final_value = balance + (position * df['Close'].iloc[-1])
    total_return = (final_value - initial_capital) / initial_capital * 100
    return {'total_return': total_return, 'final_value': final_value, 'trades': trades}

def get_options_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations: return None
        nearest_date = expirations[0]
        opt_chain = stock.option_chain(nearest_date)
        calls, puts = opt_chain.calls, opt_chain.puts
        total_call_vol = calls['volume'].sum() if not calls.empty else 0
        total_put_vol = puts['volume'].sum() if not puts.empty else 0
        pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0
        top_calls = calls.sort_values(by='volume', ascending=False).head(5)[['contractSymbol', 'strike', 'lastPrice', 'volume', 'impliedVolatility']]
        top_puts = puts.sort_values(by='volume', ascending=False).head(5)[['contractSymbol', 'strike', 'lastPrice', 'volume', 'impliedVolatility']]
        return {'expiration_date': nearest_date, 'pcr': pcr, 'total_call_vol': total_call_vol, 'total_put_vol': total_put_vol, 'top_calls': top_calls, 'top_puts': top_puts}
    except Exception as e:
        print(f"Error fetching options data: {e}")
        return None

# ============== 核心重构：状态机战术引擎 ==============
def generate_tactical_panel(df, options_data=None, info=None):
    """
    基于状态机的实战战术面板生成器。
    摒弃传统的机械打分，直接输出当前状态和执行脚本。
    """
    if df is None or df.empty: return None

    current_price = df['Close'].iloc[-1]
    
    # 1. 计算边界探针 (支撑与压力) - 战术雷达缩圈（防暴跌失真）
    # 放弃死板的30天，改为提取最近 8 个交易日（恰好覆盖 Unity 暴跌企稳后的近期真实多空博弈区）
    recent_tactical = df.tail(8)
    support_level = recent_tactical['Low'].min()
    resistance_level = recent_tactical['High'].max()
    
    # 2. 计算大局观 (价格分位)
    high_52w = info.get('fiftyTwoWeekHigh') if info else df['High'].max()
    low_52w = info.get('fiftyTwoWeekLow') if info else df['Low'].min()
    
    # 防止除以0
    if high_52w == low_52w: high_52w += 0.01
    price_percentile = ((current_price - low_52w) / (high_52w - low_52w)) * 100

    # 3. 提取情绪探针与动能
    pcr = options_data.get('pcr', 1.0) if options_data else 1.0
    rsi = df['RSI'].iloc[-1] if 'RSI' in df.columns else 50
    volume_surge = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5

    # 4. 状态机路由与脚本生成
    tactical_data = {
        'support': support_level,
        'resistance': resistance_level,
        'percentile': price_percentile,
        'actions': []
    }

    # 情绪分析文案
    if pcr < 0.6:
        tactical_data['emotion'] = f"PCR极低 ({pcr:.2f})，期权资金强烈押注向上波动。"
    elif pcr > 1.2:
        tactical_data['emotion'] = f"PCR偏高 ({pcr:.2f})，市场避险情绪较重，注意防守。"
    else:
        tactical_data['emotion'] = f"PCR中性 ({pcr:.2f})，期权市场无极端分歧。"

    # 根据状态机判定区间
    if price_percentile <= 25:
        tactical_data['state_title'] = "深水区 (超跌左侧)"
        tactical_data['state_desc'] = "股价处于一年内的绝对底部区域。此时均线大概率处于滞后的死叉状态，趋势指标已失效。"
        
        tactical_data['actions'].append("🛡️ **绝对纪律：** 严禁在此位置恐慌性止损或割肉。")
        tactical_data['actions'].append("💡 **均线过滤：** 屏蔽 SMA/MACD 的空头信号，只看底部支撑。")
        
        if pcr < 0.7 or rsi < 35:
            tactical_data['actions'].append("🔥 **异动提醒：** 情绪极度超卖/期权异动，随时可能爆发技术性超跌反弹。")
            tactical_data['actions'].append(f"🕸️ **网格激活：** 逢高至 ${resistance_level:.2f} 附近抛出机动仓，回踩至 ${support_level:.2f} 附近重新接回，摊薄底仓成本。")
        else:
            tactical_data['actions'].append("⏳ **耐心潜伏：** 右侧趋势未明，可利用极小仓位在支撑位附近试错，重仓需等待放量突破。")

    elif 25 < price_percentile <= 75:
        tactical_data['state_title'] = "箱体震荡区 (多空拉锯)"
        tactical_data['state_desc'] = "股价脱离底部，进入横盘震荡蓄势阶段。此阶段追涨杀跌极易两头打脸。"
        
        tactical_data['actions'].append(f"📏 **明确边界：** 当前运行在 ${support_level:.2f} - ${resistance_level:.2f} 箱体中。")
        tactical_data['actions'].append("🕸️ **网格战术：** 靠近下沿买入，靠近上沿卖出，赚取震荡差价。")
        
        if current_price >= resistance_level * 0.95:
            if volume_surge:
                tactical_data['actions'].append("🚀 **突破预警：** 股价逼近上沿且伴随爆量，若收盘有效站稳压力位，箱体打开，准备右侧追随！")
            else:
                tactical_data['actions'].append("⚠️ **遇阻预警：** 逼近上沿但量能不足，随时准备执行高抛。")

    else:
        tactical_data['state_title'] = "高位趋势区 (右侧博弈)"
        tactical_data['state_desc'] = "股价处于强势上升通道或历史高位。此时应顺势而为，趋势指标有效性极高。"
        
        tactical_data['actions'].append("🛡️ **底仓保护：** 依托 20日/50日均线持有，均线不破不卖。")
        if rsi > 70 and pcr < 0.6:
            tactical_data['actions'].append("⚠️ **见顶预警：** RSI极度超买且期权狂热，谨防加速赶顶，考虑分批止盈防守。")
        else:
            tactical_data['actions'].append("🌊 **顺势跟踪：** 趋势良好，切勿轻易猜顶，让利润奔跑。")

    return tactical_data

def generate_raw_data_report(df, info, options_data):
    # 原逻辑保留，这部分不用修改
    report = []
    report.append("=== 股票基本信息 ===")
    if info:
        report.append(f"代码: {info.get('symbol', 'N/A')}")
        report.append(f"名称: {info.get('shortName', 'N/A')}")
        report.append(f"当前价格: {info.get('currentPrice', 'N/A')}")
        report.append(f"市值: {info.get('marketCap', 'N/A')}")
        report.append(f"市盈率 (PE): {info.get('trailingPE', 'N/A')}")
        report.append(f"52周最高: {info.get('fiftyTwoWeekHigh', 'N/A')}")
        report.append(f"52周最低: {info.get('fiftyTwoWeekLow', 'N/A')}")
    else:
        report.append("无法获取基本信息")
    report.append("\n=== 期权情绪数据 ===")
    if options_data:
        report.append(f"到期日: {options_data['expiration_date']}")
        report.append(f"Put/Call Ratio (PCR): {options_data['pcr']:.4f}")
        report.append(f"看涨期权总成交量: {options_data['total_call_vol']}")
        report.append(f"看跌期权总成交量: {options_data['total_put_vol']}")
    else:
        report.append("无期权数据")
    return "\n".join(report)
