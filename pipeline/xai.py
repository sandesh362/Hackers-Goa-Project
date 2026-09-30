"""Integrated Gradients explanations for the selected ViT classifier."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

IG_STEPS = 16
OVERLAY_ALPHA = 0.45


def integrated_gradients(model: Any, image_processor: Any, image: Image.Image,
                         target_class: int, steps: int = IG_STEPS) -> np.ndarray:
    """Compute positive Integrated Gradients attribution, resized to source dimensions.

    Unlike Grad-CAM, Integrated Gradients applies to ViT inputs without inventing a
    convolutional target layer. It attributes the chosen class score along a straight
    path from the processor-space zero baseline to the preprocessed input.
    """
    import torch
    inputs = image_processor(images=image.convert("RGB"), return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(next(model.parameters()).device)
    baseline = torch.zeros_like(pixel_values)
    accumulated = torch.zeros_like(pixel_values)
    model.eval()
    for index in range(1, steps + 1):
        alpha = index / steps
        sample = (baseline + alpha * (pixel_values - baseline)).detach().requires_grad_(True)
        model.zero_grad(set_to_none=True)
        logits = model(pixel_values=sample).logits
        gradient = torch.autograd.grad(logits[0, target_class], sample, retain_graph=False)[0]
        accumulated += gradient.detach()
    attribution = (pixel_values - baseline) * (accumulated / steps)
    # Positive evidence for the selected class; not a manipulated-pixel mask.
    relevance = torch.relu(attribution).sum(dim=1)[0]
    relevance = relevance.detach().cpu().numpy()
    relevance -= float(relevance.min())
    peak = float(relevance.max())
    if not np.isfinite(peak) or peak <= 1e-12:
        raise RuntimeError("Integrated Gradients returned an empty attribution map.")
    relevance = np.clip(relevance / peak, 0.0, 1.0)
    return np.asarray(Image.fromarray(np.uint8(relevance * 255)).resize(image.size, Image.Resampling.BILINEAR), dtype=np.float32) / 255.0


def _heat_colors(values: np.ndarray) -> np.ndarray:
    """Apply a compact jet-like color map without an extra visualization dependency."""
    v = np.clip(values, 0.0, 1.0)
    channels = [np.clip(1.5 - np.abs(4 * v - shift), 0, 1) for shift in (3, 2, 1)]
    return np.stack(channels, axis=-1)


def save_explanation_images(original: Image.Image, attribution: np.ndarray,
                            output_dir: str | Path) -> dict[str, Path]:
    """Write a standalone heatmap and blended overlay at original image dimensions."""
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(original.convert("RGB"), dtype=np.float32) / 255.0
    heat = _heat_colors(attribution)
    overlay = np.clip((1 - OVERLAY_ALPHA * attribution[..., None]) * rgb +
                      OVERLAY_ALPHA * attribution[..., None] * heat, 0, 1)
    heatmap_path, overlay_path = folder / "integrated_gradients_heatmap.png", folder / "integrated_gradients_overlay.png"
    Image.fromarray(np.uint8(heat * 255)).save(heatmap_path, format="PNG", optimize=True)
    Image.fromarray(np.uint8(overlay * 255)).save(overlay_path, format="PNG", optimize=True)
    return {"heatmap": heatmap_path, "overlay": overlay_path}
