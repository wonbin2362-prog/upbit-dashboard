"""signal_log.csv에 쌓인 실제 알림 기록을 분석해서 종목/조건별 적중률을 보여준다.

실제로 봇이 디스코드에 보낸 알림만 기록되고(2표 이상 필터 등 실제 로직 그대로 반영됨),
lookahead 캔들이 지나면 자동으로 결과(win/loss)가 채워진다.
몇 달 뒤 아래처럼 실행해서 확인하면 된다:

    python analyze_signal_log.py
"""
import io
import math
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pandas as pd

import signal_log

Z_95 = 1.96  # 95% 신뢰수준


def wilson_ci(wins, n, z=Z_95):
    """이항분포 적중률의 95% 신뢰구간(Wilson score interval). scipy 없이 계산."""
    if n == 0:
        return (0.0, 0.0)
    phat = wins / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return (max(0.0, center - margin), min(1.0, center + margin))


def format_group(n, win):
    wr = win / n * 100
    low, high = wilson_ci(win, n)
    verdict = "우연(50%)보다 유의미하게 좋음" if low > 0.5 else "우연과 통계적으로 구별 안 됨"
    return f"표본 {n}건, 적중률 {wr:.1f}% (95% 신뢰구간 {low*100:.1f}~{high*100:.1f}%) -> {verdict}"


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
        print(f"{keys}: {format_group(n, win)}, 평균 가격변동 {avg_ret:.2f}%")

    print()
    print("=== 카테고리별 합계 ===")
    for cat, g in resolved.groupby("category"):
        n = len(g)
        win = (g["status"] == "win").sum()
        avg_ret = g["return_pct"].mean()
        print(f"{cat}: {format_group(n, win)}, 평균 가격변동 {avg_ret:.2f}%")

    print()
    print("=== 전체 합계 ===")
    n = len(resolved)
    win = (resolved["status"] == "win").sum()
    avg_ret = resolved["return_pct"].mean()
    print(f"{format_group(n, win)}, 평균 가격변동 {avg_ret:.2f}%")
    print()
    print(
        "※ '유의미하게 좋음'은 95% 신뢰구간 하한이 50%를 넘는다는 뜻으로, "
        "우연(동전 던지기)이 아니라고 통계적으로 어느 정도 확신할 수 있다는 의미입니다.\n"
        "  표본이 적으면(수십 건) 적중률이 60~70%로 보여도 신뢰구간이 넓어서 '구별 안 됨'으로 나올 수 있습니다.\n"
        "  또한 적중률이 통계적으로 확인되더라도, 수수료/슬리피지와 손익비(평균수익 vs 평균손실)를 "
        "함께 봐야 실제로 돈을 버는지 알 수 있습니다."
    )


if __name__ == "__main__":
    main()
