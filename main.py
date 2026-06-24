import argparse
import io
import sys
import time
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import watchlist
import indicators
import signals
import backtest
import categories

INTERVAL_LABELS = {
    "minute60": "1시간봉",
    "day": "일봉",
}


def check_once():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n===== {now} 분석 결과 =====")

    for category in categories.CATEGORIES:
        tickers = watchlist.get_tickers(category)
        intervals = watchlist.get_intervals(category)
        client = categories.CLIENT_BY_CATEGORY[category]
        cat_label = categories.CATEGORY_LABELS[category]

        for ticker in tickers:
            code = categories.ticker_code(category, ticker)
            name = categories.ticker_display_name(category, ticker)

            for interval in intervals:
                label = INTERVAL_LABELS.get(interval, interval)
                count = backtest.BACKTEST_COUNT_BY_INTERVAL.get(interval, 200)
                lookahead = backtest.LOOKAHEAD_BY_INTERVAL.get(interval, 5)
                try:
                    df = client.get_ohlcv(code, interval, count=count)
                    df = indicators.add_indicators(df)
                    result = signals.analyze(df)
                except Exception as e:
                    print(f"[{cat_label} / {name} / {label}] 오류: {e}")
                    continue

                if result is None:
                    continue

                status = (
                    f"[{cat_label} / {name} / {label}] "
                    f"종가={categories.format_price(result['close'])} "
                    f"RSI={result['rsi']:.1f} "
                    f"MACD={result['macd']:.2f} SIGNAL={result['macd_signal']:.2f}"
                )
                print(status)

                combined = result["combined_signal"]
                if combined != "중립":
                    stats = backtest.compute_winrate(result["labeled_df"], lookahead)
                    stat = stats.get(combined)
                    if stat and stat["count"] > 0:
                        print(
                            f"  >> 종합 신호: {combined} "
                            f"(과거 {stat['count']}회 중 적중 {stat['win_rate'] * 100:.1f}%, "
                            f"평균수익률 {stat['avg_return'] * 100:.2f}%, {lookahead}캔들 기준)"
                        )
                    else:
                        print(f"  >> 종합 신호: {combined} (과거 데이터 부족으로 통계 없음)")

                for msg in result["messages"]:
                    print(f"     - {msg}")


def run_loop(loop_minutes):
    print(f"감시를 시작합니다. {loop_minutes}분마다 갱신합니다. (Ctrl+C로 종료)")
    while True:
        check_once()
        time.sleep(loop_minutes * 60)


def main():
    parser = argparse.ArgumentParser(description="코인/주식 RSI/MACD 신호 알리미")
    sub = parser.add_subparsers(dest="command")

    list_p = sub.add_parser("list", help="감시 목록 출력")
    list_p.add_argument(
        "category", choices=categories.CATEGORIES, help="crypto, kr_stock"
    )

    add_p = sub.add_parser("add", help="감시 항목 추가")
    add_p.add_argument(
        "category", choices=categories.CATEGORIES, help="crypto, kr_stock"
    )
    add_p.add_argument(
        "value",
        help="crypto: BTC 등 / kr_stock: 회사 이름(예: 삼성전자)",
    )

    remove_p = sub.add_parser("remove", help="감시 항목 제거")
    remove_p.add_argument(
        "category", choices=categories.CATEGORIES, help="crypto, kr_stock"
    )
    remove_p.add_argument("value", help="add와 동일한 형식")

    run_p = sub.add_parser("run", help="신호 감시 실행")
    run_p.add_argument("--once", action="store_true", help="한 번만 분석하고 종료")
    run_p.add_argument(
        "--loop-minutes", type=int, default=5, help="반복 주기(분), 기본 5분"
    )

    args = parser.parse_args()

    if args.command == "list":
        watchlist.list_tickers(args.category)
    elif args.command == "add":
        _, message = watchlist.add_ticker(args.category, args.value)
        print(message)
    elif args.command == "remove":
        _, message = watchlist.remove_ticker(args.category, args.value)
        print(message)
    elif args.command == "run":
        if args.once:
            check_once()
        else:
            run_loop(args.loop_minutes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
