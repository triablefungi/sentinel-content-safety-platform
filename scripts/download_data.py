import argparse
from pathlib import Path

import pandas as pd
from datasets import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream a Civil Comments training sample.")
    parser.add_argument("--sample-size", type=int, default=20_000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/civil_comments_sample.csv"),
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.sample_size < 1_000:
        raise ValueError("sample-size must be at least 1,000")

    dataset = load_dataset("google/civil_comments", split="train", streaming=True)
    dataset = dataset.shuffle(seed=args.seed, buffer_size=10_000)

    records: list[dict[str, str | float | int]] = []
    for row in dataset.take(args.sample_size):
        toxicity = float(row["toxicity"])
        records.append(
            {
                "text": str(row["text"]),
                "toxicity_score": toxicity,
                "label": int(toxicity >= 0.5),
            }
        )

    frame = pd.DataFrame.from_records(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)

    positive_rate = frame["label"].mean()
    print(f"Saved {len(frame):,} rows to {args.output}")
    print(f"Positive toxicity rate: {positive_rate:.2%}")


if __name__ == "__main__":
    main()

