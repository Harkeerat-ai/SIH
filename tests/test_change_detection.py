"""Tests for the change-detection (bi-temporal) loader."""

import pytest
import torch

from sihvision.data.errors import MissingLabelError
from sihvision.data.loaders.change_detection import ChangeDetectionDataset
from tests.fixtures.generate_synthetic import make_change_detection


def test_len(tmp_path):
    root = make_change_detection(tmp_path / "cd", n_images=5)
    ds = ChangeDetectionDataset(root, split="train", channels=3, n_classes=2)
    assert len(ds) == 5


def test_getitem_pair_and_mask(tmp_path):
    root = make_change_detection(tmp_path / "cd", n_images=5, size=32)
    ds = ChangeDetectionDataset(root, split="train", channels=3, n_classes=2)
    images, mask, meta = ds[0]
    assert set(images.keys()) == {"t1", "t2"}
    assert images["t1"].shape == (3, 32, 32)
    assert images["t2"].shape == (3, 32, 32)
    assert mask.shape == (32, 32)
    assert mask.dtype == torch.long
    assert set(mask.unique().tolist()) <= {0, 1}
    assert meta["image_id"] == "img_0"


def test_masks_have_change_regions(tmp_path):
    root = make_change_detection(tmp_path / "cd", n_images=5, size=32)
    ds = ChangeDetectionDataset(root, split="train", channels=3, n_classes=2)
    changed = False
    for i in range(len(ds)):
        _, mask, _ = ds[i]
        if 1 in mask.unique().tolist():
            changed = True
            break
    assert changed


def test_missing_mask_raises(tmp_path):
    root = make_change_detection(tmp_path / "cd", n_images=2)
    (root / "train" / "masks" / "img_1.png").unlink()
    ds = ChangeDetectionDataset(root, split="train", channels=3, n_classes=2)
    with pytest.raises(MissingLabelError):
        ds.verify_integrity()


def test_meta(tmp_path):
    root = make_change_detection(tmp_path / "cd", n_images=1, size=32)
    ds = ChangeDetectionDataset(root, split="train", channels=3, n_classes=2)
    _, _, meta = ds[0]
    assert meta["image_id"] == "img_0"
    assert meta["orig_size"] == (32, 32)