# treeproject/content.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from anytree import PreOrderIter
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

from .tree import build_tree

__all__ = ["get_files_content", "get_files_content_from_node"]


def _compile_spec(patterns: Optional[List[str]]) -> PathSpec:
    return PathSpec.from_lines(GitWildMatchPattern, patterns or [])


def _should_include_file(p: Path, include_exts: Optional[Iterable[str]]) -> bool:
    """
    Return True if the file `p` passes the include filter.
    - include_exts: iterable of extensions like [".py", ".txt"] (case-insensitive).
      If None or empty, everything is included.
    """
    if not include_exts:
        return True
    # Normalize extensions: ensure leading dot, lowercase
    normalized = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in include_exts}
    return p.suffix.lower() in normalized


def _is_excluded(p: Path, root: Path, spec: PathSpec) -> bool:
    """
    Apply gitignore-like exclusion relative to `root`.
    """
    try:
        rel = p.relative_to(root).as_posix()
    except ValueError:
        # Fallback; shouldn't happen for subtree traversal
        rel = p.as_posix()
    return spec.match_file(rel)


def _render_block(root: Path, p: Path, content: str) -> str:
    """
    Render a single file block in the requested format:

    {relative_path}
    < content >
    """
    rel = p.relative_to(root).as_posix()
    header = f"{root.name}/{rel}"
    return f'"""{header}\n{content}\n"""'


def get_files_content(
        root: str | Path,
        *,
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        ignore_file_type_error: bool = False,
        encoding: str = "utf-8",
) -> str:
    """
    Return a concatenated string with the contents of selected files under `root`.

    Selection rules
    ---------------
    - `exclude`: list of gitignore-like patterns (relative to `root`).
    - `include`: list of file extensions to keep (e.g., [".py", ".txt"]). If None/empty,
      all files are considered (subject to `exclude`).
    - If a file cannot be decoded with `encoding`, raise `UnicodeDecodeError` unless
      `ignore_file_type_error=True`, in which case the file is skipped.

    Output format
    -------------
    For each selected file, append a block:

    {relative / path /
    from / root}
    < file
    content >

    Parameters
    ----------
    root : str | Path
        Filesystem root to scan.
    exclude : list[str] | None
        Gitignore-like exclusion patterns.
    include : list[str] | None
        List of extensions to include (e.g., [".py", ".txt"]). Case-insensitive.
    ignore_file_type_error : bool
        Skip unreadable / non-text files when True; otherwise raise.
    encoding : str
        Text encoding used to read files (default 'utf-8').

    Returns
    -------
    str
        Concatenation of all file blocks separated by a blank line.
    """
    root_path = Path(root).expanduser().resolve(strict=False)
    node = build_tree(root_path, exclude=exclude)
    return get_files_content_from_node(
        node,
        exclude=exclude,
        include=include,
        ignore_file_type_error=ignore_file_type_error,
        encoding=encoding,
    )


def get_files_content_from_node(
        node,
        *,
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        ignore_file_type_error: bool = False,
        encoding: str = "utf-8",
) -> str:
    """
    Return a concatenated string with the contents of selected files within the subtree `node`.

    The relative paths in the output are computed from `node.fs_path` (the subtree root).

    Parameters
    ----------
    node : anytree.Node
        Subtree root. Must carry `fs_path` (Path) and `is_dir` attributes as set by `build_tree`.
    exclude : list[str] | None
        Gitignore-like exclusion patterns, applied relative to `node.fs_path`.
    include : list[str] | None
        List of file extensions to include (e.g., [".py", ".txt"]). Case-insensitive.
    ignore_file_type_error : bool
        Skip unreadable / non-text files when True; otherwise raise.
    encoding : str
        Text encoding used to read files (default 'utf-8').

    Returns
    -------
    str
        Concatenation of file blocks as specified in `get_files_content()`.
    """
    root = getattr(node, "fs_path")
    spec = _compile_spec(exclude)
    selected: list[Path] = []

    # Collect matching files within the subtree (pre-order)
    for n in PreOrderIter(node):
        if getattr(n, "is_dir", False):
            continue
        p: Path = getattr(n, "fs_path")
        if _is_excluded(p, root, spec):
            continue
        if not _should_include_file(p, include):
            continue
        selected.append(p)

    # Stable output: sort by relative POSIX path
    selected.sort(key=lambda p_: p_.relative_to(root).as_posix())

    blocks: list[str] = []
    for p in selected:
        try:
            content = p.read_text(encoding=encoding)
        except (UnicodeDecodeError, PermissionError, OSError):
            if ignore_file_type_error:
                continue
            raise
        blocks.append(_render_block(root, p, content))

    return "\n\n".join(blocks)
