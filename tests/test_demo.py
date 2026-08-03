"""Tests for the end-to-end demo pipeline."""

import numpy as np


def test_demo_run(tmp_path):
    import torch

    torch.manual_seed(0)
    from sihvision.demo import run_demo

    out_dir = tmp_path / "out"
    result = run_demo(
        root=tmp_path / "data",
        out_dir=out_dir,
        n_per_class=6,
        img_size=32,
        epochs=2,
        lr=1e-3,
    )
    assert result["history"] is not None
    assert len(result["history"]["train"]) == 2
    assert result["prediction"] is not None
    assert isinstance(result["prediction"]["probs"], list)
    assert (out_dir / "dashboard.html").is_file()
    html = (out_dir / "dashboard.html").read_text(encoding="utf-8")
    assert "<html" in html


def test_demo_saliency_file_written(tmp_path):
    import torch

    torch.manual_seed(0)
    from sihvision.demo import run_demo

    out_dir = tmp_path / "out2"
    result = run_demo(
        root=tmp_path / "data2",
        out_dir=out_dir,
        n_per_class=4,
        img_size=32,
        epochs=1,
        lr=1e-3,
    )
    assert result["saliency"] is not None
    assert result["saliency"].ndim == 2


def test_demo_rejects_missing_out_dir_parent(tmp_path):
    import torch

    torch.manual_seed(0)
    from sihvision.demo import run_demo

    result = run_demo(
        root=tmp_path / "data3",
        out_dir=tmp_path / "sub" / "deep" / "out",
        n_per_class=4,
        img_size=32,
        epochs=1,
        lr=1e-3,
    )
    assert (tmp_path / "sub" / "deep" / "out" / "dashboard.html").is_file()