"""Explainability dashboard: renders a self-contained HTML page.

The page shows the input image, a saliency overlay (heatmap blended via
canvas), the model's prediction list, and sliders to toggle the overlay
opacity. All assets are inline so the page can be served by any static
handler or saved as a standalone file.
"""

import base64
import html as html_lib

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f6f7f9; }}
h1 {{ color: #1a1a2e; }}
.card {{ background: white; border-radius: 12px; padding: 1.5rem;
         box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 1.5rem; }}
img, canvas {{ max-width: 100%; border-radius: 8px; }}
.controls {{ margin-top: 1rem; }}
.slider {{ width: 240px; }}
table {{ border-collapse: collapse; }}
td, th {{ padding: .4rem .9rem; border-bottom: 1px solid #e3e6ea; text-align: left; }}
.bar {{ display: inline-block; height: 12px; background: #4f46e5; border-radius: 6px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="card">
  <h2>Saliency overlay</h2>
  <canvas id="stage"></canvas>
  <div class="controls">
    <label>Overlay opacity: <input type="range" class="slider" id="opacity"
           min="0" max="1" step="0.05" value="0.5"></label>
  </div>
</div>
<div class="card">
  <h2>Predictions</h2>
  {predictions_html}
</div>
<script>
const imageData = "{image_b64}";
const saliencyData = "{saliency_b64}";
const image = new Image();
const saliency = new Image();
const canvas = document.getElementById('stage');
const ctx = canvas.getContext('2d');
const slider = document.getElementById('opacity');
let ready = 0;

function draw() {{
  if (ready < 2) return;
  canvas.width = image.width; canvas.height = image.height;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);
  ctx.globalAlpha = parseFloat(slider.value);
  ctx.drawImage(saliency, 0, 0);
  ctx.globalAlpha = 1;
}}
image.onload = () => {{ ready++; draw(); }};
saliency.onload = () => {{ ready++; draw(); }};
slider.oninput = draw;
if (imageData) image.src = "data:image/png;base64," + imageData;
if (saliencyData) saliency.src = "data:image/png;base64," + saliencyData;
</script>
</body>
</html>
"""


def _b64(png_bytes):
    if png_bytes is None:
        return ""
    return base64.b64encode(bytes(png_bytes)).decode("ascii")


def render_dashboard(image, saliency=None, title="sihvision Explainability", predictions=None):
    """Render a self-contained HTML dashboard.

    Args:
        image: PNG bytes of the input image (required).
        saliency: PNG bytes of the saliency heatmap (optional).
        title: page title.
        predictions: list of (class_name, score) tuples (optional).
    """
    predictions = predictions or []
    if predictions:
        rows = []
        for name, score in predictions:
            pct = max(0.0, min(1.0, float(score))) * 100
            rows.append(
                "<tr>"
                f"<td>{html_lib.escape(str(name))}</td>"
                f"<td>{pct:.1f}%</td>"
                f"<td><span class='bar' style='width:{pct * 2:.0f}px'></span></td>"
                "</tr>"
            )
        pred_html = (
            "<table><tr><th>Class</th><th>Confidence</th><th></th></tr>"
            + "".join(rows)
            + "</table>"
        )
    else:
        pred_html = "<p>No predictions supplied.</p>"

    return _TEMPLATE.format(
        title=html_lib.escape(title),
        predictions_html=pred_html,
        image_b64=_b64(image),
        saliency_b64=_b64(saliency),
    )