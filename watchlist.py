import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _load():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_tickers():
    return _load()["tickers"]


def get_intervals():
    return _load()["intervals"]


def add_ticker(ticker):
    ticker = ticker.upper()
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    data = _load()
    if ticker in data["tickers"]:
        print(f"{ticker} 는 이미 감시 목록에 있습니다.")
        return
    data["tickers"].append(ticker)
    _save(data)
    print(f"{ticker} 추가됨. 현재 목록: {data['tickers']}")


def remove_ticker(ticker):
    ticker = ticker.upper()
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    data = _load()
    if ticker not in data["tickers"]:
        print(f"{ticker} 는 감시 목록에 없습니다.")
        return
    data["tickers"].remove(ticker)
    _save(data)
    print(f"{ticker} 제거됨. 현재 목록: {data['tickers']}")


def list_tickers():
    tickers = get_tickers()
    print("현재 감시 코인 목록:")
    for t in tickers:
        print(f"  - {t}")
