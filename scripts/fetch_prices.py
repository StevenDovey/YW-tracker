#!/usr/bin/env python3
"""Fetch 2y daily price history for every ticker in data/holdings.json
and write it to data/prices.json. Runs server-side (GitHub Actions),
so it talks to Yahoo Finance directly with no CORS proxy involved.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLDINGS_FILE = ROOT / "data" / "holdings.json"
OUTPUT_FILE = ROOT / "data" / "prices.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch_ticker(ticker):
    quoted = urllib.parse.quote(ticker)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quoted}?range=2y&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.load(resp)
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return None
    result = result[0]
    timestamps = result.get("timestamp") or []
    closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    dates, prices = [], []
    for ts, close in zip(timestamps, closes):
        if close is not None:
            dates.append(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
            prices.append(round(close, 4))
    if len(prices) < 2:
        return None
    return {"dates": dates, "closes": prices}


def main():
    holdings = json.loads(HOLDINGS_FILE.read_text())
    prices = {}
    failed = []
    for h in holdings:
        ticker = h["ticker"]
        try:
            series = fetch_ticker(ticker)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            series = None
            print(f"failed {ticker}: {exc}")
        if series is None:
            failed.append(ticker)
        else:
            prices[ticker] = series
        time.sleep(0.3)

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prices": prices,
    }
    OUTPUT_FILE.write_text(json.dumps(output, separators=(",", ":")))
    print(f"wrote {len(prices)}/{len(holdings)} tickers, {len(failed)} failed: {failed}")


if __name__ == "__main__":
    main()
