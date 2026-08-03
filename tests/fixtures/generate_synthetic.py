"""Deterministic synthetic dataset generators for tests.

All generators write tiny datasets (32x32, few samples) into a root directory
and are deterministic via a fixed seed. Used by loader tests via tmp_path.
"""

from pathlib import Path

import numpy as np
from PIL import Image


def _rng():
    return np.random.default_rng(42)


def make_classification(root, n_classes=3, per_class=4, size=32):
    """root/{split}/{class}/img_{i}.png"""
    root = Path(root)
    for split in ("train", "val", "test"):
        for c in range(n_classes):
            cls_dir = root / split / f"class_{c}"
            cls_dir.mkdir(parents=True, exist_ok=True)
            for i in range(per_class):
                img = _rng().integers(0, 256, (size, size, 3), dtype=np.uint8)
                Image.fromarray(img).save(cls_dir / f"img_{i}.png")
    return root


def make_detection(root, n_images=5, size=32, min_boxes=1, max_boxes=4, n_classes=3):
    """root/{split}/images/img_{i}.png + root/{split}/labels/img_{i}.txt (YOLO)"""
    if max_boxes == 0:
        min_boxes = 0
    elif min_boxes > max_boxes:
        raise ValueError("min_boxes must be <= max_boxes")
    root = Path(root)
    for split in ("train", "val"):
        img_dir = root / split / "images"
        lbl_dir = root / split / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)
        rng = _rng()
        for i in range(n_images):
            img = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
            Image.fromarray(img).save(img_dir / f"img_{i}.png")
            lines = []
            n_boxes = rng.integers(min_boxes, max_boxes + 1) if max_boxes else 0
            for _ in range(n_boxes):
                cls = int(rng.integers(0, n_classes))
                w = float(rng.uniform(0.1, 0.4))
                h = float(rng.uniform(0.1, 0.4))
                cx = float(rng.uniform(w / 2, 1 - w / 2))
                cy = float(rng.uniform(h / 2, 1 - h / 2))
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            (lbl_dir / f"img_{i}.txt").write_text("\n".join(lines), encoding="utf-8")
    return root


def make_segmentation(root, n_images=5, size=32, n_classes=4):
    """root/{split}/images/img_{i}.png + root/{split}/masks/img_{i}.png"""
    root = Path(root)
    for split in ("train", "val"):
        img_dir = root / split / "images"
        msk_dir = root / split / "masks"
        img_dir.mkdir(parents=True, exist_ok=True)
        msk_dir.mkdir(parents=True, exist_ok=True)
        rng = _rng()
        for i in range(n_images):
            img = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
            Image.fromarray(img).save(img_dir / f"img_{i}.png")
            mask = np.zeros((size, size), dtype=np.uint8)
            for cls in range(1, n_classes):
                cy = int(rng.integers(4, size - 4))
                cx = int(rng.integers(4, size - 4))
                r = int(rng.integers(2, 6))
                yy, xx = np.ogrid[:size, :size]
                mask[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = cls
            Image.fromarray(mask).save(msk_dir / f"img_{i}.png")
    return root


def make_change_detection(root, n_images=5, size=32, n_classes=2):
    """root/{split}/t1/img_{i}.png + t2/img_{i}.png + masks/img_{i}.png"""
    root = Path(root)
    for split in ("train", "val"):
        t1_dir = root / split / "t1"
        t2_dir = root / split / "t2"
        msk_dir = root / split / "masks"
        t1_dir.mkdir(parents=True, exist_ok=True)
        t2_dir.mkdir(parents=True, exist_ok=True)
        msk_dir.mkdir(parents=True, exist_ok=True)
        rng = _rng()
        for i in range(n_images):
            base = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
            Image.fromarray(base).save(t1_dir / f"img_{i}.png")
            t2 = base.copy()
            mask = np.zeros((size, size), dtype=np.uint8)
            n_changes = int(rng.integers(1, 4))
            for _ in range(n_changes):
                cy = int(rng.integers(2, size - 2))
                cx = int(rng.integers(2, size - 2))
                r = int(rng.integers(1, 4))
                yy, xx = np.ogrid[:size, :size]
                zone = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
                t2[zone] = rng.integers(0, 256, (3,), dtype=np.uint8)
                mask[zone] = 1
            Image.fromarray(t2).save(t2_dir / f"img_{i}.png")
            Image.fromarray(mask).save(msk_dir / f"img_{i}.png")
    return root


def make_spectral_tiff(root, n_images=2, size=16, n_bands=8):
    """root/{split}/images/img_{i}.tif — n_bands uint16 TIFF (needs tifffile)."""
    import tifffile

    root = Path(root)
    for split in ("train", "val"):
        img_dir = root / split / "images"
        msk_dir = root / split / "masks"
        img_dir.mkdir(parents=True, exist_ok=True)
        msk_dir.mkdir(parents=True, exist_ok=True)
        rng = _rng()
        for i in range(n_images):
            arr = rng.integers(0, 65535, (n_bands, size, size), dtype=np.uint16)
            tifffile.imwrite(img_dir / f"img_{i}.tif", arr)
            mask = np.zeros((size, size), dtype=np.uint8)
            mask[: size // 2] = 1
            Image.fromarray(mask).save(msk_dir / f"img_{i}.png")
    return root
