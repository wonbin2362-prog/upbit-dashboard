import pandas as pd

MA_SHORT = 5
MA_LONG = 20
BB_PERIOD = 20
BB_STD = 2


def rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(df, fast=12, slow=26, signal=9):
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "histogram": histogram}
    )


def moving_averages(df, short=MA_SHORT, long=MA_LONG):
    return pd.DataFrame(
        {
            "ma_short": df["close"].rolling(short).mean(),
            "ma_long": df["close"].rolling(long).mean(),
        }
    )


def bollinger_bands(df, period=BB_PERIOD, num_std=BB_STD):
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    return pd.DataFrame(
        {
            "bb_mid": mid,
            "bb_upper": mid + num_std * std,
            "bb_lower": mid - num_std * std,
        }
    )


def add_indicators(
    df,
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    ma_short=MA_SHORT,
    ma_long=MA_LONG,
    bb_period=BB_PERIOD,
    bb_std=BB_STD,
):
    out = df.copy()
    out["rsi"] = rsi(out, period=rsi_period)

    macd_df = macd(out, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    out["macd"] = macd_df["macd"]
    out["macd_signal"] = macd_df["signal"]
    out["macd_hist"] = macd_df["histogram"]

    ma_df = moving_averages(out, short=ma_short, long=ma_long)
    out["ma_short"] = ma_df["ma_short"]
    out["ma_long"] = ma_df["ma_long"]

    bb_df = bollinger_bands(out, period=bb_period, num_std=bb_std)
    out["bb_mid"] = bb_df["bb_mid"]
    out["bb_upper"] = bb_df["bb_upper"]
    out["bb_lower"] = bb_df["bb_lower"]

    return out
