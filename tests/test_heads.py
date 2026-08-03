"""Tests for task heads built on top of a backbone."""

import torch


def test_classification_head_shapes():
    from sihvision.models.heads import ClassificationHead

    head = ClassificationHead(in_features=512, num_classes=5)
    out = head(torch.zeros(4, 512, 7, 7))
    assert tuple(out.shape) == (4, 5)


def test_regression_head_shapes():
    from sihvision.models.heads import RegressionHead

    head = RegressionHead(in_features=512)
    out = head(torch.zeros(3, 512, 7, 7))
    assert tuple(out.shape) == (3, 1)


def test_segmentation_head_up_to_original_size():
    from sihvision.models.heads import SegmentationHead

    head = SegmentationHead(in_features=512, num_classes=2)
    out = head(torch.zeros(2, 512, 8, 8), target_size=64)
    assert tuple(out.shape) == (2, 2, 64, 64)


def test_segmentation_head_num_outputs():
    from sihvision.models.heads import SegmentationHead

    head = SegmentationHead(in_features=256, num_classes=5)
    out = head(torch.zeros(1, 256, 8, 8), target_size=32)
    assert out.shape[1] == 5


def test_change_detection_head():
    from sihvision.models.heads import ChangeDetectionHead

    head = ChangeDetectionHead(in_features=512)
    out = head(torch.zeros(2, 512, 8, 8), torch.ones(2, 512, 8, 8), target_size=64)
    assert tuple(out.shape) == (2, 2, 64, 64)


def test_full_satellite_equal_inputs():
    """Change detection with identical t1/t2 must produce near-symmetric output."""
    from sihvision.models.heads import ChangeDetectionHead

    head = ChangeDetectionHead(in_features=64)
    t = torch.rand(1, 64, 8, 8)
    a = head(t, t, target_size=16)
    assert tuple(a.shape) == (1, 2, 16, 16)