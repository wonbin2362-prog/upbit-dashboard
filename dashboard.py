from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import watchlist
import indicators
import signals
import backtest
import categories

INTERVAL_LABELS = {
    "minute60": "1시간봉",
    "day": "일봉",
}

st.set_page_config(page_title="코인/주식 RSI/MACD 대시보드", layout="wide")


@st.cache_data(ttl=300)
def load_analysis(category, code, interval):
    client = categories.CLIENT_BY_CATEGORY[category]
    count = backtest.BACKTEST_COUNT_BY_INTERVAL.get(interval, 200)
    df = client.get_ohlcv(code, interval, count=count)
    df = indicators.add_indicators(df)
    result = signals.analyze(df)
    return df, result


def _fetch_one(category, ticker, interval):
    code = categories.ticker_code(category, ticker)
    name = categories.ticker_display_name(category, ticker)
    label = INTERVAL_LABELS.get(interval, interval)
    try:
        _, result = load_analysis(category, code, interval)
    except Exception as e:
        return {
            "종목": name,
            "주기": label,
            "종가": None,
            "RSI": None,
            "MACD": None,
            "SIGNAL": None,
            "종합신호": f"오류: {e}",
            "승률": "-",
            "세부": "-",
        }

    if result is None:
        return None

    combined = result["combined_signal"]
    win_text = "-"
    if combined != "중립":
        lookahead = backtest.LOOKAHEAD_BY_INTERVAL.get(interval, 5)
        stats = backtest.compute_winrate(result["labeled_df"], lookahead)
        stat = stats.get(combined)
        if stat and stat["count"] > 0:
            win_text = (
                f"{stat['win_rate'] * 100:.1f}% "
                f"(과거 {stat['count']}회, 평균 {stat['avg_return'] * 100:.2f}%)"
            )
        else:
            win_text = "데이터 부족"

    return {
        "종목": name,
        "주기": label,
        "종가": categories.format_price(result["close"]),
        "RSI": round(result["rsi"], 1),
        "MACD": round(result["macd"], 2),
        "SIGNAL": round(result["macd_signal"], 2),
        "종합신호": combined,
        "승률": win_text,
        "세부": " / ".join(result["messages"]) if result["messages"] else "-",
    }


def build_summary_rows(category, tickers, intervals):
    pairs = [(category, ticker, interval) for ticker in tickers for interval in intervals]
    with ThreadPoolExecutor(max_workers=min(8, len(pairs))) as executor:
        results = list(executor.map(lambda p: _fetch_one(*p), pairs))
    rows = [r for r in results if r is not None]
    return pd.DataFrame(rows)


def highlight_signal(row):
    label = row["종합신호"]
    if label == "강한 매수":
        return ["background-color: #1f5c1f"] * len(row)
    if label == "약한 매수":
        return ["background-color: #1f3d1f"] * len(row)
    if label == "강한 매도":
        return ["background-color: #6e1f1f"] * len(row)
    if label == "약한 매도":
        return ["background-color: #4a1f1f"] * len(row)
    return [""] * len(row)


def render_chart(category, code, interval):
    df, _ = load_analysis(category, code, interval)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.03,
        subplot_titles=("가격", "RSI", "MACD"),
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="가격",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI", line=dict(color="orange")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD", line=dict(color="blue")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal", line=dict(color="red")), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Histogram"), row=3, col=1)

    fig.update_layout(height=450, xaxis_rangeslider_visible=False, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


def render_crypto_sidebar():
    with st.sidebar:
        st.header("감시 코인 관리")
        tickers = watchlist.get_tickers("crypto")
        st.write("현재 목록:", ", ".join(tickers))

        new_ticker = st.text_input("추가할 코인 (예: SOL)")
        if st.button("추가", key="crypto_add"):
            ok, message = watchlist.add_ticker("crypto", new_ticker)
            (st.success if ok else st.error)(message)
            if ok:
                st.cache_data.clear()
                st.rerun()

        remove_target = st.selectbox("삭제할 코인", options=tickers if tickers else ["-"])
        if st.button("삭제", key="crypto_remove") and tickers:
            ok, message = watchlist.remove_ticker("crypto", remove_target)
            (st.success if ok else st.error)(message)
            if ok:
                st.cache_data.clear()
                st.rerun()


def render_auto_refresh_sidebar():
    with st.sidebar:
        st.divider()
        auto_refresh_default = st.query_params.get("auto_refresh", "0") == "1"
        refresh_sec_default = int(st.query_params.get("refresh_sec", 60))

        auto_refresh = st.checkbox("자동 새로고침", value=auto_refresh_default)
        refresh_sec = st.number_input(
            "새로고침 주기(초)", min_value=10, value=refresh_sec_default, step=10
        )
        st.query_params["auto_refresh"] = "1" if auto_refresh else "0"
        st.query_params["refresh_sec"] = str(refresh_sec)

        if st.button("지금 새로고침"):
            st.cache_data.clear()
            st.rerun()

    return auto_refresh, refresh_sec


def render_stock_manager(category, add_label, add_help):
    tickers = watchlist.get_tickers(category)
    display_list = ", ".join(categories.ticker_display_name(category, t) for t in tickers)
    st.write("현재 목록:", display_list if tickers else "(없음)")

    col1, col2 = st.columns([3, 1])
    with col1:
        new_value = st.text_input(add_label, help=add_help, key=f"{category}_input")
    with col2:
        st.write("")
        st.write("")
        if st.button("추가", key=f"{category}_add") and new_value:
            ok, message = watchlist.add_ticker(category, new_value)
            (st.success if ok else st.error)(message)
            if ok:
                st.cache_data.clear()
                st.rerun()

    if tickers:
        remove_target = st.selectbox(
            "삭제할 종목",
            options=tickers,
            format_func=lambda t: categories.ticker_display_name(category, t),
            key=f"{category}_remove_select",
        )
        if st.button("삭제", key=f"{category}_remove"):
            remove_value = remove_target["code"] if category == "kr_stock" else remove_target
            ok, message = watchlist.remove_ticker(category, remove_value)
            (st.success if ok else st.error)(message)
            if ok:
                st.cache_data.clear()
                st.rerun()


def render_category_tab(category):
    if category == "kr_stock":
        render_stock_manager(category, "추가할 종목 (회사 이름, 예: 삼성전자)", "정확한 회사 이름으로 검색합니다.")

    tickers = watchlist.get_tickers(category)
    intervals = watchlist.get_intervals(category)

    if not tickers:
        st.info("감시 중인 종목이 없습니다. 위에서 추가해주세요.")
        return

    st.subheader("요약")
    with st.spinner("데이터를 불러오는 중입니다... (처음 로딩은 몇 초 걸릴 수 있어요)"):
        summary_df = build_summary_rows(category, tickers, intervals)
    if not summary_df.empty:
        st.dataframe(summary_df.style.apply(highlight_signal, axis=1), use_container_width=True)

    st.subheader("상세 차트")
    col1, col2 = st.columns(2)
    with col1:
        sel_ticker = st.selectbox(
            "종목 선택",
            options=tickers,
            format_func=lambda t: categories.ticker_display_name(category, t),
            key=f"{category}_chart_ticker",
        )
    with col2:
        sel_interval = st.selectbox(
            "주기 선택",
            options=intervals,
            format_func=lambda x: INTERVAL_LABELS.get(x, x),
            key=f"{category}_chart_interval",
        )
    sel_code = categories.ticker_code(category, sel_ticker)
    with st.spinner("차트를 그리는 중입니다..."):
        render_chart(category, sel_code, sel_interval)


def main():
    st.title("코인 / 주식 RSI · MACD 대시보드")

    render_crypto_sidebar()
    auto_refresh, refresh_sec = render_auto_refresh_sidebar()

    tab_crypto, tab_kr = st.tabs(["코인", "한국주식"])

    with tab_crypto:
        render_category_tab("crypto")
    with tab_kr:
        render_category_tab("kr_stock")

    if auto_refresh:
        st.caption(f"{refresh_sec}초마다 자동으로 새로고침됩니다.")
        st.markdown(
            f'<meta http-equiv="refresh" content="{refresh_sec}">',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
