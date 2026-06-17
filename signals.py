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

    return {
        "close": last["close"],
        "rsi": rsi_val,
        "macd": last["macd"],
        "macd_signal": last["macd_signal"],
        "macd_hist": last["macd_hist"],
        "messages": messages,
        "combined_signal": last["signal_label"],
        "labeled_df": labeled,
    }
