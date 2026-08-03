"""Tests for the unified trainer."""

import numpy as np
import pytest
import torch
from PIL import Image

from sihvision.models.registry import build_model


def _cls_data(tmp_path, split="train", n=8, img=32, nc=3):
    for c in range(nc):
        d = tmp_path / split / f"class_{c}"
        d.mkdir(parents=True)
        for i in range(n):
            arr = np.zeros((img, img, 3), dtype=np.uint8)
            arr[..., c] = 200
            Image.fromarray(arr).save(d / f"{i}.png")


def _seg_data(tmp_path, split="train", n=6, img=32):
    d = tmp_path / split / "images"
    m = tmp_path / split / "masks"
    d.mkdir(parents=True)
    for i in range(n):
        arr = np.zeros((img, img, 3), dtype=np.uint8)
        mask = (np.indices((img, img)).sum(0) < img).astype(np.uint8) * 1
        Image.fromarray(arr).save(d / f"{i}.png")
        Image.fromarray(mask * 127).save(m / f"{i}.png")


def test_train_classification_loss_decreases(tmp_path):
    from sihvision.data.build import build_dataset
    from sihvision.train import Trainer

    _cls_data(tmp_path)
    ds = build_dataset(
        "classification", "folder_classification", tmp_path,
        split="train", channels=3,
    )
    cfg = {"task": "classification", "model": {"backbone": "resnet18"}, "data": {}}
    model = build_model(cfg, num_classes=3)
    t = Trainer(cfg, model, device="cpu")
    loss0 = t.run_epoch(ds, "train")
    loss1 = t.run_epoch(ds, "train")
    assert loss1 <= loss0 + 1e-6


def test_train_epoch_returns_scalar_loss(tmp_path):
    from sihvision.data.build import build_dataset
    from sihvision.train import Trainer

    _cls_data(tmp_path)
    ds = build_dataset(
        "classification", "folder_classification", tmp_path,
        split="train", channels=3,
    )
    cfg = {"task": "classification", "model": {"backbone": "resnet18"}, "data": {}}
    model = build_model(cfg, num_classes=3)
    t = Trainer(cfg, model, device="cpu")
    loss = t.run_epoch(ds, "train")
    assert isinstance(loss, float)
    assert loss > 0


def test_train_detection_not_supported():
    from sihvision.models.registry import build_model
    from sihvision.train import train

    cfg = {"task": "detection", "model": {}}
    model = build_model(cfg, num_classes=2)
    with pytest.raises(NotImplementedError, match="YOLO"):
        train(cfg, model, None)


def test_train_segmentation_loss_decreases(tmp_path):
    from sihvision.data.build import build_dataset
    from sihvision.train import train
    from tests.fixtures.generate_synthetic import make_segmentation

    make_segmentation(tmp_path, n_images=6, size=32, n_classes=2)
    ds = build_dataset(
        "segmentation", "mask_segmentation", tmp_path,
        split="train", channels=3,
    )
    cfg = {"task": "segmentation", "model": {"backbone": "resnet18"}, "data": {}, "train": {"epochs": 2, "lr": 1e-3}}
    model = build_model(cfg, num_classes=2)
    history = train(cfg, model, ds)
    assert len(history["train"]) == 2
    assert history["train"][-1] <= history["train"][0] + 1e-6


def test_train_change_detection(tmp_path):
    from sihvision.data.build import build_dataset
    from sihvision.train import train
    from tests.fixtures.generate_synthetic import make_change_detection

    make_change_detection(tmp_path, n_images=6, size=32, n_classes=2)
    ds = build_dataset(
        "change_detection", "change_detection", tmp_path,
        split="train", channels=3,
    )
    cfg = {"task": "change_detection", "model": {"backbone": "resnet18"}, "data": {}, "train": {"epochs": 2, "lr": 1e-3}}
    model = build_model(cfg, num_classes=2)
    history = train(cfg, model, ds)
    assert len(history["train"]) == 2