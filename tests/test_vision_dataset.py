"""Tests for the base VisionDataset contract."""

import pytest
import torch

from sihvision.data.errors import DatasetError, UnsupportedFormatError
from sihvision.data.vision_dataset import VisionDataset


class _Concrete(VisionDataset):
    def __init__(self):
        super().__init__(
            task="classification",
            classes=["a", "b"],
            channels=3,
        )

    def __len__(self):
        return 1

    def __getitem__(self, idx):
        return torch.zeros(3, 8, 8), torch.tensor(0), {"image_id": "x"}


def test_contract_attributes():
    ds = _Concrete()
    assert ds.task == "classification"
    assert ds.classes == ["a", "b"]
    assert ds.num_classes == 2
    assert ds.channels == 3


def test_contract_len_and_getitem():
    ds = _Concrete()
    assert len(ds) == 1
    images, targets, meta = ds[0]
    assert isinstance(images, torch.Tensor)
    assert isinstance(meta, dict)


def test_contract_is_abstract():
    with pytest.raises(TypeError):
        VisionDataset(task="classification", classes=[], channels=3)  # noqa: SLF001


def test_contract_has_verify_integrity():
    ds = _Concrete()
    assert hasattr(ds, "verify_integrity")
    ds.verify_integrity()


def test_errors_hierarchy():
    err = DatasetError("x")
    assert isinstance(err, ValueError)
    unsupported = UnsupportedFormatError("y")
    assert isinstance(unsupported, DatasetError)