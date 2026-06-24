from datetime import datetime, timedelta

import pandas as pd
import FinanceDataReader as fdr

_kr_listing_cache = None


def get_ohlcv(ticker, interval, count=200):
    start = (datetime.now() - timedelta(days=count * 2)).strftime("%Y-%m-%d")
    df = fdr.DataReader(ticker, start)
    if df is None or df.empty:
        raise RuntimeError(f"{ticker} ({interval}) 주가 데이터를 가져오지 못했습니다.")
    df = df.rename(columns=str.lower)
    return df.tail(count)


def _get_kr_listing():
    """KRX 일반 종목 + ETF 목록을 Code/Name 두 컬럼으로 합쳐서 반환한다(캐시됨)."""
    global _kr_listing_cache
    if _kr_listing_cache is None:
        stocks = fdr.StockListing("KRX")[["Code", "Name"]]
        etfs = fdr.StockListing("ETF/KR")[["Symbol", "Name"]].rename(columns={"Symbol": "Code"})
        _kr_listing_cache = pd.concat([stocks, etfs], ignore_index=True)
    return _kr_listing_cache


def find_kr_ticker_by_name(name):
    """회사 이름으로 한국 주식 종목을 검색해 {"code", "name"} 후보 목록을 반환한다.

    이름이 정확히 일치하는 종목이 있으면 그 하나만 반환하고,
    그렇지 않으면 이름에 포함되는 모든 종목을 후보로 반환한다.
    """
    listing = _get_kr_listing()
    exact = listing[listing["Name"] == name]
    if not exact.empty:
        matches = exact
    else:
        matches = listing[listing["Name"].str.contains(name, na=False)]
    return [
        {"code": row["Code"], "name": row["Name"]}
        for _, row in matches[["Code", "Name"]].iterrows()
    ]
