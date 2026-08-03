"""Task heads mounted on a shared backbone.

Backbones produce a [B, C, H', W'] spatial feature tensor; heads translate
it into task-specific outputs:

- classification -> [B, C] logits (mean-pool the spatial dims)
- regression    -> [B, 1]
- segmentation  -> [B, num_classes, H, W] (upsampled to ``target_size``)
- change_detection -> [B, 2, H, W] over a t1/t2 feature pair
"""

import torch
import torch.nn as nn


class ClassificationHead(nn.Module):
    def __init__(self, in_features, num_classes):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(in_features, num_classes)

    def forward(self, x):
        x = self.pool(x).flatten(1)
        return self.fc(x)


class RegressionHead(nn.Module):
    def __init__(self, in_features):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(in_features, 1)

    def forward(self, x):
        x = self.pool(x).flatten(1)
        return self.fc(x)


class SegmentationHead(nn.Module):
    def __init__(self, in_features, num_classes):
        super().__init__()
        self.conv = nn.Conv2d(in_features, num_classes, kernel_size=1)

    def forward(self, x, target_size):
        x = self.conv(x)
        if x.shape[-1] != target_size:
            x = nn.functional.interpolate(
                x, size=(target_size, target_size), mode="bilinear", align_corners=False
            )
        return x


class ChangeDetectionHead(nn.Module):
    """Abs-difference operator produces binary change map logits.

    The head is symmetric in t1/t2: swapping inputs flips nothing, the
    abs-difference is order-invariant by design.
    """

    def __init__(self, in_features):
        super().__init__()
        self.conv = nn.Conv2d(in_features, 2, kernel_size=1)

    def forward(self, f1, f2, target_size):
        diff = torch.abs(f1 - f2)
        out = self.conv(diff)
        if out.size(-1) != target_size:
            out = nn.functional.interpolate(
                out, size=(target_size, target_size), mode="bilinear", align_corners=False
            )
        return out