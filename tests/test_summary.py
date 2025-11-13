# tests/test_summary.py
import os
import sys
import stat
from pathlib import Path

import pytest

from treeproject import build_tree_and_contents


def _make_file(p: Path, content: str = "x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _tree_part(s: str) -> str:
    """Return only the part before the first content block."""
    parts = s.split('"""', 1)
    return parts[0].rstrip()


def _extract_blocks(s: str):
    """
    Extract (header, body) blocks from the output. Same logic as in test_content.
    """
    blocks = []
    header = None
    body = []

    for line in s.splitlines():
        if line.startswith('"""'):
            if line == '"""':
                if header is not None:
                    blocks.append((header, "\n".join(body)))
                    header, body = None, []
            else:
                if header is not None:
                    blocks.append((header, "\n".join(body)))
                    body = []
                header = line[3:]
        else:
            if header is not None:
                body.append(line)

    if header is not None:
        blocks.append((header, "\n".join(body)))

    return blocks


def test_tree_and_contents_basic(tmp_path: Path):
    _make_file(tmp_path / "a.txt", "AA")
    _make_file(tmp_path / "b.md", "BB")

    result = build_tree_and_contents(
        tmp_path,
        tree_exclude=[],
        tree_follow_symlinks=False,
        content_include=[".txt"],
    )

    tree_part = _tree_part(result).splitlines()
    assert tree_part[0] == tmp_path.name
    assert "a.txt" in result
    assert "b.md" in result

    blocks = _extract_blocks(result)
    headers = [h for h, _ in blocks]

    assert f"{tmp_path.name}/a.txt" in headers
    assert f"{tmp_path.name}/b.md" not in headers


def test_independent_filters_tree_vs_content(tmp_path: Path):
    _make_file(tmp_path / "a.txt", "AAA")
    _make_file(tmp_path / "b.log", "BBB")

    result = build_tree_and_contents(
        tmp_path,
        tree_exclude=["*.log"],           # log appears in tree? → NO
        content_include=[".txt"],         # included content? only txt
    )

    tree_part = _tree_part(result)
    assert "b.log" not in tree_part

    blocks = _extract_blocks(result)
    headers = [h for h, _ in blocks]
    assert f"{tmp_path.name}/a.txt" in headers
    assert f"{tmp_path.name}/b.log" not in headers


def test_no_matching_content_returns_only_tree(tmp_path: Path):
    _make_file(tmp_path / "a.txt", "AAA")

    result = build_tree_and_contents(
        tmp_path,
        content_include=[".unknown"],
    )

    blocks = _extract_blocks(result)
    assert blocks == []


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink creation needs privileges on Windows")
def test_symlink_effect_when_follow_false_true(tmp_path: Path):
    real = tmp_path / "real"
    real.mkdir()
    _make_file(real / "inside.txt", "IN")
    link = tmp_path / "linkdir"
    link.symlink_to(real, target_is_directory=True)

    # ---- Case 1: follow_symlinks = False
    res_no_follow = build_tree_and_contents(
        tmp_path,
        tree_follow_symlinks=False,
        content_include=[".txt"],
        content_ignore_file_type_error=True,
    )

    tree_no_follow = _tree_part(res_no_follow).splitlines()
    assert tree_no_follow[0] == tmp_path.name
    assert "linkdir" in tree_no_follow[1]

    # real is scanned normally → inside.txt exists
    blocks_no_follow = _extract_blocks(res_no_follow)
    headers_no_follow = [h for h, _ in blocks_no_follow]

    assert f"{tmp_path.name}/real/inside.txt" in headers_no_follow
    # linkdir is not descended → no inside.txt under linkdir
    assert f"{tmp_path.name}/linkdir/inside.txt" not in headers_no_follow

    # ---- Case 2: follow_symlinks = True
    res_follow = build_tree_and_contents(
        tmp_path,
        tree_follow_symlinks=True,
        content_include=[".txt"],
    )

    blocks_follow = _extract_blocks(res_follow)
    headers_follow = [h for h, _ in blocks_follow]

    assert f"{tmp_path.name}/real/inside.txt" in headers_follow
    assert f"{tmp_path.name}/linkdir/inside.txt" in headers_follow


@pytest.mark.skipif(os.name != "posix", reason="Permission bits test is POSIX-only")
def test_unreadable_file_is_skipped_when_flag_true(tmp_path: Path):
    secret = tmp_path / "secret.txt"
    _make_file(secret, "HIDDEN")

    secret.chmod(0)
    try:
        result = build_tree_and_contents(
            tmp_path,
            content_ignore_file_type_error=True,
        )
        blocks = _extract_blocks(result)
        headers = [h for h, _ in blocks]
        assert f"{tmp_path.name}/secret.txt" not in headers
    finally:
        secret.chmod(stat.S_IRWXU)
