import json
import os

import stock_client

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
CATEGORIES = ["crypto", "kr_stock"]


def _load():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "tickers" in data:
        data = {
            "crypto": {"tickers": data["tickers"], "intervals": data["intervals"]},
            "kr_stock": {"tickers": [], "intervals": ["day"]},
        }
        _save(data)

    return data


def _save(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_tickers(category):
    return _load()[category]["tickers"]


def get_intervals(category):
    return _load()[category]["intervals"]


def add_ticker(category, value):
    """감시 목록에 항목을 추가한다. (성공여부, 안내 메시지)를 반환한다."""
    data = _load()

    if category == "crypto":
        ticker = value.upper()
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        if ticker in data["crypto"]["tickers"]:
            return False, f"{ticker} 는 이미 감시 목록에 있습니다."
        data["crypto"]["tickers"].append(ticker)
        added_label = ticker

    elif category == "kr_stock":
        candidates = stock_client.find_kr_ticker_by_name(value)
        existing_codes = {t["code"] for t in data["kr_stock"]["tickers"]}
        if not candidates:
            return False, f"'{value}' 에 해당하는 종목을 찾지 못했습니다."
        if len(candidates) > 1:
            names = ", ".join(f"{c['name']}({c['code']})" for c in candidates)
            return False, f"'{value}' 에 해당하는 종목이 여러 개입니다: {names}. 더 정확한 이름으로 다시 시도해주세요."
        candidate = candidates[0]
        if candidate["code"] in existing_codes:
            return False, f"{candidate['name']}({candidate['code']}) 는 이미 감시 목록에 있습니다."
        data["kr_stock"]["tickers"].append(candidate)
        added_label = f"{candidate['name']}({candidate['code']})"

    else:
        raise ValueError(f"알 수 없는 카테고리: {category}")

    _save(data)
    return True, f"{added_label} 추가됨. 현재 목록: {data[category]['tickers']}"


def remove_ticker(category, value):
    """감시 목록에서 항목을 제거한다. (성공여부, 안내 메시지)를 반환한다."""
    data = _load()
    tickers = data[category]["tickers"]

    if category == "kr_stock":
        before = len(tickers)
        tickers[:] = [t for t in tickers if t["code"] != value and t["name"] != value]
        if len(tickers) == before:
            return False, f"{value} 는 감시 목록에 없습니다."
    else:
        ticker = value.upper()
        if category == "crypto" and not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        if ticker not in tickers:
            return False, f"{ticker} 는 감시 목록에 없습니다."
        tickers.remove(ticker)

    _save(data)
    return True, f"{value} 제거됨. 현재 목록: {data[category]['tickers']}"


def list_tickers(category):
    tickers = get_tickers(category)
    print(f"현재 감시 목록 ({category}):")
    for t in tickers:
        if category == "kr_stock":
            print(f"  - {t['name']}({t['code']})")
        else:
            print(f"  - {t}")
