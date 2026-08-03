"""Config loading and validation for sihvision experiments."""

import yaml

VALID_TASKS = {"classification", "detection", "segmentation", "change_detection", "regression"}
VALID_FORMATS = {
    "folder_classification",
    "yolo",
    "mask_segmentation",
    "change_detection",
    "regression",
}
VALID_BACKBONES = {
    "resnet18",
    "resnet34",
    "resnet50",
    "efficientnet_b0",
    "efficientnet_b1",
    "mobilenet_v3_small",
    "vgg11",
}
VALID_CHANNELS = {1, 3, 4}
VALID_YOLO_MODELS = {"n", "s", "m"}
VALID_DEVICES = {"auto", "cpu", "cuda", "mps"}

TASK_FORMATS = {
    "classification": {"folder_classification"},
    "detection": {"yolo"},
    "segmentation": {"mask_segmentation"},
    "change_detection": {"change_detection"},
    "regression": {"regression"},
}


class ConfigError(ValueError):
    """Raised when an experiment config is invalid."""


def _require_mapping(cfg, path):
    if not isinstance(cfg, dict):
        raise ConfigError(f"{path} must be a mapping, got {type(cfg).__name__}")
    return cfg


def validate_task(task):
    if task not in VALID_TASKS:
        raise ConfigError(
            f"Unknown task {task!r}. Valid tasks: {sorted(VALID_TASKS)}"
        )


def validate_format(task, fmt):
    if fmt not in VALID_FORMATS:
        raise ConfigError(
            f"Unknown data format {fmt!r}. Valid formats: {sorted(VALID_FORMATS)}"
        )
    allowed = TASK_FORMATS[task]
    if fmt not in allowed:
        raise ConfigError(
            f"Data format {fmt!r} is not valid for task {task!r}. "
            f"Expected one of: {sorted(allowed)}"
        )


def validate_backbone(backbone):
    if backbone is not None and backbone not in VALID_BACKBONES:
        raise ConfigError(
            f"Unknown backbone {backbone!r}. Valid backbones: {sorted(VALID_BACKBONES)}"
        )


def validate_channels(channels):
    if channels not in VALID_CHANNELS:
        raise ConfigError(
            f"Unknown channel count {channels!r}. Valid channels: {sorted(VALID_CHANNELS)}"
        )


def validate_img_size(img_size):
    if not isinstance(img_size, int) or img_size <= 0:
        raise ConfigError(f"img_size must be a positive int, got {img_size!r}")


def validate_split_ratio(split_ratio):
    if not (
        isinstance(split_ratio, (list, tuple))
        and len(split_ratio) == 3
        and all(isinstance(x, (int, float)) and x >= 0 for x in split_ratio)
    ):
        raise ConfigError(
            f"split_ratio must be a list of 3 non-negative numbers, got {split_ratio!r}"
        )


def validate_train(train):
    train = _require_mapping(train, "train")
    lr = train.get("lr", 1e-3)
    if not (isinstance(lr, (int, float)) and lr > 0):
        raise ConfigError(f"train.lr must be a positive float, got {lr!r}")
    epochs = train.get("epochs", 30)
    if not (isinstance(epochs, int) and epochs > 0):
        raise ConfigError(f"train.epochs must be a positive int, got {epochs!r}")
    device = train.get("device", "auto")
    if device not in VALID_DEVICES:
        raise ConfigError(
            f"train.device must be one of auto/cpu/cuda/mps, got {device!r}"
        )
    yolo = train.get("yolo", {})
    if yolo:
        yolo = _require_mapping(yolo, "train.yolo")
        size = yolo.get("model_size", "n")
        if size not in VALID_YOLO_MODELS:
            raise ConfigError(
                f"train.yolo.model_size must be one of {sorted(VALID_YOLO_MODELS)}, got {size!r}"
            )


def validate_config(cfg):
    """Validate a full experiment config, returning normalized values."""
    _require_mapping(cfg, "config")
    if "task" not in cfg:
        raise ConfigError("Missing required key: task")
    task = cfg["task"]
    validate_task(task)

    if "data" not in cfg:
        raise ConfigError("Missing required key: data")
    data = _require_mapping(cfg["data"], "data")
    if "root" not in data:
        raise ConfigError("Missing required key: data.root")
    if not isinstance(data["root"], str) or not data["root"].strip():
        raise ConfigError("data.root must be a non-empty string")

    fmt = data.get("format")
    if fmt is not None:
        validate_format(task, fmt)

    channels = data.get("channels", 3)
    validate_channels(channels)

    img_size = data.get("img_size", 256)
    validate_img_size(img_size)

    split_ratio = data.get("split_ratio", [0.7, 0.15, 0.15])
    validate_split_ratio(split_ratio)

    model = cfg.get("model", {})
    model = _require_mapping(model, "model")
    backbone = model.get("backbone")
    validate_backbone(backbone)

    if "train" in cfg:
        validate_train(cfg["train"])

    return cfg


def load_config(path):
    """Load a YAML config file and validate it."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    validate_config(cfg)
    return cfg
