import argparse
import io
import sys
import time
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import watchlist
import upbit_client
import indicators
import signals
import backtest

INTERVAL_LABELS = {
    "minute60": "1시간봉",
    "day": "일봉",
}


def check_once():
    tickers = watchlist.get_tickers()
    intervals = watchlist.get_intervals()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n===== {now} 분석 결과 =====")

    for ticker in tickers:
        for interval in intervals:
            label = INTERVAL_LABELS.get(interval, interval)
            count = backtest.BACKTEST_COUNT_BY_INTERVAL.get(interval, 200)
            lookahead = backtest.LOOKAHEAD_BY_INTERVAL.get(interval, 5)
            try:
                df = upbit_client.get_ohlcv(ticker, interval, count=count)
                df = indicators.add_indicators(df)
                result = signals.analyze(df)
            except Exception as e:
                print(f"[{ticker} / {label}] 오류: {e}")
                continue

            if result is None:
                continue

            status = (
                f"[{ticker} / {label}] 종가={result['close']:.2f} "
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
    parser = argparse.ArgumentParser(description="업비트 RSI/MACD 신호 알리미")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="감시 중인 코인 목록 출력")

    add_p = sub.add_parser("add", help="감시 코인 추가")
    add_p.add_argument("ticker", help="예: BTC, ETH, WLD 또는 KRW-BTC")

    remove_p = sub.add_parser("remove", help="감시 코인 제거")
    remove_p.add_argument("ticker", help="예: BTC, ETH, WLD 또는 KRW-BTC")

    run_p = sub.add_parser("run", help="신호 감시 실행")
    run_p.add_argument("--once", action="store_true", help="한 번만 분석하고 종료")
    run_p.add_argument(
        "--loop-minutes", type=int, default=5, help="반복 주기(분), 기본 5분"
    )

    args = parser.parse_args()

    if args.command == "list":
        watchlist.list_tickers()
    elif args.command == "add":
        watchlist.add_ticker(args.ticker)
    elif args.command == "remove":
        watchlist.remove_ticker(args.ticker)
    elif args.command == "run":
        if args.once:
            check_once()
        else:
            run_loop(args.loop_minutes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
