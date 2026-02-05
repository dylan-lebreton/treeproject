"""
treeproject — lightweight filesystem tree and content utilities.

This package provides simple, composable tools to:
- render directory structures as readable trees,
- extract and concatenate file contents with fine-grained filtering.

The API is based on ``pathlib.Path`` and is designed to be dependency-free,
deterministic, and suitable for programmatic as well as human-facing use
cases.
"""

from __future__ import annotations

from .tree import path_tree
from .content import path_content

__all__ = ["path_tree", "path_content"]
