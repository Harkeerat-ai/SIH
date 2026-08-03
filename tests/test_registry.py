"""Tests for the build_model registry."""

import pytest
import torch


def test_registry_classification():
    from sihvision.models.registry import build_model

    cfg = {"task": "classification", "model": {"backbone": "resnet18"}, "data": {"channels": 3}}
    model = build_model(cfg, num_classes=3)
    out = model(torch.zeros(2, 3, 64, 64))
    assert tuple(out.shape) == (2, 3)


def test_registry_regression():
    from sihvision.models.registry import build_model

    cfg = {"task": "regression", "model": {"backbone": "resnet18"}, "data": {"channels": 3}}
    model = build_model(cfg, num_classes=1)
    out = model(torch.zeros(2, 3, 64, 64))
    assert tuple(out.shape) == (2, 1)


def test_registry_segmentation():
    from sihvision.models.registry import build_model

    cfg = {"task": "segmentation", "model": {"backbone": "resnet18"}, "data": {"channels": 3}}
    model = build_model(cfg, num_classes=2)
    out = model(torch.zeros(2, 3, 64, 64))
    assert tuple(out.shape) == (2, 2, 64, 64)


def test_registry_change_detection():
    from sihvision.models.registry import build_model

    cfg = {"task": "change_detection", "model": {"backbone": "resnet18"}, "data": {"channels": 3}}
    model = build_model(cfg, num_classes=2)
    d = {"t1": torch.zeros(2, 3, 64, 64), "t2": torch.rand(2, 3, 64, 64)}
    out = model(d)
    assert tuple(out.shape) == (2, 2, 64, 64)


def test_registry_detection_yolo():
    from sihvision.models.registry import build_model

    cfg = {
        "task": "detection",
        "model": {"backbone": "resnet18"},
        "data": {"channels": 3},
        "train": {"yolo": {"model_size": "n"}},
    }
    model = build_model(cfg, num_classes=2)
    assert model is not None


def test_registry_rejects_unknown_task():
    from sihvision.models.registry import build_model

    cfg = {"task": "nonsense", "model": {}, "data": {}}
    with pytest.raises(ValueError, match="task"):
        build_model(cfg, num_classes=2)


def test_registry_uses_channels():
    from sihvision.models.registry import build_model

    cfg = {"task": "classification", "model": {"backbone": "resnet18"}, "data": {"channels": 4}}
    model = build_model(cfg, num_classes=3)
    out = model(torch.zeros(2, 4, 64, 64))
    assert tuple(out.shape) == (2, 3)


def test_registry_default_backbone():
    from sihvision.models.registry import build_model

    cfg = {"task": "classification", "model": {}, "data": {}}
    model = build_model(cfg, num_classes=3)
    assert model is not None