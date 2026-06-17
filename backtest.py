import numpy as np

# 신호 적중 여부를 판단할 때 몇 캔들 뒤까지 볼지 (1시간봉=24캔들=1일, 일봉=5캔들=5일)
LOOKAHEAD_BY_INTERVAL = {"minute60": 24, "day": 5}

# 백테스트용으로 받아올 과거 캔들 개수 (1시간봉=약 25일, 일봉=약 1년) - 너무 늘리면 API 호출이 많아져 느려짐
BACKTEST_COUNT_BY_INTERVAL = {"minute60": 600, "day": 365}

SIGNAL_LABELS = ["강한 매수", "약한 매수", "강한 매도", "약한 매도"]


def label_signals(df):
    """RSI와 MACD 신호를 결합해 캔들마다 종합 신호를 매긴다."""
    df = df.copy()

    rsi_oversold = df["rsi"] <= 30
    rsi_overbought = df["rsi"] >= 70
    macd_cross_up = (df["macd"].shift(1) <= df["macd_signal"].shift(1)) & (
        df["macd"] > df["macd_signal"]
    )
    macd_cross_down = (df["macd"].shift(1) >= df["macd_signal"].shift(1)) & (
        df["macd"] < df["macd_signal"]
    )

    strong_buy = rsi_oversold & macd_cross_up
    strong_sell = rsi_overbought & macd_cross_down
    weak_buy = (rsi_oversold | macd_cross_up) & ~strong_buy
    weak_sell = (rsi_overbought | macd_cross_down) & ~strong_sell

    df["signal_label"] = np.select(
        [strong_buy, strong_sell, weak_buy, weak_sell],
        ["강한 매수", "강한 매도", "약한 매수", "약한 매도"],
        default="중립",
    )
    return df


def compute_winrate(labeled_df, lookahead):
    """과거에 같은 신호가 나왔을 때, lookahead 캔들 후 실제로 신호 방향대로 움직였는지 비율을 계산한다."""
    df = labeled_df.copy()
    df["future_return"] = df["close"].shift(-lookahead) / df["close"] - 1

    stats = {}
    for label in SIGNAL_LABELS:
        subset = df[(df["signal_label"] == label) & df["future_return"].notna()]
        if subset.empty:
            stats[label] = {"count": 0, "win_rate": None, "avg_return": None}
            continue

        if "매수" in label:
            win_rate = (subset["future_return"] > 0).mean()
        else:
            win_rate = (subset["future_return"] < 0).mean()

        stats[label] = {
            "count": int(len(subset)),
            "win_rate": float(win_rate),
            "avg_return": float(subset["future_return"].mean()),
        }
    return stats
