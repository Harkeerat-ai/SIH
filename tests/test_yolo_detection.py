"""Tests for the YOLO-format detection loader."""

import pytest
import torch

from sihvision.data.errors import MissingLabelError
from sihvision.data.loaders.yolo_detection import YoloDetectionDataset
from tests.fixtures.generate_synthetic import make_detection


def test_len(tmp_path):
    root = make_detection(tmp_path / "det", n_images=5)
    ds = YoloDetectionDataset(root, split="train", channels=3, n_classes=3)
    assert len(ds) == 5


def test_getitem_targets(tmp_path):
    root = make_detection(tmp_path / "det", n_images=5, size=32)
    ds = YoloDetectionDataset(root, split="train", channels=3, n_classes=3)
    images, target, meta = ds[0]
    assert isinstance(images, torch.Tensor)
    assert images.shape == (3, 32, 32)
    assert target["boxes"].shape[1] == 4
    assert target["boxes"].dtype == torch.float32
    assert target["labels"].shape[0] == target["boxes"].shape[0]
    assert target["labels"].dtype == torch.long
    assert (target["labels"] >= 0).all() and (target["labels"] < 3).all()


def test_boxes_xyxy_pixel_coords_and_in_bounds(tmp_path):
    root = make_detection(tmp_path / "det", n_images=10, size=64)
    ds = YoloDetectionDataset(root, split="train", channels=3, n_classes=3)
    for i in range(len(ds)):
        _, target, _ = ds[i]
        boxes = target["boxes"]
        assert (boxes[:, 0] < boxes[:, 2]).all()
        assert (boxes[:, 1] < boxes[:, 3]).all()
        assert (boxes[:, 0] >= 0).all() and (boxes[:, 2] <= 64).all()
        assert (boxes[:, 1] >= 0).all() and (boxes[:, 3] <= 64).all()


def test_empty_label_file_gives_empty_targets(tmp_path):
    root = make_detection(tmp_path / "det", n_images=1, max_boxes=0)
    ds = YoloDetectionDataset(root, split="train", channels=3, n_classes=3)
    images, target, meta = ds[0]
    assert target["boxes"].shape == (0, 4)
    assert target["labels"].shape == (0,)


def test_missing_label_raises(tmp_path):
    root = make_detection(tmp_path / "det", n_images=2)
    (root / "train" / "labels" / "img_1.txt").unlink()
    ds = YoloDetectionDataset(root, split="train", channels=3, n_classes=3)
    with pytest.raises(MissingLabelError):
        ds.verify_integrity()


def test_meta(tmp_path):
    root = make_detection(tmp_path / "det", n_images=1, size=32)
    ds = YoloDetectionDataset(root, split="train", channels=3, n_classes=3)
    _, _, meta = ds[0]
    assert meta["image_id"] == "img_0"
    assert meta["image_path"].endswith(".png")
    assert meta["orig_size"] == (32, 32)
    assert meta["channels"] == 3


def test_coco_format_unsupported(tmp_path):
    from sihvision.data.errors import UnsupportedFormatError

    root = make_detection(tmp_path / "det", n_images=1)
    with pytest.raises(UnsupportedFormatError):
        YoloDetectionDataset(root, split="train", channels=3, n_classes=3, label_format="coco")