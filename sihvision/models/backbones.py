"""Backbone builders for sihvision.

Each backbone comes from ``torchvision.models`` and is stripped of its
classification head so a task head can sit on top. Input channels are
adapted (1/3/4) by replacing the first conv layer, supporting
multi-spectral satellite images.
"""

import torch.nn as nn
from torchvision import models

# backbone name -> output feature width
_FEATURES = {
    "resnet18": 512,
    "resnet34": 512,
    "resnet50": 2048,
    "efficientnet_b0": 1280,
    "efficientnet_b1": 1280,
    "mobilenet_v3_small": 576,
    "vgg11": 512,
}


def kind_of(name):
    if name.startswith("resnet"):
        return "resnet"
    if name.startswith("vgg"):
        return "vgg"
    if name.startswith("efficientnet"):
        return "efficientnet"
    if name.startswith("mobilenet"):
        return "mobilenet"
    raise ValueError(f"Unsupported backbone {name!r}")


def backbone_out_features(name):
    if name not in _FEATURES:
        raise ValueError(f"Unsupported backbone {name!r}")
    return _FEATURES[name]


def _replace_first_conv(model, name, in_channels):
    """Swap the first conv layer to accept ``in_channels``."""
    kind = kind_of(name)
    if kind == "resnet":
        conv = model.conv1
        model.conv1 = nn.Conv2d(
            in_channels, conv.out_channels,
            kernel_size=conv.kernel_size, stride=conv.stride, padding=conv.padding,
            bias=False,
        )
    elif kind == "vgg":
        conv = model.features[0]
        model.features[0] = nn.Conv2d(
            in_channels, conv.out_channels,
            kernel_size=conv.kernel_size, stride=conv.stride, padding=conv.padding,
        )
    elif kind == "efficientnet":
        conv = model.features[0][0]
        model.features[0][0] = nn.Conv2d(
            in_channels, conv.out_channels,
            kernel_size=conv.kernel_size, stride=conv.stride, padding=conv.padding,
            bias=False,
        )
    elif kind == "mobilenet":
        conv = model.features[0][0]
        model.features[0][0] = nn.Conv2d(
            in_channels, conv.out_channels,
            kernel_size=conv.kernel_size, stride=conv.stride, padding=conv.padding,
            bias=False,
        )
    return model


def _strip_classifier(model, name):
    """Remove pooling + FC so forward() returns spatial features."""
    kind = kind_of(name)
    if kind == "resnet":
        # children: conv1, bn1, relu, maxpool, layer1..4, avgpool, fc
        layers = list(model.children())[:-2]
        return nn.Sequential(*layers)
    if kind == "vgg":
        return model.features
    if kind in ("efficientnet", "mobilenet"):
        return model.features
    raise ValueError(f"Unsupported backbone {name!r}")


class FeatureBackbone(nn.Module):
    """Backbone producing a [B, C, H', W'] feature tensor."""

    def __init__(self, name, channels=3):
        super().__init__()
        if name not in _FEATURES:
            raise ValueError(f"Unsupported backbone {name!r}")
        if channels not in (1, 3, 4):
            raise ValueError(f"channels must be in (1, 3, 4), got {channels!r}")
        self.name = name
        self.channels = channels
        self.out_features = _FEATURES[name]

        model = getattr(models, name)(weights=None)
        if channels != 3:
            _replace_first_conv(model, name, channels)
        self.features = _strip_classifier(model, name)

    def forward(self, x):
        return self.features(x)


def build_backbone(name, channels=3):
    return FeatureBackbone(name, channels=channels)