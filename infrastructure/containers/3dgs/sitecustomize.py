#!/usr/bin/env python3
"""
Runtime monkeypatches for SageMaker Nerfstudio execution.

Nerfstudio's default PIL -> numpy conversion path can break in our container
with Pillow ABI mismatches (`TypeError: function takes exactly 2 arguments`).
Using numpy's direct array conversion avoids that path entirely while
preserving uint8 image tensors for training.
"""

from __future__ import annotations

import numpy as np


def _patched_pil_to_numpy(pil_image):
    array = np.asarray(pil_image)
    if array.dtype != np.uint8:
        array = array.astype(np.uint8)
    return np.array(array, copy=True)


try:
    from nerfstudio.data.utils import data_utils
    from nerfstudio.data.datasets import base_dataset

    data_utils.pil_to_numpy = _patched_pil_to_numpy
    base_dataset.pil_to_numpy = _patched_pil_to_numpy
    print("✅ sitecustomize: patched nerfstudio PIL conversion")
except Exception as exc:  # pragma: no cover - best-effort runtime shim
    print(f"⚠️ sitecustomize: could not patch nerfstudio PIL conversion: {exc}")
