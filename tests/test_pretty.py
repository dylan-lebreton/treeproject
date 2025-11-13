# tests/test_pretty.py
import sys
from pathlib import Path

import pytest

from treeproject import build_tree, draw_tree, build_and_draw_tree


def _make_file(p: Path, content: str = "x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _lines(s: str):
    return s.splitlines()


def test_draw_tree_basic_single_level(tmp_path: Path):
    # Root contains two dirs and two files
    (tmp_path / "bDir").mkdir()
    (tmp_path / "ADir").mkdir()
    _make_file(tmp_path / "z.txt")
    _make_file(tmp_path / "A.txt")

    node = build_tree(tmp_path)
    out = draw_tree(node)
    lines = _lines(out)

    # First line is the root node's name
    assert lines[0] == tmp_path.name

    # The rest must be: dirs first (case-insensitive), then files (case-insensitive)
    # RenderTree with ContStyle draws single-level children prefixed by ├── / └──
    assert lines[1:] == [
        "├── ADir",
        "├── bDir",
        "├── A.txt",
        "└── z.txt",
    ]


def test_draw_tree_nested_structure(tmp_path: Path):
    # project/
    #   src/
    #     a.py
    #   docs/
    #     readme.md
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    _make_file(tmp_path / "src/a.py")
    _make_file(tmp_path / "docs/readme.md")

    node = build_tree(tmp_path)
    out = draw_tree(node)
    lines = _lines(out)

    # Root
    assert lines[0] == tmp_path.name

    # The exact shape with ContStyle:
    # root
    # ├── docs
    # │   └── readme.md
    # └── src
    #     └── a.py
    assert lines[1:] == [
        "├── docs",
        "│   └── readme.md",
        "└── src",
        "    └── a.py",
    ]


def test_build_and_draw_tree_equivalence(tmp_path: Path):
    # Mixed content with items to exclude
    (tmp_path / "pkg/__pycache__").mkdir(parents=True)
    _make_file(tmp_path / "pkg/keep.py")
    _make_file(tmp_path / "pkg/__pycache__/drop.pyc")
    _make_file(tmp_path / "top.log")
    _make_file(tmp_path / "top.txt")

    exclude = ["__pycache__/", "*.log"]

    node = build_tree(tmp_path, exclude=exclude)
    s1 = draw_tree(node)
    s2 = build_and_draw_tree(tmp_path, exclude=exclude)

    assert isinstance(s2, str)
    assert s1 == s2
    # ensure excluded items do not appear
    assert "__pycache__" not in s2
    assert "top.log" not in s2
    # kept items
    assert "pkg" in s2 and "keep.py" in s2 and "top.txt" in s2


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink creation needs privileges on Windows")
def test_build_and_draw_tree_symlink_dir_flag(tmp_path: Path):
    # real/
    #   inside.txt
    # linkdir -> real (symlink)
    real = tmp_path / "real"
    real.mkdir()
    _make_file(real / "inside.txt")

    link = tmp_path / "linkdir"
    link.symlink_to(real, target_is_directory=True)

    # ---- Case 1: follow_symlinks = False
    s_no_follow = build_and_draw_tree(tmp_path, follow_symlinks=False)
    lines_no_follow = _lines(s_no_follow)

    # Expected shape:
    # root
    # ├── linkdir          (no children under linkdir)
    # └── real
    #     └── inside.txt
    assert lines_no_follow[0] == tmp_path.name
    assert lines_no_follow[1:] == [
        "├── linkdir",
        "└── real",
        "    └── inside.txt",
    ]

    # ---- Case 2: follow_symlinks = True
    s_follow = build_and_draw_tree(tmp_path, follow_symlinks=True)
    lines_follow = _lines(s_follow)

    # Expected shape:
    # root
    # ├── linkdir
    # │   └── inside.txt
    # └── real
    #     └── inside.txt
    assert lines_follow[0] == tmp_path.name
    assert lines_follow[1:] == [
        "├── linkdir",
        "│   └── inside.txt",
        "└── real",
        "    └── inside.txt",
    ]


def test_build_and_draw_tree_returns_string_and_does_not_print(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _make_file(tmp_path / "a.txt")
    out = build_and_draw_tree(tmp_path)
    # It should return a string
    assert isinstance(out, str)
    # And not print anything by itself
    captured = capsys.readouterr()
    assert captured.out == ""

    # If the user prints it, it should appear
    print(out)
    captured2 = capsys.readouterr()
    assert tmp_path.name in captured2.out
    assert "a.txt" in captured2.out
