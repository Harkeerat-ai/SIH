"""Tests for the regression dataset (images -> scalar target)."""

import numpy as np
import pytest
import torch
from PIL import Image


def _make_regression(root, n=6, size=16):
    img_dir = root / "train" / "images"
    img_dir.mkdir(parents=True)
    rng = np.random.default_rng(1)
    lines = []
    for i in range(n):
        arr = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
        Image.fromarray(arr).save(img_dir / f"img_{i}.png")
        lines.append(f"img_{i},{i / 10.0:.3f}")
    (root / "train" / "labels.csv").write_text(
        "image_id,value\n" + "\n".join(lines), encoding="utf-8"
    )
    return root


def test_regression_dataset_shape(tmp_path):
    from sihvision.data.loaders.regression import RegressionDataset

    root = _make_regression(tmp_path)
    ds = RegressionDataset(root, split="train", channels=3)
    assert len(ds) == 6
    img, target, meta = ds[0]
    assert tuple(img.shape) == (3, 16, 16)
    assert target.dtype == torch.float32
    assert target.ndim == 0


def test_regression_dataset_matches_csv(tmp_path):
    from sihvision.data.loaders.regression import RegressionDataset

    root = _make_regression(tmp_path)
    ds = RegressionDataset(root, split="train", channels=3)
    _, t1, _ = ds[1]
    assert t1.item() == pytest.approx(0.1, abs=1e-5)


def test_regression_missing_labels_raises(tmp_path):
    from sihvision.data.loaders.regression import RegressionDataset

    (tmp_path / "train" / "images").mkdir(parents=True)
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(
        tmp_path / "train" / "images" / "a.png"
    )
    with pytest.raises(ValueError, match="labels"):
        RegressionDataset(tmp_path, split="train")


def test_regression_missing_split_raises(tmp_path):
    from sihvision.data.loaders.regression import RegressionDataset

    with pytest.raises(ValueError, match="directory"):
        RegressionDataset(tmp_path, split="train")


def test_regression_meta(tmp_path):
    from sihvision.data.loaders.regression import RegressionDataset

    root = _make_regression(tmp_path)
    ds = RegressionDataset(root, split="train", channels=3)
    img, target, meta = ds[2]
    assert meta["image_id"] == "img_2"
    assert meta["channels"] == 3