"""signal_log.csv에 쌓인 실제 알림 기록을 분석해서 종목/조건별 적중률을 보여준다.

실제로 봇이 디스코드에 보낸 알림만 기록되고(2표 이상 필터 등 실제 로직 그대로 반영됨),
lookahead 캔들이 지나면 자동으로 결과(win/loss)가 채워진다.
몇 달 뒤 아래처럼 실행해서 확인하면 된다:

    python analyze_signal_log.py
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pandas as pd

import signal_log


def main():
    df = signal_log._load()
    if df.empty:
        print("아직 기록된 알림이 없습니다.")
        return

    df["buy_votes"] = pd.to_numeric(df["buy_votes"], errors="coerce")
    df["sell_votes"] = pd.to_numeric(df["sell_votes"], errors="coerce")
    df["return_pct"] = pd.to_numeric(df["return_pct"], errors="coerce")

    n_pending = (df["status"] == "pending").sum()
    resolved = df[df["status"].isin(["win", "loss"])].copy()

    print(f"전체 기록: {len(df)}건 (결과 대기중 {n_pending}건, 결과 확정 {len(resolved)}건)")
    if resolved.empty:
        print("아직 결과가 확정된 알림이 없습니다. lookahead 기간이 지나야 결과가 채워집니다.")
        return

    print()
    print("=== 종목/봉별 ===")
    group_cols = ["category", "name", "interval"]
    for keys, g in resolved.groupby(group_cols):
        n = len(g)
        win = (g["status"] == "win").sum()
        avg_ret = g["return_pct"].mean()
        print(f"{keys}: 표본 {n}건, 적중률 {win/n*100:.1f}%, 평균 가격변동 {avg_ret:.2f}%")

    print()
    print("=== 카테고리별 합계 ===")
    for cat, g in resolved.groupby("category"):
        n = len(g)
        win = (g["status"] == "win").sum()
        avg_ret = g["return_pct"].mean()
        print(f"{cat}: 표본 {n}건, 적중률 {win/n*100:.1f}%, 평균 가격변동 {avg_ret:.2f}%")

    print()
    print("=== 전체 합계 ===")
    n = len(resolved)
    win = (resolved["status"] == "win").sum()
    avg_ret = resolved["return_pct"].mean()
    print(f"표본 {n}건, 적중률 {win/n*100:.1f}%, 평균 가격변동 {avg_ret:.2f}%")


if __name__ == "__main__":
    main()
