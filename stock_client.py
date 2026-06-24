from datetime import datetime, timedelta

import FinanceDataReader as fdr

_kr_listing_cache = None
_sp500_listing_cache = None


def get_ohlcv(ticker, interval, count=200):
    start = (datetime.now() - timedelta(days=count * 2)).strftime("%Y-%m-%d")
    df = fdr.DataReader(ticker, start)
    if df is None or df.empty:
        raise RuntimeError(f"{ticker} ({interval}) 주가 데이터를 가져오지 못했습니다.")
    df = df.rename(columns=str.lower)
    return df.tail(count)


def _get_kr_listing():
    global _kr_listing_cache
    if _kr_listing_cache is None:
        _kr_listing_cache = fdr.StockListing("KRX")
    return _kr_listing_cache


def _get_sp500_listing():
    global _sp500_listing_cache
    if _sp500_listing_cache is None:
        _sp500_listing_cache = fdr.StockListing("S&P500")
    return _sp500_listing_cache


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


def is_sp500_member(symbol):
    listing = _get_sp500_listing()
    return symbol.upper() in listing["Symbol"].str.upper().values
