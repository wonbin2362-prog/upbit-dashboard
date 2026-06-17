import time

import pandas as pd
import pyupbit


def get_ohlcv(ticker, interval, count=200):
    if count <= 200:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
        if df is None or df.empty:
            raise RuntimeError(f"{ticker} ({interval}) 캔들 데이터를 가져오지 못했습니다.")
        return df
    return _get_ohlcv_extended(ticker, interval, count)


def _get_ohlcv_extended(ticker, interval, total_count):
    chunks = []
    to = None
    remaining = total_count

    while remaining > 0:
        request_count = min(remaining, 200)
        chunk = pyupbit.get_ohlcv(ticker, interval=interval, count=request_count, to=to)
        if chunk is None or chunk.empty:
            break
        chunks.append(chunk)
        to = chunk.index[0].strftime("%Y-%m-%d %H:%M:%S")
        remaining -= len(chunk)
        if len(chunk) < request_count:
            break
        time.sleep(0.1)

    if not chunks:
        raise RuntimeError(f"{ticker} ({interval}) 캔들 데이터를 가져오지 못했습니다.")

    full = pd.concat(list(reversed(chunks)))
    return full[~full.index.duplicated(keep="first")]
