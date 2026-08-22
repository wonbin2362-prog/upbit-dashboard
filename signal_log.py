import os

import pandas as pd

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signal_log.csv")

COLUMNS = [
    "id", "logged_at", "category", "code", "name", "interval",
    "candle_time", "action", "signal_label", "buy_votes", "sell_votes",
    "trend", "close", "lookahead", "status", "future_close", "return_pct", "resolved_at",
]


def _load():
    # 컬럼마다 타입이 섞여 있고(문자열/숫자/NA) 계속 값이 채워지므로,
    # pandas가 dtype을 잘못 추론해서 나중에 문자열을 못 넣는 문제를 막기 위해 전부 object로 다룬다.
    if not os.path.exists(LOG_PATH):
        return pd.DataFrame(columns=COLUMNS, dtype=object)
    df = pd.read_csv(LOG_PATH, dtype=str)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[COLUMNS].astype(object).where(pd.notna(df[COLUMNS]), pd.NA)


def _save(df):
    df.to_csv(LOG_PATH, index=False)


def log_alert(category, code, name, interval, candle_time, action, signal_label,
              buy_votes, sell_votes, trend, close, lookahead):
    """실제로 디스코드 알림이 나간 신호를 한 줄 기록한다. 같은 캔들에 대해 중복 기록하지 않는다."""
    candle_time_str = pd.Timestamp(candle_time).isoformat()
    entry_id = f"{category}:{code}:{interval}:{candle_time_str}"
    df = _load()

    if not df.empty and (df["id"] == entry_id).any():
        return

    row = {
        "id": entry_id,
        "logged_at": pd.Timestamp.now().isoformat(),
        "category": category,
        "code": code,
        "name": name,
        "interval": interval,
        "candle_time": candle_time_str,
        "action": action,
        "signal_label": signal_label,
        "buy_votes": buy_votes,
        "sell_votes": sell_votes,
        "trend": trend,
        "close": close,
        "lookahead": lookahead,
        "status": "pending",
        "future_close": pd.NA,
        "return_pct": pd.NA,
        "resolved_at": pd.NA,
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _save(df)


def resolve_pending(ohlcv_df, category, code, interval):
    """이 종목/봉의 최신 시세(ohlcv_df)를 이용해, lookahead 캔들이 지난 대기 중인 기록의 결과(적중/실패)를 채운다."""
    df = _load()
    mask = (
        (df["category"] == category)
        & (df["code"] == str(code))
        & (df["interval"] == interval)
        & (df["status"] == "pending")
    )
    pending_idx = df[mask].index
    if len(pending_idx) == 0:
        return

    index_list = [pd.Timestamp(t).isoformat() for t in ohlcv_df.index]
    changed = False

    for idx in pending_idx:
        candle_time = df.at[idx, "candle_time"]
        lookahead = int(df.at[idx, "lookahead"])
        if candle_time not in index_list:
            continue

        pos = index_list.index(candle_time)
        target_pos = pos + lookahead
        if target_pos >= len(ohlcv_df):
            continue

        future_close = float(ohlcv_df["close"].iloc[target_pos])
        close = float(df.at[idx, "close"])
        return_pct = (future_close / close - 1) * 100

        action = df.at[idx, "action"]
        won = (return_pct > 0) if action == "매수" else (return_pct < 0)

        df.at[idx, "future_close"] = future_close
        df.at[idx, "return_pct"] = return_pct
        df.at[idx, "status"] = "win" if won else "loss"
        df.at[idx, "resolved_at"] = pd.Timestamp.now().isoformat()
        changed = True

    if changed:
        _save(df)
