"""Tests for the explainability dashboard rendering."""

import numpy as np


def _img_png_bytes():
    from PIL import Image

    import io

    arr = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def test_dashboard_renders_html():
    from sihvision.dashboard import render_dashboard

    html = render_dashboard(
        image=_img_png_bytes(),
        saliency=_img_png_bytes(),
        title="Satellite Scene",
        predictions=[("urban", 0.91), ("water", 0.08), ("forest", 0.01)],
    )
    assert isinstance(html, str)
    assert "<html" in html
    assert "Satellite Scene" in html
    assert "urban" in html
    assert "91.0%" in html


def test_dashboard_embeds_overlay_js():
    from sihvision.dashboard import render_dashboard

    html = render_dashboard(
        image=_img_png_bytes(),
        saliency=_img_png_bytes(),
    )
    # saliency overlay blended via JS/canvas
    assert "canvas" in html
    assert "overlay" in html.lower()


def test_dashboard_missing_saliency_still_renders():
    from sihvision.dashboard import render_dashboard

    html = render_dashboard(image=_img_png_bytes())
    assert "<html" in html