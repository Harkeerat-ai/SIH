"""Task models = backbone + task head, keyed by task."""

import torch.nn as nn

from sihvision.models.backbones import build_backbone
from sihvision.models.heads import (
    ChangeDetectionHead,
    ClassificationHead,
    RegressionHead,
    SegmentationHead,
)


class ClassificationModel(nn.Module):
    def __init__(self, backbone, num_classes, channels=3):
        super().__init__()
        self.backbone = build_backbone(backbone, channels=channels)
        self.head = ClassificationHead(self.backbone.out_features, num_classes)

    def forward(self, x):
        return self.head(self.backbone(x))


class RegressionModel(nn.Module):
    def __init__(self, backbone, channels=3):
        super().__init__()
        self.backbone = build_backbone(backbone, channels=channels)
        self.head = RegressionHead(self.backbone.out_features)

    def forward(self, x):
        return self.head(self.backbone(x))


class SegmentationModel(nn.Module):
    def __init__(self, backbone, n_classes, channels=3):
        super().__init__()
        self.backbone = build_backbone(backbone, channels=channels)
        self.head = SegmentationHead(self.backbone.out_features, n_classes)

    def forward(self, x):
        target_size = x.shape[-1]
        return self.head(self.backbone(x), target_size)


class ChangeDetectionModel(nn.Module):
    def __init__(self, backbone, channels=3):
        super().__init__()
        self.backbone = build_backbone(backbone, channels=channels)
        self.head = ChangeDetectionHead(self.backbone.out_features)

    def forward(self, d):
        f1 = self.backbone(d["t1"])
        f2 = self.backbone(d["t2"])
        return self.head(f1, f2, target_size=d["t1"].shape[-1])


def build_classification_model(backbone, num_classes, channels=3):
    return ClassificationModel(backbone, num_classes, channels=channels)


def build_regression_model(backbone, channels=3):
    return RegressionModel(backbone, channels=channels)


def build_segmentation_model(backbone, n_classes, channels=3):
    return SegmentationModel(backbone, n_classes, channels=channels)


def build_change_detection_model(backbone, channels=3):
    return ChangeDetectionModel(backbone, channels=channels)