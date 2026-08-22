import pandas as pd

import backtest

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70


def analyze(df):
    """df는 add_indicators()가 적용된 데이터프레임. 마지막 캔들 기준으로 신호를 분석한다."""
    if len(df) < 2:
        return None

    labeled = backtest.label_signals(df)
    last = labeled.iloc[-1]
    prev = labeled.iloc[-2]

    messages = []

    rsi_val = last["rsi"]
    if rsi_val <= RSI_OVERSOLD:
        messages.append(f"RSI {rsi_val:.1f} -> 과매도 (매수 관심)")
    elif rsi_val >= RSI_OVERBOUGHT:
        messages.append(f"RSI {rsi_val:.1f} -> 과매수 (매도 관심)")

    macd_cross_up = prev["macd"] <= prev["macd_signal"] and last["macd"] > last["macd_signal"]
    macd_cross_down = prev["macd"] >= prev["macd_signal"] and last["macd"] < last["macd_signal"]

    if macd_cross_up:
        messages.append("MACD 골든크로스 (매수 신호)")
    elif macd_cross_down:
        messages.append("MACD 데드크로스 (매도 신호)")

    ma_cross_up = prev["ma_short"] <= prev["ma_long"] and last["ma_short"] > last["ma_long"]
    ma_cross_down = prev["ma_short"] >= prev["ma_long"] and last["ma_short"] < last["ma_long"]

    if ma_cross_up:
        messages.append("이동평균 골든크로스 (매수 신호)")
    elif ma_cross_down:
        messages.append("이동평균 데드크로스 (매도 신호)")

    if last["close"] <= last["bb_lower"]:
        messages.append("볼린저밴드 하단 이탈 (매수 관심)")
    elif last["close"] >= last["bb_upper"]:
        messages.append("볼린저밴드 상단 이탈 (매도 관심)")

    ichimoku_cross_up = prev["ichimoku_tenkan"] <= prev["ichimoku_kijun"] and last["ichimoku_tenkan"] > last["ichimoku_kijun"]
    ichimoku_cross_down = prev["ichimoku_tenkan"] >= prev["ichimoku_kijun"] and last["ichimoku_tenkan"] < last["ichimoku_kijun"]

    if ichimoku_cross_up:
        messages.append("일목균형표 전환선-기준선 골든크로스 (매수 신호)")
    elif ichimoku_cross_down:
        messages.append("일목균형표 전환선-기준선 데드크로스 (매도 신호)")

    # 장기추세는 득표에는 반영하지 않고, 참고 정보로만 함께 보여준다.
    trend_ma = last["trend_ma"]
    if pd.notna(trend_ma):
        if last["close"] > trend_ma:
            trend = "상승"
        elif last["close"] < trend_ma:
            trend = "하락"
        else:
            trend = "중립"
    else:
        trend = None

    return {
        "close": last["close"],
        "rsi": rsi_val,
        "macd": last["macd"],
        "macd_signal": last["macd_signal"],
        "macd_hist": last["macd_hist"],
        "ma_short": last["ma_short"],
        "ma_long": last["ma_long"],
        "bb_upper": last["bb_upper"],
        "bb_lower": last["bb_lower"],
        "ichimoku_tenkan": last["ichimoku_tenkan"],
        "ichimoku_kijun": last["ichimoku_kijun"],
        "trend": trend,
        "trend_ma": trend_ma,
        "buy_votes": int(last["buy_votes"]),
        "sell_votes": int(last["sell_votes"]),
        "messages": messages,
        "combined_signal": last["signal_label"],
        "labeled_df": labeled,
    }
