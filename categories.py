import stock_client
import upbit_client

CATEGORIES = ["crypto", "kr_stock"]

CATEGORY_LABELS = {
    "crypto": "코인",
    "kr_stock": "한국주식",
}

CLIENT_BY_CATEGORY = {
    "crypto": upbit_client,
    "kr_stock": stock_client,
}

# 특정 종목은 5개 지표 투표 시스템 대신, 이동평균 교차(골든/데드크로스)만 단순하게 본다.
# 일봉 기준 20일선/200일선 교차만 확인하며, 다른 봉 종류(minute60 등)에는 적용하지 않는다.
SIMPLE_MA_CROSS_TICKERS = {
    ("crypto", "KRW-BTC"): {"ma_short": 20, "ma_long": 200, "interval": "day"},
    ("crypto", "KRW-ETH"): {"ma_short": 20, "ma_long": 200, "interval": "day"},
}


def ticker_code(category, ticker):
    """watchlist에 저장된 항목에서 실제 데이터 조회용 코드를 뽑아낸다."""
    if category == "kr_stock":
        return ticker["code"]
    return ticker


def ticker_display_name(category, ticker):
    """사람이 읽을 표시용 이름을 뽑아낸다."""
    if category == "kr_stock":
        return ticker["name"]
    if category == "crypto":
        return ticker.replace("KRW-", "")
    return ticker


def format_price(price):
    return f"{price:,.0f}원"
