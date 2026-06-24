import os
import tempfile
import uuid

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt

LOOKBACK_CANDLES_BY_INTERVAL = {"minute60": 60 * 24, "day": 60}
FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]


def _use_korean_font():
    candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


_use_korean_font()


def compute_levels(df):
    """구간 내 진짜 고가/저가를 기준으로 피보나치 조정 레벨을 계산한다."""
    high = df["high"].max()
    low = df["low"].min()
    return {
        "high": high,
        "low": low,
        "levels": {ratio: low + (high - low) * ratio for ratio in FIB_RATIOS},
    }


def render_chart(df, title):
    info = compute_levels(df)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df["close"], color="#2b6cb0", linewidth=1.2, label="종가")

    colors = ["#e53e3e", "#dd6b20", "#38a169", "#3182ce", "#805ad5"]
    for (ratio, level), color in zip(info["levels"].items(), colors):
        ax.axhline(level, linestyle="--", linewidth=0.9, color=color, alpha=0.8)
        ax.text(
            df.index[-1], level, f" {ratio * 100:.1f}% ({level:,.0f})",
            va="center", fontsize=8, color=color,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1),
        )

    current_price = df["close"].iloc[-1]
    ax.scatter(
        [df.index[-1]], [current_price], color="gold", edgecolor="black",
        zorder=5, s=60, label=f"현재가 {current_price:,.0f}",
    )

    ax.set_title(title)
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()

    path = os.path.join(tempfile.gettempdir(), f"fib_{uuid.uuid4().hex}.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
