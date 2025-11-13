from __future__ import annotations

from pathlib import Path

from anytree import Node
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

__all__ = ["build_tree"]


def build_tree(
        root: str | Path,
        *,
        follow_symlinks: bool = False,
        exclude: list[str] | None = None,
) -> Node:
    """
    Build an `anytree.Node` hierarchy representing the filesystem rooted at `root`.

    The tree closely reflects the underlying directory structure:
    - Each node corresponds to either a file or a directory.
    - File nodes are always leaves.
    - Directory nodes may or may not have children.
    - Symbolic links are represented as nodes, but symlinked directories are not
      traversed unless `follow_symlinks=True`.

    Exclusion rules:
        The `exclude` parameter accepts a list of gitignore-style patterns.
        Any file or directory matching any of the patterns is entirely excluded.
        For directories, exclusion prevents descending into that directory.

        Supported pattern syntax (via `pathspec`):
        - `*`, `?`, `[]` wildcards
        - `**` recursive wildcard
        - `pattern/` to match directories specifically
        - `/pattern` to match relative to the project root

    Parameters
    ----------
    root : str | Path
        The root directory to scan. If it is a file, a single-node tree is returned.
    follow_symlinks : bool, optional (default=False)
        If True, descend into symlinked directories. By default, symlinked directories
        are not followed to avoid cycles.
    exclude : list[str] | None, optional
        List of gitignore-style patterns to exclude. Defaults to no exclusion.

    Returns
    -------
    Node
        The root node of the constructed tree. Each node carries:
        - `fs_path`: `pathlib.Path` (absolute, resolved)
        - `is_dir`: `bool`
        - `is_symlink`: `bool`

    Raises
    ------
    FileNotFoundError
        If `root` does not exist.

    Notes
    -----
    - The function never raises errors for unreadable directories; they are skipped.
    - `anytree.Node.path` (built-in) returns a tuple of nodes along the tree path.
      The filesystem path is stored under `node.fs_path` to avoid name clashes.
    """
    root_path = Path(root).expanduser().resolve(strict=False)
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    spec = PathSpec.from_lines(GitWildMatchPattern, exclude or [])

    def _rel_posix(p: Path) -> str:
        try:
            rel = p.relative_to(root_path).as_posix()
        except ValueError:
            rel = p.as_posix()
        if p.is_dir():
            rel = rel.rstrip("/") + "/"
        return rel

    def _is_excluded(p: Path) -> bool:
        return spec.match_file(_rel_posix(p))

    def _iter_children(dir_path: Path) -> list[Path]:
        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            return []
        entries.sort(key=lambda e: (not e.is_dir(), e.name.casefold()))
        return [e for e in entries if not _is_excluded(e)]

    def _build(path: Path, parent: Node | None) -> Node:
        is_dir = path.is_dir()
        is_link = path.is_symlink()

        node = Node(
            path.name,
            parent=parent,
            fs_path=path,  # <-- FS path lives here
            is_dir=is_dir,
            is_symlink=is_link,
        )

        if is_dir:
            if is_link and not follow_symlinks:
                return node
            for child in _iter_children(path):
                _build(child, parent=node)

        return node

    if root_path.is_file():
        return Node(
            root_path.name,
            fs_path=root_path,
            is_dir=False,
            is_symlink=root_path.is_symlink(),
        )

    return _build(root_path, parent=None)
