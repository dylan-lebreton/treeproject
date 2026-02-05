# treeproject/content.py

"""
Filesystem content extraction utilities.

This module provides helpers to extract and concatenate the textual contents
of files from a filesystem path. It is designed to complement the tree
rendering utilities by enabling content bundling for documentation,
debugging, or large-language-model (LLM) context generation.

Features include:
- structured file content formatting,
- optional binary file detection and skipping,
- deterministic traversal order,
- pruning-based structural filtering,
- configurable encoding and error-handling strategies.
"""


from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal

from treeproject.tree import print_tree


def file_to_text(
    path: Path,
    *,
    root: Path | None = None,
    encoding: str = "utf-8",
) -> str:
    """
    Read a text file and return a formatted textual block.

    The returned string embeds both the file path and its full textual content,
    using a stable delimiter format suitable for concatenation, logging, or
    downstream processing (e.g. LLM context building).

    If a ``root`` is provided, the file path is rendered relative to that root.
    Otherwise, the absolute resolved path is used.

    Parameters
    ----------
    path : pathlib.Path
        Path to the file to read. Must refer to a regular file.
    root : pathlib.Path | None, optional
        Base path used to compute a relative path for display. If ``None``,
        the absolute resolved path is used instead.
    encoding : str, default="utf-8"
        Text encoding used to decode the file.

    Returns
    -------
    str
        A formatted text block containing the file path and its contents.

    Raises
    ------
    ValueError
        If ``path`` does not refer to a regular file.
    OSError
        If the file cannot be read.
    UnicodeDecodeError
        If the file cannot be decoded using the specified encoding.
    """

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    data = path.read_text(encoding=encoding)  # may raise UnicodeDecodeError / OSError

    if root is not None:
        header_path = path.resolve().relative_to(root.resolve()).as_posix()
    else:
        header_path = path.resolve().as_posix()

    return f"===== FILE: {header_path} =====\n" f"{data}\n" f"===== END FILE ====="


def is_binary_file(path: Path, *, sample_size: int = 8192) -> bool:
    """
    Heuristically determine whether a file appears to be binary.

    The detection is based on reading a small byte sample and checking for:
    - the presence of NUL bytes (strong binary indicator),
    - a high proportion of non-text ASCII control or extended bytes.

    This function is intended as a fast, best-effort heuristic and does not
    guarantee perfect classification.

    Parameters
    ----------
    path : pathlib.Path
        Path to the file to inspect. Must refer to a regular file.
    sample_size : int, default=8192
        Number of bytes read from the start of the file for analysis.

    Returns
    -------
    bool
        ``True`` if the file appears to be binary, ``False`` otherwise.

    Raises
    ------
    ValueError
        If ``path`` does not refer to a regular file.
    OSError
        If the file cannot be read.
    """

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    with path.open("rb") as f:
        sample = f.read(sample_size)

    if b"\x00" in sample:
        return True

    text_bytes = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(32, 127)))
    non_text = sum(b not in text_bytes for b in sample)
    return non_text / max(len(sample), 1) > 0.30


def path_content(
    root: Path,
    *,
    follow_symlinks: bool = False,
    include: Callable[[Path], bool] = lambda p: True,
    skip_binary: bool = True,
    encoding: str = "utf-8",
    errors: Literal["raise", "skip"] = "raise",
) -> str:
    """
    Collect and concatenate the textual contents of files under a path.

    Starting from ``root``, this function walks the filesystem tree, applies
    structural filtering via ``include``, optionally skips binary files, and
    returns a single string containing the formatted contents of all selected
    files.

    Directory traversal follows ``pathlib.Path.walk`` semantics and supports
    optional symbolic link following. Directory pruning is performed in-place
    to avoid descending into excluded paths.

    Each file is rendered using ``file_to_text`` and concatenated with blank
    lines between blocks.

    Parameters
    ----------
    root : pathlib.Path
        Root path to process. May be a file or a directory.
    follow_symlinks : bool, default=False
        Whether to follow symbolic links during traversal.
    include : Callable[[pathlib.Path], bool], optional
        Predicate used to filter paths. If it returns ``False`` for a path,
        that path is ignored; directories are also pruned and not descended into.
    skip_binary : bool, default=True
        If ``True``, files detected as binary via ``is_binary_file`` are skipped.
    encoding : str, default="utf-8"
        Text encoding used when reading files.
    errors : {"raise", "skip"}, default="raise"
        Error handling strategy when reading or decoding a file:
        - ``"raise"`` propagates the exception,
        - ``"skip"`` silently ignores the file.

    Returns
    -------
    str
        A single string containing the concatenated formatted contents of all
        selected files.

    Raises
    ------
    ValueError
        If ``root`` is neither a file nor a directory.
    OSError
        If a filesystem operation fails and ``errors="raise"``.
    UnicodeDecodeError
        If decoding fails and ``errors="raise"``.
    """
    root = root.resolve()
    blocks: list[str] = []

    def should_follow(p: Path) -> bool:
        return follow_symlinks or not p.is_symlink()

    def safe_add_file(p: Path) -> None:
        if skip_binary and is_binary_file(p):
            return
        try:
            blocks.append(file_to_text(p, root=root, encoding=encoding))
        except (OSError, UnicodeDecodeError):
            if errors == "skip":
                return
            raise

    if root.is_file():
        if include(root) and should_follow(root):
            safe_add_file(root)
        return "\n\n".join(blocks)

    if not root.is_dir():
        raise ValueError(f"Not a file or directory: {root}")

    for dirpath, dirnames, filenames in root.walk(follow_symlinks=follow_symlinks):
        # Prune dirs in-place + stable sort
        kept = [
            name
            for name in dirnames
            if include(dirpath / name) and should_follow(dirpath / name)
        ]
        dirnames[:] = sorted(kept, key=str.casefold)

        for name in sorted(filenames, key=str.casefold):
            p = dirpath / name
            if not include(p) or not should_follow(p):
                continue
            safe_add_file(p)

    return "\n\n".join(blocks)
