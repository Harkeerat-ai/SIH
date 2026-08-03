"""Tests for task models = backbone + task head."""

import pytest
import torch


def test_classification_model():
    from sihvision.models.task_models import build_classification_model

    model = build_classification_model("resnet18", num_classes=3, channels=3)
    out = model(torch.zeros(2, 3, 64, 64))
    assert tuple(out.shape) == (2, 3)


def test_classification_multichannel():
    from sihvision.models.task_models import build_classification_model

    model = build_classification_model("resnet18", num_classes=4, channels=4)
    out = model(torch.zeros(1, 4, 64, 64))
    assert tuple(out.shape) == (1, 4)


def test_regression_model():
    from sihvision.models.task_models import build_regression_model

    model = build_regression_model("resnet18", channels=3)
    out = model(torch.zeros(2, 3, 64, 64))
    assert tuple(out.shape) == (2, 1)


def test_segmentation_model():
    from sihvision.models.task_models import build_segmentation_model

    model = build_segmentation_model("resnet18", n_classes=2, channels=3)
    out = model(torch.zeros(2, 3, 64, 64))
    assert tuple(out.shape) == (2, 2, 64, 64)


def test_change_detection_model():
    from sihvision.models.task_models import build_change_detection_model

    model = build_change_detection_model("resnet18", channels=3)
    d = {"t1": torch.zeros(2, 3, 64, 64), "t2": torch.rand(2, 3, 64, 64)}
    out = model(d)
    assert tuple(out.shape) == (2, 2, 64, 64)


def test_regression_model_out_of_range():
    from sihvision.models.task_models import build_regression_model

    model = build_regression_model("resnet18", channels=3)
    out = model(torch.rand(2, 3, 64, 64))
    assert torch.isfinite(out).all()