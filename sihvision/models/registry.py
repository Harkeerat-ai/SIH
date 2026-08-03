"""Config-driven model builder.

``build_model(cfg, num_classes)`` returns the task model for a config that
has already been validated by ``sihvision.config.validate_config``.
Detection is delegated to an out-of-process YOLO trainer (ultralytics), so
the registry returns a lightweight marker for that task.
"""

from sihvision.models.task_models import (
    build_change_detection_model,
    build_classification_model,
    build_regression_model,
    build_segmentation_model,
)

DEFAULT_BACKBONE = "resnet18"


class _YoloProxy:
    """Placeholder for detection until ultralytics YOLO integration."""

    name = "yolo"


def build_model(cfg, num_classes):
    task = cfg["task"]
    if task == "detection":
        device = cfg.get("train", {}).get("yolo", {})
        return _YoloProxy()

    model_cfg = cfg.get("model", {}) or {}
    backbone = model_cfg.get("backbone", DEFAULT_BACKBONE)
    data_cfg = cfg.get("data", {}) or {}
    channels = data_cfg.get("channels", 3)

    if task == "classification":
        return build_classification_model(backbone, num_classes, channels=channels)
    if task == "regression":
        return build_regression_model(backbone, channels=channels)
    if task == "segmentation":
        return build_segmentation_model(backbone, num_classes, channels=channels)
    if task == "change_detection":
        return build_change_detection_model(backbone, channels=channels)
    raise ValueError(
        f"Unknown task {task!r}. Supported: "
        "classification, detection, segmentation, change_detection, regression"
    )