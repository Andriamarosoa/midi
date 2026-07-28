"""Compatibility helpers shared by Keras 2 and Keras 3 runtimes."""

from __future__ import annotations

import inspect
from typing import Any


def predict_compat(
    model: Any,
    inputs: Any,
    *,
    verbose: int = 0,
    workers: int = 1,
) -> Any:
    """Call ``predict`` without legacy queue options on Keras 3."""
    kwargs: dict[str, object] = {"verbose": int(verbose)}
    if "workers" in inspect.signature(model.predict).parameters:
        kwargs["workers"] = int(workers)
    return model.predict(inputs, **kwargs)
