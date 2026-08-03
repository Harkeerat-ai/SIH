"""Tests for synthetic fixture generators."""

from tests.fixtures.generate_synthetic import (
    make_change_detection,
    make_classification,
    make_detection,
    make_segmentation,
)


def test_make_classification(tmp_path):
    root = make_classification(tmp_path / "cls", n_classes=3, per_class=4)
    assert (root / "train" / "class_0" / "img_0.png").exists()
    assert len(list((root / "val" / "class_2").glob("*.png"))) == 4


def test_make_detection(tmp_path):
    root = make_detection(tmp_path / "det", n_images=5)
    assert len(list((root / "train" / "images").glob("*.png"))) == 5
    assert len(list((root / "train" / "labels").glob("*.txt"))) == 5
    first = (root / "train" / "labels" / "img_0.txt").read_text()
    parts = first.split()
    assert len(parts) == 5
    assert float(parts[1]) <= 1.0


def test_make_segmentation(tmp_path):
    root = make_segmentation(tmp_path / "seg", n_images=5, n_classes=4)
    assert len(list((root / "train" / "masks").glob("*.png"))) == 5


def test_make_change_detection(tmp_path):
    root = make_change_detection(tmp_path / "cd", n_images=5)
    assert len(list((root / "train" / "t1").glob("*.png"))) == 5
    assert len(list((root / "train" / "t2").glob("*.png"))) == 5
    assert len(list((root / "train" / "masks").glob("*.png"))) == 5