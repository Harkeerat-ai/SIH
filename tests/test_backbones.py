"""Tests for the backbone builder."""

import pytest
import torch


def test_build_backbone_resnet18():
    from sihvision.models.backbones import build_backbone

    model = build_backbone("resnet18", channels=3)
    assert model is not None
    out = model(torch.zeros(2, 3, 224, 224))
    assert tuple(out.shape) == (2, 512, 7, 7)


def test_build_backbone_resnet50():
    from sihvision.models.backbones import build_backbone

    out = build_backbone("resnet50", channels=3)(torch.zeros(1, 3, 224, 224))
    assert tuple(out.shape) == (1, 2048, 7, 7)


def test_build_backbone_vgg11():
    from sihvision.models.backbones import build_backbone

    out = build_backbone("vgg11", channels=3)(torch.zeros(1, 3, 224, 224))
    assert out.dim() == 4
    assert out.shape[1] == 512


def test_build_backbone_efficientnet_b0():
    from sihvision.models.backbones import build_backbone

    out = build_backbone("efficientnet_b0", channels=3)(torch.zeros(1, 3, 224, 224))
    assert out.dim() == 4
    assert out.shape[1] == 1280


def test_build_backbone_mobilenet_v3_small():
    from sihvision.models.backbones import build_backbone

    out = build_backbone("mobilenet_v3_small", channels=3)(torch.zeros(1, 3, 224, 224))
    assert out.dim() == 4
    assert out.shape[1] == 576


def test_build_backbone_single_channel():
    from sihvision.models.backbones import build_backbone

    out = build_backbone("resnet18", channels=1)(torch.zeros(1, 1, 224, 224))
    assert tuple(out.shape) == (1, 512, 7, 7)


def test_build_backbone_four_channels():
    from sihvision.models.backbones import build_backbone

    out = build_backbone("resnet18", channels=4)(torch.zeros(1, 4, 224, 224))
    assert tuple(out.shape) == (1, 512, 7, 7)


def test_reject_unknown_backbone():
    from sihvision.data.errors import DatasetError
    from sihvision.models.backbones import build_backbone

    with pytest.raises(ValueError, match="backbone"):
        build_backbone("nonsense", channels=3)


def test_reject_invalid_channels():
    from sihvision.models.backbones import build_backbone

    with pytest.raises(ValueError, match="channels"):
        build_backbone("resnet18", channels=8)