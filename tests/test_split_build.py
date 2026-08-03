"""Tests for split logic and the dataset factory."""

import pytest


def test_split_ratio_sizes(tmp_path):
    import numpy as np
    from PIL import Image

    from sihvision.data.split import split_dataset

    root = tmp_path / "cls"
    for c in range(3):
        d = root / "all" / f"class_{c}"
        d.mkdir(parents=True)
        for i in range(10):
            arr = np.zeros((8, 8, 3), dtype=np.uint8)
            Image.fromarray(arr).save(d / f"img_{i}.png")
    train, val, test = split_dataset(
        "classification", "folder_classification", root, ratio=[0.7, 0.15, 0.15]
    )
    total = 30
    train_expected = int(total * 0.7)
    assert len(train) == train_expected
    assert len(val) == int(total * 0.15)
    assert len(test) == total - train_expected - int(total * 0.15)


def test_split_rejects_bad_ratio(tmp_path):
    import numpy as np
    from PIL import Image

    from sihvision.data.split import split_dataset

    root = tmp_path / "cls"
    for c in range(2):
        d = root / "all" / f"class_{c}"
        d.mkdir(parents=True)
        for i in range(5):
            Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(d / f"img_{i}.png")
    with pytest.raises(ValueError, match="split_ratio"):
        split_dataset("classification", "folder_classification", root, ratio=[0.7, 0.3])


def test_split_sum_must_be_one(tmp_path):
    import numpy as np
    from PIL import Image

    from sihvision.data.split import split_dataset

    root = tmp_path / "cls"
    for c in range(2):
        d = root / "all" / f"class_{c}"
        d.mkdir(parents=True)
        for i in range(5):
            Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(d / f"img_{i}.png")
    with pytest.raises(ValueError, match="sum"):
        split_dataset("cls", "folder_classification", root, ratio=[0.9, 0.1, 0.1])


def test_build_dataset_unknown_task(tmp_path):
    from sihvision.data.build import build_dataset

    with pytest.raises(ValueError, match="task"):
        build_dataset("nonsense", "folder_classification", tmp_path)


def test_build_dataset_unknown_format(tmp_path):
    from sihvision.data.build import build_dataset

    with pytest.raises(ValueError, match="format"):
        build_dataset("classification", "nonsense", tmp_path)