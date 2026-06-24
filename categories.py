import stock_client
import upbit_client

CATEGORIES = ["crypto", "kr_stock", "us_stock"]

CATEGORY_LABELS = {
    "crypto": "코인",
    "kr_stock": "한국주식",
    "us_stock": "미국주식",
}

CLIENT_BY_CATEGORY = {
    "crypto": upbit_client,
    "kr_stock": stock_client,
    "us_stock": stock_client,
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


def format_price(category, price):
    if category == "us_stock":
        return f"${price:,.2f}"
    return f"{price:,.0f}원"
