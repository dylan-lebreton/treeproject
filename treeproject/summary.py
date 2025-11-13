# treeproject/summary.py
from __future__ import annotations

from pathlib import Path

from .content import get_files_content_from_node
from .pretty import draw_tree
from .tree import build_tree

__all__ = ["build_tree_and_contents"]


def build_tree_and_contents(
        root: str | Path,
        *,
        # Params for the tree build
        tree_follow_symlinks: bool = False,
        tree_exclude: list[str] | None = None,
        # Params for the file contents (independent filtering)
        content_exclude: list[str] | None = None,
        content_include: list[str] | None = None,
        content_ignore_file_type_error: bool = False,
        encoding: str = "utf-8",
) -> str:
    """
    Build the filesystem tree once, then return a single string containing:
      1) the rendered directory tree, and
      2) the concatenated contents of selected files.

    The tree is built with its own options (follow_symlinks/exclude).
    File contents are filtered independently (include/exclude) from the already-built tree.

    Parameters
    ----------
    root : str | Path
        Directory to scan.
    tree_follow_symlinks : bool
        Whether to descend into symlinked directories when building the tree.
    tree_exclude : list[str] | None
        Gitignore-like exclusion patterns applied to the tree build.
    content_exclude : list[str] | None
        Gitignore-like exclusion patterns for content extraction (relative to root).
    content_include : list[str] | None
        File extensions to include for content extraction (e.g. [".py", ".txt"]).
        If None/empty, all files are considered (subject to content_exclude).
    content_ignore_file_type_error : bool
        If True, skip unreadable/non-text files; otherwise raise.
    encoding : str
        Text encoding used to read files (default "utf-8").

    Returns
    -------
    str
        Tree (UTF-8 with unicode connectors), then a blank line, then zero or more
        file blocks of the form:

            \"\"\"<root.name>/<relative/path>
            <file content>
            \"\"\"

        If no files match the content selection, only the tree is returned.
    """
    # Build once
    node = build_tree(root, follow_symlinks=tree_follow_symlinks, exclude=tree_exclude)

    # Render tree from the in-memory node
    tree_str = draw_tree(node)

    # Extract contents from the same node, with independent filters
    contents_str = get_files_content_from_node(
        node,
        exclude=content_exclude,
        include=content_include,
        ignore_file_type_error=content_ignore_file_type_error,
        encoding=encoding,
    )

    return f"{tree_str}\n\n{contents_str}" if contents_str.strip() else tree_str
