import argparse
import json
from pathlib import Path

from src.agents.agent import analyze_company


def main():
    parser = argparse.ArgumentParser(description="Analyze a public SEC 10-K filing.")
    parser.add_argument("--ticker", default="MSFT")
    parser.add_argument("--fiscal-year", type=int, default=2025)
    args = parser.parse_args()
    result = analyze_company(args.ticker, args.fiscal_year)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    output = Path("output")
    output.mkdir(exist_ok=True)
    target = output / f"analysis_{args.ticker.upper()}_{args.fiscal_year}.json"
    target.write_text(rendered, encoding="utf-8")
    print(f"Saved result to {target}")


if __name__ == "__main__":
    main()
