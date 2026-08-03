"""Tests for the mask-PNG segmentation loader."""

import numpy as np
import pytest
import torch
from PIL import Image

from sihvision.data.errors import MissingLabelError
from sihvision.data.loaders.mask_segmentation import MaskSegmentationDataset
from tests.fixtures.generate_synthetic import make_segmentation


def test_len_and_classes(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=5, n_classes=4)
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    assert len(ds) == 5
    assert ds.num_classes == 4
    assert ds.classes == ["0", "1", "2", "3"]


def test_getitem_shapes(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=5, size=32, n_classes=4)
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    images, mask, meta = ds[0]
    assert images.shape == (3, 32, 32)
    assert mask.shape == (32, 32)
    assert mask.dtype == torch.long
    assert mask.min() >= 0 and mask.max() < 4


def test_mask_values_match_seeded_image(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=5, size=32, n_classes=4)
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    _, mask, _ = ds[0]
    assert (mask.numpy() == 0).any()
    assert (mask.numpy() != 0).any()


def test_meta(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=1, size=32, n_classes=4)
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    _, _, meta = ds[0]
    assert meta["image_id"] == "img_0"
    assert meta["image_path"].endswith(".png")
    assert meta["orig_size"] == (32, 32)


def test_missing_mask_raises(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=2)
    (root / "train" / "masks" / "img_1.png").unlink()
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    with pytest.raises(MissingLabelError):
        ds.verify_integrity()


def test_mask_basename_mismatch_raises(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=2)
    (root / "train" / "masks" / "img_1.png").rename(root / "train" / "masks" / "other.png")
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    with pytest.raises(MissingLabelError):
        ds.verify_integrity()


def test_extra_images_without_mask_not_included(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=2)
    img_dir = root / "train" / "images"
    (img_dir / "stray.png").write_bytes(b"")
    ds = MaskSegmentationDataset(root, split="train", channels=3, n_classes=4)
    assert len(ds) == 2