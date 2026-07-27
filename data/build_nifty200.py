"""
Generate data/nifty200.py from official NSE + Upstox data.
"""

import csv
import gzip
import json
import requests

UPSTOX_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
NIFTY200_URL = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def download_json_gz(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return json.loads(gzip.decompress(response.content))


def download_csv(url):
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return list(csv.DictReader(response.text.splitlines()))


def main():
    print("Downloading Upstox instrument master...")
    instruments = download_json_gz(UPSTOX_URL)

    print("Downloading NIFTY 200 constituents...")
    constituents = download_csv(NIFTY200_URL)

    wanted = {
        row["Symbol"].strip().upper()
        for row in constituents
    }

    symbol_map = {}

    for inst in instruments:
        if (
            inst.get("exchange") == "NSE"
            and inst.get("instrument_type") == "EQ"
        ):
            symbol = inst.get("trading_symbol", "").strip().upper()

            if symbol in wanted:
                symbol_map[inst["instrument_key"]] = symbol

    print(f"Matched {len(symbol_map)} stocks")

    with open("data/nifty200.py", "w") as f:
        f.write('"""\n')
        f.write("Auto-generated. Do not edit.\n")
        f.write('"""\n\n')

        f.write("SYMBOL_MAP = {\n")

        for key, symbol in sorted(symbol_map.items(), key=lambda x: x[1]):
            f.write(f'    "{key}": "{symbol}",\n')
        f.write("}\n\n")
        f.write("NIFTY200 = list(SYMBOL_MAP.keys())\n")

    print("Generated data/nifty200.py successfully.")


if __name__ == "__main__":
    main()
