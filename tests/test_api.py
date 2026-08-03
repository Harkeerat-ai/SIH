"""Tests for the FastAPI prediction service."""

import io

import numpy as np
import pytest
from PIL import Image


def _png_bytes(size=32, color=128):
    arr = np.full((size, size, 3), color, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def app():
    from sihvision.api.app import create_app

    return create_app()


@pytest.fixture
def test_client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_health(test_client):
    r = test_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_classification(test_client, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "task: classification\n"
        "model:\n  backbone: resnet18\n"
        "data:\n  channels: 3\n"
        "train:\n  device: cpu\n"
    )
    from sihvision.api.app import register_model

    register_model(str(cfg), classes=["a", "b", "c"])
    r = test_client.post(
        "/predict",
        files={"file": ("img.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["task"] == "classification"
    assert isinstance(body["predictions"], list)
    for p in body["predictions"]:
        assert set(p) == {"class", "score"}


def test_predict_with_saliency(test_client, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "task: classification\n"
        "model:\n  backbone: resnet18\n"
        "data:\n  channels: 3\n"
    )
    from sihvision.api.app import register_model

    register_model(str(cfg), classes=["a", "b"])
    r = test_client.post(
        "/predict?explain=true",
        files={"file": ("img.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["saliency"]["method"] in ("gradcam", "vanilla")
    assert body["saliency"]["heatmap_b64"] is not None


def test_predict_missing_file(test_client, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "task: classification\n"
        "model:\n  backbone: resnet18\n"
        "data:\n  channels: 3\n"
    )
    from sihvision.api.app import register_model

    register_model(str(cfg), classes=["a", "b"])
    r = test_client.post("/predict")
    assert r.status_code == 422


def test_iot_endpoint_rejects_non_png(test_client, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "task: classification\n"
        "model:\n  backbone: resnet18\n"
        "data:\n  channels: 3\n"
    )
    from sihvision.api.app import register_model

    register_model(str(cfg), classes=["a", "b"])
    r = test_client.post("/iot/predict", content=b"not an image", headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 400


def test_iot_endpoint_predicts(test_client, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "task: classification\n"
        "model:\n  backbone: resnet18\n"
        "data:\n  channels: 3\n"
    )
    from sihvision.api.app import register_model

    register_model(str(cfg), classes=["a", "b"])
    r = test_client.post(
        "/iot/predict",
        content=_png_bytes(),
        headers={"Content-Type": "image/png"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["task"] == "classification"