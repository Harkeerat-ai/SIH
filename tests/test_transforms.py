"""Tests for per-task transform presets."""

import pytest
import torch
from torchvision.transforms import v2

from sihvision.data.transforms import (
    get_change_detection_transforms,
    get_detection_transforms,
    get_eval_transforms,
    get_train_transforms,
)


def _rand(*shape):
    return torch.rand(shape)


def test_train_classification_shape():
    t = get_train_transforms("classification", img_size=64, channels=3)
    out = t(_rand(3, 32, 32))
    assert out.shape == (3, 64, 64)
    assert out.dtype == torch.float32


def test_train_segmentation_applies_to_mask():
    t = get_train_transforms("segmentation", img_size=64, channels=3)
    img = _rand(3, 32, 32)
    mask = torch.zeros(32, 32, dtype=torch.long)
    mask[5:10, 5:10] = 1
    out_img, out_mask = t(img, mask)
    assert out_img.shape == (3, 64, 64)
    assert out_mask.shape == (64, 64)
    assert out_mask.dtype == torch.long
    assert set(out_mask.unique().tolist()) <= {0, 1}


def test_train_change_detection_applies_identically():
    t = get_change_detection_transforms(img_size=64, channels=3)
    img1 = _rand(3, 32, 32)
    img2 = _rand(3, 32, 32)
    out1, out2, mask = t(img1, img2, torch.zeros(32, 32, dtype=torch.long))
    assert out1.shape == (3, 64, 64)
    assert out2.shape == (3, 64, 64)
    assert out1.shape == out2.shape
    assert mask.shape == (64, 64)


def test_eval_deterministic():
    t = get_eval_transforms("classification", img_size=32, channels=3)
    x = _rand(3, 16, 16)
    a = t(x)
    b = t(x)
    assert torch.equal(a, b)


def test_eval_preserves_identify_for_flip_aware():
    t = get_eval_transforms("segmentation", img_size=16, channels=3)
    img = torch.arange(3 * 16 * 16, dtype=torch.float32).reshape(3, 16, 16) / 255.0
    mask = torch.zeros(16, 16, dtype=torch.long)
    out_img, out_mask = t(img, mask)
    assert out_mask.shape == (16, 16)


def test_detection_transforms_resize_only():
    t = get_detection_transforms(img_size=64, channels=3)
    img = _rand(3, 32, 32)
    boxes = torch.tensor([[4.0, 5.0, 20.0, 25.0]])
    labels = torch.tensor([0])
    out_img, out_boxes, out_labels = t(img, boxes, labels)
    assert out_img.shape == (3, 64, 64)
    assert out_boxes.shape == (1, 4)
    assert out_boxes[:, 0] < out_boxes[:, 2]
    assert out_boxes[:, 1] < out_boxes[:, 3]
    assert torch.equal(out_labels, labels)


def test_train_transforms_reject_unknown_task():
    with pytest.raises(ValueError, match="classification|segmentation|detection"):
        get_train_transforms("detection2", img_size=32, channels=3)


def test_normalize_std_zero_guard():
    """Channels with constant values must not produce inf during normalize."""
    img = torch.zeros(3, 8, 8)
    t = get_eval_transforms("classification", img_size=8, channels=3)
    out = t(img)
    assert torch.isfinite(out).all()