"""Explainable-AI saliency for sihvision models.

``saliency_map`` produces a single-channel heatmap in [0,1] over the input
image for a trained model, using either:

- ``gradcam`` — Grad-CAM over the last conv feature map (Selvaraju et al.)
- ``vanilla`` — absolute gradient of the target logit w.r.t. the input
"""

import torch
import torch.nn as nn


class _GradHook:
    """Stores the forward activations and backward gradients of a module."""

    def __init__(self, module):
        self.activations = None
        self.gradients = None
        self._fh = module.register_forward_hook(self._fwd)
        self._bh = module.register_full_backward_hook(self._bwd)

    def _fwd(self, module, inp, out):
        self.activations = out.detach()

    def _bwd(self, module, grad_in, grad_out):
        self.gradients = grad_out[0].detach()

    def remove(self):
        self._fh.remove()
        self._bh.remove()


def _find_last_conv(model):
    """Return the last nn.Conv2d module in the model tree, or None."""
    last = None

    def walk(module):
        nonlocal last
        for child in module.children():
            if isinstance(child, nn.Conv2d):
                last = child
            else:
                walk(child)

    walk(model)
    return last


def _freeze(model):
    """Set requires_grad=False on all params; return prev state."""
    prev = [p.requires_grad for p in model.parameters()]
    for p in model.parameters():
        p.requires_grad = False
    return prev


def _unfreeze(model, prev):
    for p, flag in zip(model.parameters(), prev):
        p.requires_grad = flag


def _norm01(x):
    """Normalize a [H,W] tensor to [0,1]."""
    lo = x.min()
    hi = x.max()
    if hi <= lo:
        return torch.zeros_like(x)
    return (x - lo) / (hi - lo)


def _gradcam_impl(model, image, class_idx, spatial=False):
    conv = _find_last_conv(model)
    if conv is None:
        raise ValueError(
            "Grad-CAM requires at least one conv layer; none found in model"
        )
    hook = _GradHook(conv)
    prev = _freeze(model)
    model.eval()

    image = image.detach().clone().requires_grad_(True)
    logits = model(image)
    if not isinstance(logits, torch.Tensor):
        raise ValueError("saliency targets a single-tensor-output model")
    target = _salient_target(logits, class_idx, spatial=spatial)
    model.zero_grad()
    target.backward()

    acts = hook.activations[0]  # [C, H', W']
    grads = hook.gradients[0]   # [C, H', W']
    weights = grads.flatten(1).mean(dim=1)  # [C]
    cam = torch.relu((weights[:, None, None] * acts).sum(dim=0))  # [H', W']
    hook.remove()
    _unfreeze(model, prev)

    if cam.shape != image.shape[-2:]:
        cam = torch.nn.functional.interpolate(
            cam[None, None],
            size=image.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )[0, 0]
    return _norm01(cam)


def _vanilla_impl(model, image, class_idx, spatial=False):
    prev = _freeze(model)
    model.eval()
    image = image.detach().clone().requires_grad_(True)
    logits = model(image)
    if not isinstance(logits, torch.Tensor):
        raise ValueError("Vanilla saliency needs a tensor output")
    target = _salient_target(logits, class_idx, spatial=spatial)
    model.zero_grad()
    target.backward()
    grad = image.grad.abs().mean(dim=1)[0]  # [H, W]
    _unfreeze(model, prev)
    return _norm01(grad)


def _salient_target(logits, class_idx, spatial=False):
    """Return the scalar target to backprop into."""
    if spatial:
        # For segmentation, backprop the mean of all class logits so the
        # whole predictive map contributes.
        return logits.flatten().sum()
    logits = logits.flatten()
    idx = class_idx if class_idx is not None else int(logits.argmax())
    return logits[idx]


def _gradcam_cd(model, images):
    """Grad-CAM for change detection: diff magnitude drives saliency."""
    # The shared backbone runs both streams; hook its last conv.
    conv = _find_last_conv(model.backbone)
    if conv is None:
        raise ValueError("Grad-CAM requires a conv layer; none found")
    prev = _freeze(model)
    model.eval()
    t1 = images["t1"].detach().clone().requires_grad_(True)
    t2 = images["t2"].detach().clone().requires_grad_(True)
    hook = _GradHook(conv)
    f1 = model.backbone(t1)
    f2 = model.backbone(t2)
    # Diff feature magnitude as the saliency signal.
    diff = (f1 - f2).abs().sum(dim=1).mean()
    model.zero_grad()
    diff.backward()
    grads = hook.gradients[0]
    acts = hook.activations[0]
    weights = grads.flatten(1).mean(dim=1)
    cam = torch.relu((weights[:, None, None] * acts).sum(dim=0))
    hook.remove()
    _unfreeze(model, prev)
    size = images["t1"].shape[-2:]
    if cam.shape != size:
        cam = torch.nn.functional.interpolate(
            cam[None, None], size=size, mode="bilinear", align_corners=False
        )[0, 0]
    return _norm01(cam)


def _vanilla_cd(model, images):
    """Vanilla gradient of the change magnitude w.r.t. t2."""
    prev = _freeze(model)
    model.eval()
    t1 = images["t1"].detach().clone().requires_grad_(True)
    t2 = images["t2"].detach().clone().requires_grad_(True)
    f1 = model.backbone(t1)
    f2 = model.backbone(t2)
    diff = (f1 - f2).abs().sum(dim=1).mean()
    model.zero_grad()
    diff.backward()
    grad = t2.grad.abs().mean(dim=1)[0]
    _unfreeze(model, prev)
    return _norm01(grad)


def saliency_map(model, image, method="gradcam", class_idx=None):
    """Compute a [H, W] saliency heatmap in [0,1].

    Supports single-tensor input (classification / regression / segmentation)
    and change-detection dict input (``{"t1": .., "t2": ..}``).

    Args:
        model: sihvision task model.
        image: [1, C, H, W] tensor or {"t1": .., "t2": ..} dict.
        method: ``gradcam`` or ``vanilla``.
        class_idx: target index; defaults to argmax.
    """
    if method not in ("gradcam", "vanilla"):
        raise ValueError(
            f"method must be 'gradcam' or 'vanilla', got {method!r}"
        )
    is_dict = isinstance(image, dict)
    if not is_dict and (image.ndim != 4 or image.shape[0] != 1):
        raise ValueError(
            f"image must be [1, C, H, W], got shape {tuple(image.shape)}"
        )
    if is_dict:
        if method == "gradcam":
            return _gradcam_cd(model, image)
        return _vanilla_cd(model, image)
    # Determine whether this is a spatial-output (segmentation) model.
    probe = image.detach().clone().requires_grad_(True)
    with torch.no_grad():
        out = model(probe)
    spatial = isinstance(out, torch.Tensor) and out.ndim == 4
    if method == "gradcam":
        return _gradcam_impl(model, image, class_idx, spatial=spatial)
    return _vanilla_impl(model, image, class_idx, spatial=spatial)