"""Tests for the folder classification loader."""

import torch

from sihvision.data.loaders.folder_classification import FolderClassificationDataset
from tests.fixtures.generate_synthetic import make_classification


def test_len_and_classes(tmp_path):
    root = make_classification(tmp_path / "cls", n_classes=3, per_class=4)
    ds = FolderClassificationDataset(root, split="train", channels=3)
    assert len(ds) == 3 * 4
    assert ds.classes == ["class_0", "class_1", "class_2"]
    assert ds.num_classes == 3


def test_getitem_shapes(tmp_path):
    root = make_classification(tmp_path / "cls", n_classes=3, per_class=4, size=32)
    ds = FolderClassificationDataset(root, split="train", channels=3)
    images, target, meta = ds[0]
    assert isinstance(images, torch.Tensor)
    assert images.shape == (3, 32, 32)
    assert images.dtype == torch.float32
    assert images.min() >= 0.0 and images.max() <= 1.0
    assert isinstance(target, torch.Tensor)
    assert target.dtype == torch.long
    assert 0 <= target.item() < 3
    assert meta["image_id"].startswith("img_")
    assert meta["image_path"].endswith(".png")
    assert meta["orig_size"] == (32, 32)
    assert meta["channels"] == 3


def test_class_mapping_by_folder(tmp_path):
    root = make_classification(tmp_path / "cls", n_classes=3, per_class=4)
    ds = FolderClassificationDataset(root, split="train")
    images, target, meta = ds[0]
    assert ds.classes[target.item()] in ("class_0", "class_1", "class_2")


def test_grayscale_image_duplicated_to_3_channels(tmp_path):
    import numpy as np
    from PIL import Image

    root = tmp_path / "gs"
    d = root / "train" / "gray"
    d.mkdir(parents=True)
    arr = np.random.default_rng(7).integers(0, 256, (16, 16), dtype=np.uint8)
    Image.fromarray(arr).save(d / "g.png")
    ds = FolderClassificationDataset(root, split="train", channels=3)
    images, _, _ = ds[0]
    assert images.shape == (3, 16, 16)
    assert torch.allclose(images[0], images[1])


def test_missing_split_dir_raises(tmp_path):
    import pytest

    root = make_classification(tmp_path / "cls")
    with pytest.raises(ValueError, match="nonexistent"):
        FolderClassificationDataset(root, split="nonexistent")


def test_empty_class_dir_raises(tmp_path):
    import pytest

    root = tmp_path / "empty"
    (root / "train" / "class_a").mkdir(parents=True)
    with pytest.raises(ValueError, match="class_a"):
        FolderClassificationDataset(root, split="train")