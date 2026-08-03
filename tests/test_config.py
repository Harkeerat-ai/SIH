"""Tests for config loading and validation."""

import pytest

from sihvision.config import ConfigError, load_config, validate_config


def test_minimal_valid_classification_config():
    cfg = {
        "task": "classification",
        "data": {
            "root": "data/psx",
            "format": "folder_classification",
            "channels": 3,
            "img_size": 256,
            "split_ratio": [0.7, 0.15, 0.15],
        },
        "model": {"backbone": "resnet50", "pretrained": True},
        "train": {"epochs": 5, "lr": 1e-3, "device": "cpu"},
    }
    validate_config(cfg)


def test_config_applies_defaults():
    cfg = {
        "task": "classification",
        "data": {"root": "data/psx"},
    }
    validate_config(cfg)


def test_config_missing_task():
    with pytest.raises(ConfigError, match="task"):
        validate_config({"data": {"root": "x"}})


def test_config_unknown_task():
    with pytest.raises(ConfigError, match="Unknown task"):
        validate_config({"task": "magic", "data": {"root": "x"}})


def test_config_missing_root():
    with pytest.raises(ConfigError, match="data.root"):
        validate_config({"task": "classification", "data": {}})


def test_config_format_task_mismatch():
    with pytest.raises(ConfigError, match="not valid for task"):
        validate_config(
            {
                "task": "classification",
                "data": {"root": "x", "format": "yolo"},
            }
        )


def test_config_unknown_format():
    with pytest.raises(ConfigError, match="Unknown data format"):
        validate_config(
            {
                "task": "classification",
                "data": {"root": "x", "format": "things"},
            }
        )


def test_config_bad_channels():
    with pytest.raises(ConfigError, match="channel"):
        validate_config(
            {
                "task": "classification",
                "data": {"root": "x", "channels": 7},
            }
        )


def test_config_unknown_backbone():
    with pytest.raises(ConfigError, match="backbone"):
        validate_config(
            {
                "task": "classification",
                "data": {"root": "x"},
                "model": {"backbone": "supershark"},
            }
        )


def test_config_bad_split_ratio():
    with pytest.raises(ConfigError, match="split_ratio"):
        validate_config(
            {
                "task": "classification",
                "data": {"root": "x", "split_ratio": [0.7, 0.3]},
            }
        )


def test_config_bad_device():
    with pytest.raises(ConfigError, match="train.device"):
        validate_config(
            {
                "task": "classification",
                "data": {"root": "x"},
                "train": {"device": "groq"},
            }
        )


def test_load_config_from_yaml(tmp_path):
    import yaml

    p = tmp_path / "exp.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "task": "segmentation",
                "data": {"root": "data/masks", "format": "mask_segmentation"},
                "model": {"backbone": "resnet18"},
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg["task"] == "segmentation"