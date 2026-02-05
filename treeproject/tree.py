# treeproject/tree.py

"""
Filesystem tree rendering utilities.

This module provides a lightweight, dependency-free utility to render a
directory structure as a human-readable Unicode tree, similar to the Unix
``tree`` command.

Traversal is deterministic (directories first, case-insensitive sorting),
supports optional symbolic link following, and relies on strict pruning-based
filtering: if a directory is excluded, its entire subtree is skipped.

The main entry point is :func:`path_tree`, which returns the rendered tree
as a string.
"""


from __future__ import annotations

from pathlib import Path
from typing import Callable


def is_dir(p: Path) -> bool:
    """
    Safely determine whether a path refers to a directory.

    This helper wraps ``Path.is_dir()`` to guard against filesystem-related
    errors (e.g. permission issues), returning ``False`` if the directory
    status cannot be determined.

    Parameters
    ----------
    p : pathlib.Path
        Path to test.

    Returns
    -------
    bool
        ``True`` if the path is a directory, ``False`` otherwise.
    """

    try:
        return p.is_dir()
    except OSError:
        return False


def path_tree(
    root: Path,
    *,
    follow_symlinks: bool = False,
    include: Callable[[Path], bool] = lambda p: True,
) -> str:
    """
    Render a directory tree as a Unicode string using a tree-style layout.

    Starting from ``root``, this function recursively traverses the filesystem
    and produces a visual representation of the directory structure using
    tree-style connectors (``├──``, ``└──``, ``│``).

    Traversal order is stable and deterministic:
    - directories are listed before files,
    - entries are sorted case-insensitively by name.

    Structural filtering is controlled via the ``include`` predicate. If
    ``include(path)`` returns ``False`` for a directory, that directory is
    pruned entirely and none of its descendants are visited.

    Parameters
    ----------
    root : pathlib.Path
        Root directory to display.
    follow_symlinks : bool, default=False
        Whether to follow symbolic links to directories during traversal.
    include : Callable[[pathlib.Path], bool], optional
        Predicate used to filter paths. If it returns ``False`` for a path,
        that path is neither displayed nor traversed. For directories, this
        results in full subtree pruning.

    Returns
    -------
    str
        The rendered directory tree as a single string.

    Raises
    ------
    OSError
        If a filesystem operation fails while resolving the root path.
    """

    root = root.resolve()
    lines: list[str] = [str(root)]

    def iter_children(d: Path) -> list[Path]:
        """
        Return the immediate children of a directory in stable tree order.

        Children are sorted such that directories appear before files, and all
        entries are ordered case-insensitively by name. If the directory cannot
        be read, an empty list is returned.

        Parameters
        ----------
        d : pathlib.Path
            Directory whose children should be listed.

        Returns
        -------
        list[pathlib.Path]
            Sorted list of child paths.
        """

        try:
            children = list(d.iterdir())
        except OSError:
            return []
        # Keep a stable, "tree-like" order: dirs first, then files; case-insensitive name sort.
        children.sort(key=lambda p: (not is_dir(p), p.name.casefold()))
        return children

    def rec(d: Path, prefix: str) -> None:
        """
        Recursively render a subtree with proper tree-style indentation.

        This function appends the children of a directory using the appropriate
        Unicode branch connectors and maintains vertical continuation bars for
        ancestor levels as needed.

        Directory traversal is subject to the ``include`` predicate and the
        ``follow_symlinks`` setting.

        Parameters
        ----------
        d : pathlib.Path
            Directory currently being traversed.
        prefix : str
            Prefix string used to align and draw tree branches.
        """

        # Prune + hide are the same here: if include() is False, we neither show nor descend.
        children = [c for c in iter_children(d) if include(c)]
        n = len(children)

        for i, child in enumerate(children):
            last = i == n - 1
            branch = "└── " if last else "├── "
            lines.append(prefix + branch + child.name)

            if is_dir(child):
                ext = "    " if last else "│   "
                if follow_symlinks or not child.is_symlink():
                    rec(child, prefix + ext)

    # If you want the filter to be able to exclude the root itself, handle it outside.
    rec(root, "")
    return "\n".join(lines)
