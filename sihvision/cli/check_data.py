"""check-data CLI: build a dataset from a config and report summary.

Usage::

    check-data path/to/config.yaml
"""

import argparse
import sys

import yaml

from sihvision.data.build import build_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect a sihvision dataset from config.")
    parser.add_argument("config", help="Path to experiment YAML config")
    parser.add_argument("--split", choices=["train", "val", "test", "all"], default="train")
    args = parser.parse_args(argv)

    try:
        with open(args.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        print(f"ERROR loading config: {exc}", file=sys.stderr)
        return 1
    task = cfg["task"]
    data = cfg["data"]
    fmt = data["format"]
    root = data["root"]

    try:
        ds = build_dataset(task, fmt, root, split=args.split, **load_kwargs(data))
    except Exception as exc:  # pragma: no cover
        print(f"ERROR building dataset: {exc}", file=sys.stderr)
        return 1

    print(f"task: {ds.task}")
    print(f"classes: {ds.classes}")
    print(f"num_classes: {ds.num_classes}")
    print(f"channels: {ds.channels}")
    print(f"len({args.split}): {len(ds)}")
    sample = ds[0]
    print("sample[0].images=", sample[0].shape if hasattr(sample[0], "shape") else type(sample[0]))
    print("sample[0].targets=", sample[1])
    return 0


def load_kwargs(data):
    keep = {"channels", "n_classes", "classes", "label_format"}
    return {k: v for k, v in data.items() if k in keep and v is not None}


if __name__ == "__main__":
    raise SystemExit(main())