# treeproject/pretty.py
from __future__ import annotations

from pathlib import Path

from anytree import RenderTree, ContStyle

from .tree import build_tree

__all__ = ["draw_tree", "build_and_draw_tree"]


def draw_tree(node) -> str:
    """
    Return a readable UTF-8 text representation of a filesystem tree.

    Parameters
    ----------
    node : anytree.Node
        Root node of the tree. Only the node's ``name`` attribute is printed.

    Returns
    -------
    str
        A multi-line string showing the hierarchical structure of the tree,
        using Unicode line-drawing characters (├──, └──, │).
    """
    lines = []
    for pre, _fill, n in RenderTree(node, style=ContStyle):
        lines.append(f"{pre}{n.name}")
    return "\n".join(lines)


def build_and_draw_tree(
        root: str | Path,
        *,
        follow_symlinks: bool = False,
        exclude: list[str] | None = None,
) -> str:
    """
    Build a filesystem tree using ``build_tree()`` and return its text representation.

    This function exists for convenience when you want to obtain the rendered tree
    directly without manipulating the intermediate anytree structure.

    Parameters
    ----------
    root : str | Path
        Filesystem root to scan.
    follow_symlinks : bool, optional
        Whether to descend into symlinked directories.
    exclude : list[str] | None, optional
        Gitignore-like exclusion patterns.

    Returns
    -------
    str
        UTF-8 rendered tree representation returned by :func:`draw_tree`.
    """
    node = build_tree(
        root,
        follow_symlinks=follow_symlinks,
        exclude=exclude,
    )
    return draw_tree(node)
