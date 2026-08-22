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
# 신호 1개만으로는 판단이 애매해서, 카테고리별로 최소 몇 표가 모여야 알림을 보낼지 정한다.
# (미지정 카테고리는 기본값 1표 = 기존 동작 그대로)
MIN_VOTES_BY_CATEGORY = {"crypto": 2}


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


def check_and_notify(webhook_by_category, webhook_by_ticker=None):
    webhook_by_ticker = webhook_by_ticker or {}
    state = _load_state()

    for category in categories.CATEGORIES:
        default_webhook = webhook_by_category.get(category)

        tickers = watchlist.get_tickers(category)
        intervals = watchlist.get_intervals(category)
        client = categories.CLIENT_BY_CATEGORY[category]

        for ticker in tickers:
            code = categories.ticker_code(category, ticker)
            name = categories.ticker_display_name(category, ticker)
            webhook_url = webhook_by_ticker.get((category, code), default_webhook)
            if not webhook_url:
                continue

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
                votes = max(result["buy_votes"], result["sell_votes"])
                min_votes = MIN_VOTES_BY_CATEGORY.get(category, 1)
                is_alertable = combined in ALERT_SIGNALS and votes >= min_votes

                if is_alertable and combined != prev_signal:
                    label = INTERVAL_LABELS.get(interval, interval)
                    price = categories.format_price(result["close"])
                    action = "매수" if "매수" in combined else "매도"
                    emoji = "🟢" if action == "매수" else "🔴"
                    reasons = " / ".join(result["messages"]) if result["messages"] else combined
                    message = (
                        f"{emoji} [{action} 신호] {name} {label}\n"
                        f"{combined} (매수 {result['buy_votes']}표 : 매도 {result['sell_votes']}표) · 종가 {price}\n"
                        f"근거: {reasons}"
                    )
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

                # 표수 미달로 알림을 보내지 않은 경우엔 상태를 갱신하지 않는다.
                # 그래야 나중에 표수가 채워지면(같은 신호라도) 그때 알림이 나간다.
                if is_alertable or combined not in ALERT_SIGNALS:
                    state[key] = combined

    _save_state(state)


if __name__ == "__main__":
    crypto_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    stock_webhook = os.environ.get("DISCORD_WEBHOOK_URL_STOCK") or crypto_webhook

    if not crypto_webhook:
        raise SystemExit("DISCORD_WEBHOOK_URL 환경변수가 설정되어 있지 않습니다.")

    # 코인별 전용 채널 웹훅이 설정되어 있으면 그 코인만 해당 채널로 보내고,
    # 없으면 기존처럼 공용 crypto 채널(DISCORD_WEBHOOK_URL)로 보낸다.
    webhook_by_ticker = {}
    ticker_env_map = {
        "KRW-BTC": "DISCORD_WEBHOOK_URL_BTC",
        "KRW-ETH": "DISCORD_WEBHOOK_URL_ETH",
        "KRW-WLD": "DISCORD_WEBHOOK_URL_WLD",
    }
    for ticker, env_name in ticker_env_map.items():
        url = os.environ.get(env_name)
        if url:
            webhook_by_ticker[("crypto", ticker)] = url

    # 한국주식도 종목별 전용 채널 웹훅이 설정되어 있으면 그 종목만 해당 채널로 보낸다.
    stock_ticker_env_map = {
        "000660": "DISCORD_WEBHOOK_URL_HYNIX",
    }
    for code, env_name in stock_ticker_env_map.items():
        url = os.environ.get(env_name)
        if url:
            webhook_by_ticker[("kr_stock", code)] = url

    check_and_notify(
        {
            "crypto": crypto_webhook,
            "kr_stock": stock_webhook,
        },
        webhook_by_ticker,
    )
