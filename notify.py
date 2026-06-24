import json
import os

import requests

import indicators
import signals
import watchlist
import backtest
import categories
import fibonacci

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


def _send_discord_with_image(webhook_url, content, image_path):
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/png")}
        response = requests.post(webhook_url, data={"content": content}, files=files, timeout=15)
        response.raise_for_status()


def check_and_notify(webhook_by_category):
    state = _load_state()

    for category in categories.CATEGORIES:
        webhook_url = webhook_by_category.get(category)
        if not webhook_url:
            continue

        tickers = watchlist.get_tickers(category)
        intervals = watchlist.get_intervals(category)
        client = categories.CLIENT_BY_CATEGORY[category]

        for ticker in tickers:
            code = categories.ticker_code(category, ticker)
            name = categories.ticker_display_name(category, ticker)

            for interval in intervals:
                key = f"{category}:{code}:{interval}"
                count = backtest.BACKTEST_COUNT_BY_INTERVAL.get(interval, 200)

                try:
                    df = client.get_ohlcv(code, interval, count=count)
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
                    price = categories.format_price(result["close"])
                    message = f"{name} {label} {combined} (종가 {price})"
                    print(f"[알림] {message}")

                    chart_path = None
                    try:
                        fib_count = fibonacci.LOOKBACK_CANDLES_BY_INTERVAL.get(interval, 60)
                        fib_df = client.get_ohlcv(code, interval, count=fib_count)
                        chart_path = fibonacci.render_chart(fib_df, f"{name} {label} 피보나치 조정대")
                        _send_discord_with_image(webhook_url, message, chart_path)
                    except Exception as e:
                        print(f"[차트 오류] {key}: {e}")
                        _send_discord(webhook_url, message)
                    finally:
                        if chart_path and os.path.exists(chart_path):
                            os.remove(chart_path)

                state[key] = combined

    _save_state(state)


if __name__ == "__main__":
    crypto_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    stock_webhook = os.environ.get("DISCORD_WEBHOOK_URL_STOCK") or crypto_webhook

    if not crypto_webhook:
        raise SystemExit("DISCORD_WEBHOOK_URL 환경변수가 설정되어 있지 않습니다.")

    check_and_notify(
        {
            "crypto": crypto_webhook,
            "kr_stock": stock_webhook,
        }
    )
