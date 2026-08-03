"""Tests for the saliency / XAI module."""

import numpy as np
import pytest
import torch


def _cls_model():
    from sihvision.models.registry import build_model

    cfg = {"task": "classification", "model": {"backbone": "resnet18"}, "data": {}}
    return build_model(cfg, num_classes=3)


def test_gradcam_output_shape():
    from sihvision.xai import saliency_map

    model = _cls_model()
    img = torch.rand(1, 3, 64, 64)
    heatmap = saliency_map(model, img, method="gradcam")
    assert tuple(heatmap.shape) == (64, 64)
    assert heatmap.dtype == torch.float32


def test_gradcam_values_in_range():
    from sihvision.xai import saliency_map

    model = _cls_model()
    img = torch.rand(1, 3, 64, 64)
    heatmap = saliency_map(model, img, method="gradcam")
    assert heatmap.min() >= 0.0
    assert heatmap.max() <= 1.0 + 1e-6


def test_vanilla_gradients_shape():
    from sihvision.xai import saliency_map

    model = _cls_model()
    img = torch.rand(1, 3, 64, 64)
    heatmap = saliency_map(model, img, method="vanilla")
    assert tuple(heatmap.shape) == (64, 64)


def test_saliency_deterministic():
    from sihvision.xai import saliency_map

    model = _cls_model()
    model.eval()
    img = torch.rand(1, 3, 64, 64)
    a = saliency_map(model, img, method="gradcam")
    b = saliency_map(model, img, method="gradcam")
    assert torch.allclose(a, b)


def test_saliency_rejects_unknown_method():
    from sihvision.xai import saliency_map

    model = _cls_model()
    img = torch.rand(1, 3, 64, 64)
    with pytest.raises(ValueError, match="method"):
        saliency_map(model, img, method="nonsense")


def test_saliency_requires_requires_grad_input():
    from sihvision.xai import saliency_map

    model = _cls_model()
    img = torch.rand(1, 3, 64, 64)
    heatmap = saliency_map(model, img, method="vanilla")
    assert heatmap.isfinite().all()


def test_gradcam_target_class():
    from sihvision.xai import saliency_map

    model = _cls_model()
    img = torch.rand(1, 3, 64, 64)
    heatmap = saliency_map(model, img, method="gradcam", class_idx=2)
    assert tuple(heatmap.shape) == (64, 64)