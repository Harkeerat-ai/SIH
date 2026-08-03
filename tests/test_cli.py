"""Smoke tests for the check-data CLI."""

import numpy as np
from PIL import Image


def _make_split(root, n_classes=3, per_class=5):
    for c in range(n_classes):
        d = root / "all" / f"class_{c}"
        d.mkdir(parents=True)
        for i in range(per_class):
            arr = np.zeros((16, 16, 3), dtype=np.uint8)
            arr[..., c] = 255
            Image.fromarray(arr).save(d / f"img_{i}.png")
    return root


def test_check_data_cli_smoke(tmp_path, capsys):
    from sihvision.cli.check_data import main

    _make_split(tmp_path / "data")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        f"task: classification\ndata:\n  format: folder_classification\n"
        f"  root: {str(tmp_path / 'data').replace(chr(92), '/')}\n"
        f"  channels: 3\n"
    )
    rc = main([str(cfg), "--split", "all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "num_classes: 3" in out
    assert "len(all): 15" in out


def test_check_data_cli_missing_config(tmp_path, capsys):
    from sihvision.cli.check_data import main

    cfg = tmp_path / "nope.yaml"
    rc = main([str(cfg)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "ERROR" in err