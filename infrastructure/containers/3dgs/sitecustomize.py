#!/usr/bin/env python3
"""
Runtime monkeypatches for SageMaker Nerfstudio execution.

Nerfstudio's default PIL -> numpy conversion path can break in our container
with Pillow ABI mismatches (`TypeError: function takes exactly 2 arguments`).
Using numpy's direct array conversion avoids that path entirely while
preserving uint8 image tensors for training.
"""

from __future__ import annotations

import os
import numpy as np


# Force gsplat/PyTorch JIT builds to target only modern GPU architectures.
# Older defaults (sm_35/sm_37/sm_50) fail on cooperative_groups::labeled_partition.
os.environ.setdefault("TORCH_CUDA_ARCH_LIST", "7.0;8.0;8.6+PTX")
os.environ.setdefault("CUDAARCHS", "70;80;86")


def _patch_cuda_arch_flags() -> None:
    try:
        from torch.utils import cpp_extension

        original = cpp_extension._get_cuda_arch_flags

        def _filtered_cuda_arch_flags(cflags=None):
            flags = original(cflags)
            blocked = ("compute_35", "sm_35", "compute_37", "sm_37", "compute_50", "sm_50")
            return [flag for flag in flags if not any(token in flag for token in blocked)]

        cpp_extension._get_cuda_arch_flags = _filtered_cuda_arch_flags
        print(
            "✅ sitecustomize: filtered deprecated CUDA arch flags "
            f"(TORCH_CUDA_ARCH_LIST={os.environ['TORCH_CUDA_ARCH_LIST']})"
        )
    except Exception as exc:  # pragma: no cover - best-effort runtime shim
        print(f"⚠️ sitecustomize: could not patch CUDA arch flags: {exc}")


def _patched_pil_to_numpy(pil_image):
    array = np.asarray(pil_image)
    if array.dtype != np.uint8:
        array = array.astype(np.uint8)
    return np.array(array, copy=True)


_patch_cuda_arch_flags()


try:
    from nerfstudio.data.utils import data_utils
    from nerfstudio.data.datasets import base_dataset

    data_utils.pil_to_numpy = _patched_pil_to_numpy
    base_dataset.pil_to_numpy = _patched_pil_to_numpy
    print("✅ sitecustomize: patched nerfstudio PIL conversion")
except Exception as exc:  # pragma: no cover - best-effort runtime shim
    print(f"⚠️ sitecustomize: could not patch nerfstudio PIL conversion: {exc}")
