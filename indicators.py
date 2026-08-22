import pandas as pd

MA_SHORT = 5
MA_LONG = 20
BB_PERIOD = 20
BB_STD = 2
ICHIMOKU_TENKAN = 9
ICHIMOKU_KIJUN = 26
TREND_WINDOW = 60
# 장기추세 판정용 이동평균 기간(캔들 개수). 봉 종류별로 비슷한 기간을 보도록 다르게 잡는다.
# day: 60일 / minute60: 200시간(약 8일) - 참고용 정보일 뿐 알림 여부를 거르는 데는 쓰지 않는다.
TREND_WINDOW_BY_INTERVAL = {"minute60": 200, "day": 60}


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


def ichimoku(df, tenkan=ICHIMOKU_TENKAN, kijun=ICHIMOKU_KIJUN):
    tenkan_sen = (df["high"].rolling(tenkan).max() + df["low"].rolling(tenkan).min()) / 2
    kijun_sen = (df["high"].rolling(kijun).max() + df["low"].rolling(kijun).min()) / 2
    return pd.DataFrame({"ichimoku_tenkan": tenkan_sen, "ichimoku_kijun": kijun_sen})


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
    ichimoku_tenkan=ICHIMOKU_TENKAN,
    ichimoku_kijun=ICHIMOKU_KIJUN,
    trend_window=TREND_WINDOW,
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

    ichimoku_df = ichimoku(out, tenkan=ichimoku_tenkan, kijun=ichimoku_kijun)
    out["ichimoku_tenkan"] = ichimoku_df["ichimoku_tenkan"]
    out["ichimoku_kijun"] = ichimoku_df["ichimoku_kijun"]

    out["trend_ma"] = out["close"].rolling(trend_window).mean()

    return out
