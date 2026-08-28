#!/usr/bin/env python3
"""Fetch new BNZ YouWealth unit prices and append them to data/fund-prices.json.
Runs server-side (GitHub Actions) so the page never needs to call BNZ's API
from the visitor's browser or cache anything in localStorage.
"""
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "fund-prices.json"

API_KEY = "vjqaLG3y07VHpZnIe8nYX808FGPYid8G"
FUND_CODES = {
    "High Growth Fund": "BNZ2112012",
    "Growth Fund": "BNZ2112008",
    "Balanced Fund": "BNZ2112007",
    "Moderate Fund": "BNZ2112010",
    "Conservative Fund": "BNZ2112011",
}


def fetch_day(date_str):
    url = f"https://api.bnz.co.nz/v1/fundunitprices?date={date_str}&fundProduct=retailManagedFund"
    req = urllib.request.Request(url, headers={"ApiKey": API_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.load(resp)
    prices_by_code = {}
    for entry in payload.get("fundUnitPrices") or []:
        code = entry.get("fundCode")
        amount = (entry.get("sellPrice") or {}).get("amount")
        if code is not None and amount is not None:
            prices_by_code[code] = float(amount)
    return prices_by_code


def daterange(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def main():
    fund_data = json.loads(DATA_FILE.read_text())
    today = datetime.now(timezone.utc).date()

    last_dates = {
        fund: datetime.strptime(entries[-1][0], "%Y-%m-%d").date()
        for fund, entries in fund_data.items()
    }
    start = min(last_dates.values()) + timedelta(days=1)

    if start > today:
        print("no new business days to fetch")
        return

    fetched_days = 0
    for d in daterange(start, today):
        date_str = d.strftime("%Y-%m-%d")
        try:
            prices_by_code = fetch_day(date_str)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"failed {date_str}: {exc}")
            continue
        if not prices_by_code:
            print(f"no data for {date_str}")
            continue
        fetched_days += 1
        for fund, code in FUND_CODES.items():
            if d <= last_dates[fund]:
                continue
            price = prices_by_code.get(code)
            if price is not None:
                fund_data[fund].append([date_str, price])

    for fund in fund_data:
        fund_data[fund] = sorted(
            {entry[0]: entry[1] for entry in fund_data[fund]}.items()
        )
        fund_data[fund] = [[date, price] for date, price in fund_data[fund]]

    DATA_FILE.write_text(json.dumps(fund_data, separators=(",", ":")))
    print(f"fetched {fetched_days} business day(s) up to {today}")


if __name__ == "__main__":
    main()
