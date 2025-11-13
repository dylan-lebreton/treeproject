import os
import stat
import sys
from pathlib import Path

import pytest
from anytree import PreOrderIter

from treeproject import build_tree


def _collect_paths(node, root: Path):
    """
    Collect relative POSIX paths from the built tree (including directories).
    Returns a set of strings.
    """
    rels = set()
    for n in PreOrderIter(node):
        p = getattr(n, "fs_path", None)
        assert p is not None, "each node must carry a `path` attribute"
        rels.add("" if p == root else p.relative_to(root).as_posix())
    return rels


def _make_file(p: Path, content: str = "x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_root_is_a_file(tmp_path: Path):
    f = tmp_path / "single.txt"
    _make_file(f, "hello")

    root = build_tree(f)
    assert root.name == "single.txt"
    assert getattr(root, "is_dir") is False
    assert getattr(root, "is_symlink") is False
    # A single-node tree
    assert len(list(PreOrderIter(root))) == 1


def test_basic_directory_tree(tmp_path: Path):
    # project/
    #   src/
    #     a.py
    #     b.txt
    #   docs/
    #     readme.md
    #   .hidden/
    #   top.txt
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".hidden").mkdir()
    _make_file(tmp_path / "src/a.py")
    _make_file(tmp_path / "src/b.txt")
    _make_file(tmp_path / "docs/readme.md")
    _make_file(tmp_path / "top.txt")

    node = build_tree(tmp_path)
    rels = _collect_paths(node, tmp_path)

    # Presence
    assert "" in rels  # root
    assert "src" in rels and "docs" in rels and ".hidden" in rels
    assert "src/a.py" in rels and "src/b.txt" in rels
    assert "docs/readme.md" in rels
    assert "top.txt" in rels

    # Node attributes spot checks
    # Find "src" node
    src = next(n for n in PreOrderIter(node) if getattr(n, "fs_path") == (tmp_path / "src"))
    assert src.is_dir is True
    # Find a.py node
    apy = next(n for n in PreOrderIter(node) if getattr(n, "fs_path") == (tmp_path / "src/a.py"))
    assert apy.is_dir is False


def test_exclude_patterns_gitignore_like(tmp_path: Path):
    # Build layout including typical junk
    for d in [".git", ".venv", "build", "__pycache__", "pkg/data"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    for f in [
        ".git/config",
        ".venv/pyvenv.cfg",
        "build/artifact.bin",
        "__pycache__/x.cpython-312.pyc",
        "pkg/data/keep.txt",
        "pkg/skipme.pyc",
        "top.log",
        "top.py",
    ]:
        _make_file(tmp_path / f)

    # Exclude hidden dot-dirs, bytecode, build dir, and *.log anywhere
    patterns = [".*/", "__pycache__/", "*.pyc", "build/", "*.log"]

    node = build_tree(tmp_path, exclude=patterns)
    rels = _collect_paths(node, tmp_path)

    # Kept
    assert "pkg" in rels
    assert "pkg/data" in rels
    assert "pkg/data/keep.txt" in rels
    assert "top.py" in rels

    # Excluded
    assert ".git" not in rels
    assert ".venv" not in rels
    assert "__pycache__" not in rels
    assert "build" not in rels
    assert "pkg/skipme.pyc" not in rels
    assert "top.log" not in rels


def test_exclude_root_relative_pattern(tmp_path: Path):
    # Leading slash should match from the provided root
    _make_file(tmp_path / "keep.txt")
    _make_file(tmp_path / "drop.txt")

    node = build_tree(tmp_path, exclude=["/drop.txt"])
    rels = _collect_paths(node, tmp_path)
    assert "keep.txt" in rels
    assert "drop.txt" not in rels


def test_directory_exclusion_blocks_descent(tmp_path: Path):
    # If a directory is excluded with trailing slash, its children must not appear
    (tmp_path / "logs/day1").mkdir(parents=True)
    (tmp_path / "logs/day2").mkdir(parents=True)
    _make_file(tmp_path / "logs/day1/events.jsonl")
    _make_file(tmp_path / "logs/day2/events.jsonl")

    node = build_tree(tmp_path, exclude=["logs/"])
    rels = _collect_paths(node, tmp_path)
    assert "logs" not in rels
    assert "logs/day1" not in rels
    assert "logs/day1/events.jsonl" not in rels


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink creation needs privileges on Windows")
def test_symlink_directory_traversal_flag(tmp_path: Path):
    # Create a real dir and a symlink to it
    real = tmp_path / "real"
    real.mkdir()
    _make_file(real / "inside.txt")

    link = tmp_path / "linkdir"
    link.symlink_to(real, target_is_directory=True)

    # Default: follow_symlinks=False → node exists, but no children traversed
    node = build_tree(tmp_path, follow_symlinks=False)
    rels = _collect_paths(node, tmp_path)
    assert "linkdir" in rels
    assert "linkdir/inside.txt" not in rels

    # follow_symlinks=True → children under linkdir appear
    node2 = build_tree(tmp_path, follow_symlinks=True)
    rels2 = _collect_paths(node2, tmp_path)
    assert "linkdir" in rels2
    assert "linkdir/inside.txt" in rels2

    # Check is_symlink attribute on linkdir
    link_node = next(n for n in PreOrderIter(node2) if getattr(n, "fs_path") == link)
    assert link_node.is_symlink is True
    assert link_node.is_dir is True  # symlink to dir is treated as dir


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink creation needs privileges on Windows")
def test_symlink_to_file_is_leaf(tmp_path: Path):
    real = tmp_path / "data.txt"
    _make_file(real, "data")
    s = tmp_path / "data_link.txt"
    s.symlink_to(real)

    node = build_tree(tmp_path)
    # symlink to a file should be a file-like node (leaf)
    link_node = next(n for n in PreOrderIter(node) if getattr(n, "fs_path") == s)
    assert link_node.is_dir is False
    assert link_node.is_symlink is True


@pytest.mark.skipif(not os.name == "posix", reason="Permission bits test is POSIX-only")
def test_unreadable_directory_is_skipped_safely(tmp_path: Path):
    secret = tmp_path / "secret"
    secret.mkdir()
    _make_file(secret / "hidden.txt")

    # remove read/execute so os.listdir/iterdir raises PermissionError
    secret.chmod(0)
    try:
        node = build_tree(tmp_path)
        rels = _collect_paths(node, tmp_path)
        # directory exists as a node, but children couldn't be listed
        assert "secret" in rels
        assert "secret/hidden.txt" not in rels
    finally:
        # restore perms to avoid cleanup issues on some systems
        secret.chmod(stat.S_IRWXU)


def test_sorting_is_dirs_first_then_files_case_insensitive(tmp_path: Path):
    # Build a mix of names with varying case
    (tmp_path / "bDir").mkdir()
    (tmp_path / "ADir").mkdir()
    _make_file(tmp_path / "z.txt")
    _make_file(tmp_path / "A.txt")

    node = build_tree(tmp_path)

    # Immediate children of root (ordering preserved as created in sorted order)
    root_children = list(node.children)
    names = [c.name for c in root_children]

    # Directories first (alphabetical case-insensitive), then files (alphabetical case-insensitive)
    assert names == ["ADir", "bDir", "A.txt", "z.txt"]


def test_excluding_everything_returns_only_root_node(tmp_path: Path):
    (tmp_path / "dir").mkdir()
    _make_file(tmp_path / "dir/file.txt")
    _make_file(tmp_path / "top.txt")

    node = build_tree(tmp_path, exclude=["**"])
    # Only root should remain (we still return a root node representing the directory)
    nodes = list(PreOrderIter(node))
    assert len(nodes) == 1
    assert nodes[0].fs_path == tmp_path
    assert nodes[0].is_dir is True
