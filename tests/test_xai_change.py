"""Tests for change-detection and segmentation saliency."""

import torch


def _seg_model():
    from sihvision.models.registry import build_model

    cfg = {"task": "segmentation", "model": {"backbone": "resnet18"}, "data": {}}
    return build_model(cfg, num_classes=2)


def test_saliency_segmentation_model():
    from sihvision.xai import saliency_map

    model = _seg_model()
    img = torch.rand(1, 3, 64, 64)
    for method in ("gradcam", "vanilla"):
        hm = saliency_map(model, img, method=method)
        assert tuple(hm.shape) == (64, 64)
        assert hm.min() >= 0 and hm.max() <= 1.0 + 1e-6


def test_saliency_change_detection_diff():
    """For change detection the salient region should favor the changed area."""
    from sihvision.models.registry import build_model
    from sihvision.xai import saliency_map

    cfg = {"task": "change_detection", "model": {"backbone": "resnet18"}, "data": {}}
    model = build_model(cfg, num_classes=2)

    t1 = torch.zeros(1, 3, 64, 64)
    t2 = torch.zeros_like(t1)
    t2[:, 2, 16:48, 16:48] = 1.0  # changed square
    hm = saliency_map(model, {"t1": t1, "t2": t2}, method="gradcam")
    assert tuple(hm.shape) == (64, 64)

    changed_region = hm[16:48, 16:48].mean()
    outside_region = torch.cat([hm[:16].flatten(), hm[48:].flatten()]).mean()
    assert changed_region > outside_region - 1e-3