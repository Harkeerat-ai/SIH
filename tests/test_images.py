"""Tests for image I/O helper."""

import numpy as np
import pytest
import torch
from PIL import Image

from sihvision.data.images import ImageLoadError, load_image


def _save(img_arr, path, mode):
    Image.fromarray(img_arr, mode=mode).save(path)


def test_rgb_loads_float01(tmp_path):
    p = tmp_path / "rgb.png"
    _write_rgb(p, 16)
    t = load_image(p, channels=3)
    assert t.shape == (3, 16, 16)
    assert t.dtype == torch.float32
    assert t.min() >= 0.0 and t.max() <= 1.0


def test_grayscale_duplicated_to_3(tmp_path):
    p = tmp_path / "gray.png"
    arr = np.random.default_rng(1).integers(0, 256, (16, 16), dtype=np.uint8)
    _write(arr, p, "L")
    t = load_image(p, channels=3)
    assert t.shape == (3, 16, 16)
    assert torch.allclose(t[0], t[1])


def test_grayscale_kept_as_1(tmp_path):
    p = tmp_path / "gray.png"
    _write(np.random.default_rng(2).integers(0, 256, (16, 16), dtype=np.uint8), p, "L")
    t = load_image(p, channels=1)
    assert t.shape == (1, 16, 16)


def test_rgba_trimmed_to_3(tmp_path):
    p = tmp_path / "rgba.png"
    _write(np.random.default_rng(3).integers(0, 256, (16, 16, 4), dtype=np.uint8), p, "RGBA")
    t = load_image(p, channels=3)
    assert t.shape == (3, 16, 16)


def test_rgba_kept_as_4(tmp_path):
    p = tmp_path / "rgba.png"
    _write(np.random.default_rng(4).integers(0, 256, (16, 16, 4), dtype=np.uint8), p, "RGBA")
    t = load_image(p, channels=4)
    assert t.shape == (4, 16, 16)


def test_rgb_promoted_to_4(tmp_path):
    p = tmp_path / "rgb.png"
    _write_rgb(p, 16)
    t = load_image(p, channels=4)
    assert t.shape == (4, 16, 16)
    assert torch.allclose(t[3].float(), torch.ones(16, 16))


def test_multiband_tiff(tmp_path, monkeypatch):
    tifffile = pytest.importorskip("tifffile")
    p = tmp_path / "ms.tif"
    arr = np.random.default_rng(5).integers(0, 65535, (8, 16, 16), dtype=np.uint16)
    tifffile.imwrite(p, arr)
    t = load_image(p, channels=8)
    assert t.shape == (8, 16, 16)
    assert t.dtype == torch.float32
    assert t.max() <= 1.0


def test_multiband_tiff_too_few_bands(tmp_path):
    tifffile = pytest.importorskip("tifffile")
    p = tmp_path / "ms.tif"
    tifffile.imwrite(p, np.zeros((4, 16, 16), dtype=np.uint16))
    with pytest.raises(ImageLoadError):
        load_image(p, channels=8)


def _write_rgb(p, size):
    arr = np.random.default_rng(0).integers(0, 256, (size, size, 3), dtype=np.uint8)
    _write(arr, p, "RGB")


def _write(arr, p, mode):
    Image.fromarray(arr, mode=mode).save(p)