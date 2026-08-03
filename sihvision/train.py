"""Unified trainer across classification / segmentation / change detection.

Detection is delegated to the external YOLO trainer and is out of scope here.
Regression shares the classification loop with MSE in place of cross-entropy.
"""

import contextlib
import time

import torch
import torch.nn as nn

from sihvision.config import VALID_TASKS


def _loss_for_task(task):
    if task in ("classification", "change_detection", "segmentation"):
        return nn.CrossEntropyLoss()
    if task == "regression":
        return nn.MSELoss()
    raise ValueError(f"Unsupported task for training: {task!r}")


class Trainer:
    """Runs ``epochs`` passes over a dataset for a given task model."""

    def __init__(self, cfg, model, device="auto", epochs=None, lr=None):
        self.cfg = cfg
        self.model = model
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model.to(self.device)
        self.loss_fn = _loss_for_task(cfg["task"])
        train_cfg = cfg.get("train", {}) or {}
        self.epochs = epochs or train_cfg.get("epochs", 1)
        self.lr = lr or train_cfg.get("lr", 1e-3)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)

    def train(self, loader):
        pass

    def _move(self, batch):
        images, targets, _ = batch
        for k in ("t1", "t2"):
            if isinstance(images, dict):
                images[k] = images[k].to(self.device)
            else:
                break
        if isinstance(images, dict):
            return images, targets.to(self.device) if isinstance(targets, torch.Tensor) else targets
        return images.to(self.device), targets.to(self.device)

    def run_epoch(self, dataset, phase="train"):
        """Run one epoch (train or eval) and return average loss (float)."""
        if phase == "train":
            self.model.train()
        else:
            self.model.eval()
        total_loss, n = 0.0, 0
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")
        for batch in _batched(dataset, batch_size=4):
            images, targets = self._move(batch)
            if isinstance(images, dict):
                logits = self.model(images)
                mask = targets.to(self.device)  # [N,H,W] long
            else:
                logits = self.model(images)
                if self.cfg["task"] == "regression":
                    mask = targets.to(self.device).view(-1, 1)  # [N,1]
                else:
                    mask = targets  # [N] or [B,H,W]
            loss = self.loss_fn(logits, mask)
            if phase == "train":
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
            total_loss += loss.detach().item() * len(batch)
            n += len(batch)
        return total_loss / n


def _batched(dataset, batch_size):
    """Yield non-overlapping tuples of samples up to ``batch_size`` fields."""
    idx = 0
    while idx < len(dataset):
        batch = [dataset[i] for i in range(idx, min(idx + batch_size, len(dataset)))]
        # stack
        imgs = batch[0][0]
        if isinstance(imgs, dict):
            keys = list(imgs)
            stacked = {k: torch.stack([b[0][k] for b in batch]) for k in keys}
        else:
            stacked = torch.stack([b[0] for b in batch])
        tgt = torch.stack([b[1] for b in batch])
        yield stacked, tgt, [b[2] for b in batch]
        idx += batch_size


def train(cfg, model, train_ds, val_ds=None, device="cpu", epochs=None):
    """Train ``model`` for ``epochs`` epochs, returning history of losses.

    Detection is intentionally unsupported here (use YOLO trainer instead).
    """
    if cfg["task"] == "detection":
        raise NotImplementedError(
            "Detection training uses the YOLO trainer, not sihvision.Trainer."
        )
    trainer = Trainer(cfg, model, device=device, epochs=epochs)
    history = {"train": [], "val": []}
    for ep in range(trainer.epochs):
        train_loss = trainer.run_epoch(train_ds, "train")
        history["train"].append(train_loss)
        if val_ds is not None:
            history["val"].append(trainer.run_epoch(val_ds, "val"))
    return history