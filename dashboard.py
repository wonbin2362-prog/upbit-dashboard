from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import watchlist
import upbit_client
import indicators
import signals
import backtest

INTERVAL_LABELS = {
    "minute60": "1시간봉",
    "day": "일봉",
}

st.set_page_config(page_title="업비트 RSI/MACD 대시보드", layout="wide")


@st.cache_data(ttl=300)
def load_analysis(ticker, interval):
    count = backtest.BACKTEST_COUNT_BY_INTERVAL.get(interval, 200)
    df = upbit_client.get_ohlcv(ticker, interval, count=count)
    df = indicators.add_indicators(df)
    result = signals.analyze(df)
    return df, result


def _fetch_one(ticker, interval):
    label = INTERVAL_LABELS.get(interval, interval)
    try:
        _, result = load_analysis(ticker, interval)
    except Exception as e:
        return {
            "코인": ticker,
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
        "코인": ticker,
        "주기": label,
        "종가": result["close"],
        "RSI": round(result["rsi"], 1),
        "MACD": round(result["macd"], 2),
        "SIGNAL": round(result["macd_signal"], 2),
        "종합신호": combined,
        "승률": win_text,
        "세부": " / ".join(result["messages"]) if result["messages"] else "-",
    }


def build_summary_rows(tickers, intervals):
    pairs = [(ticker, interval) for ticker in tickers for interval in intervals]
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


def render_chart(ticker, interval):
    df, _ = load_analysis(ticker, interval)

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


def main():
    st.title("업비트 RSI / MACD 대시보드")

    with st.sidebar:
        st.header("감시 코인 관리")
        tickers = watchlist.get_tickers()
        st.write("현재 목록:", ", ".join(tickers))

        new_ticker = st.text_input("추가할 코인 (예: SOL)")
        if st.button("추가"):
            watchlist.add_ticker(new_ticker)
            st.cache_data.clear()
            st.rerun()

        remove_target = st.selectbox("삭제할 코인", options=tickers if tickers else ["-"])
        if st.button("삭제") and tickers:
            watchlist.remove_ticker(remove_target)
            st.cache_data.clear()
            st.rerun()

        st.divider()
        auto_refresh = st.checkbox("자동 새로고침", value=False)
        refresh_sec = st.number_input("새로고침 주기(초)", min_value=10, value=60, step=10)
        if st.button("지금 새로고침"):
            st.cache_data.clear()
            st.rerun()

    tickers = watchlist.get_tickers()
    intervals = watchlist.get_intervals()

    if not tickers:
        st.info("감시 중인 코인이 없습니다. 사이드바에서 추가해주세요.")
        return

    st.subheader("요약")
    with st.spinner("데이터를 불러오는 중입니다... (처음 로딩은 몇 초 걸릴 수 있어요)"):
        summary_df = build_summary_rows(tickers, intervals)
    if not summary_df.empty:
        st.dataframe(summary_df.style.apply(highlight_signal, axis=1), use_container_width=True)

    st.subheader("상세 차트")
    col1, col2 = st.columns(2)
    with col1:
        sel_ticker = st.selectbox("코인 선택", options=tickers)
    with col2:
        sel_interval = st.selectbox(
            "주기 선택", options=intervals, format_func=lambda x: INTERVAL_LABELS.get(x, x)
        )
    with st.spinner("차트를 그리는 중입니다..."):
        render_chart(sel_ticker, sel_interval)

    if auto_refresh:
        st.caption(f"{refresh_sec}초마다 자동으로 새로고침됩니다.")
        st.markdown(
            f'<meta http-equiv="refresh" content="{refresh_sec}">',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
