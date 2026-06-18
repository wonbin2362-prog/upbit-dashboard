import json
import os

import requests

import indicators
import signals
import upbit_client
import watchlist
import backtest

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_state.json")
INTERVAL_LABELS = {
    "minute60": "1시간봉",
    "day": "일봉",
}
ALERT_SIGNALS = {"강한 매수", "약한 매수", "강한 매도", "약한 매도"}


def _load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


def _send_discord(webhook_url, content):
    response = requests.post(webhook_url, json={"content": content}, timeout=10)
    response.raise_for_status()


def check_and_notify(webhook_url):
    state = _load_state()
    tickers = watchlist.get_tickers()
    intervals = watchlist.get_intervals()

    for ticker in tickers:
        for interval in intervals:
            key = f"{ticker}:{interval}"
            count = backtest.BACKTEST_COUNT_BY_INTERVAL.get(interval, 200)

            try:
                df = upbit_client.get_ohlcv(ticker, interval, count=count)
                df = indicators.add_indicators(df)
                result = signals.analyze(df)
            except Exception as e:
                print(f"[오류] {key}: {e}")
                continue

            if result is None:
                continue

            combined = result["combined_signal"]
            prev_signal = state.get(key)

            if combined in ALERT_SIGNALS and combined != prev_signal:
                label = INTERVAL_LABELS.get(interval, interval)
                message = (
                    f"[{ticker} / {label}] {combined}\n"
                    f"종가: {result['close']:.2f} / RSI: {result['rsi']:.1f} / "
                    f"MACD: {result['macd']:.2f} / SIGNAL: {result['macd_signal']:.2f}\n"
                    f"{' / '.join(result['messages']) if result['messages'] else ''}"
                )
                print(f"[알림] {message}")
                _send_discord(webhook_url, message)

            state[key] = combined

    _save_state(state)


if __name__ == "__main__":
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise SystemExit("DISCORD_WEBHOOK_URL 환경변수가 설정되어 있지 않습니다.")
    check_and_notify(webhook)
