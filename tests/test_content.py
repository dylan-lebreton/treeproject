# tests/test_content.py
import os
import stat
from pathlib import Path

import pytest
from treeproject import get_files_content


def _make_file(p: Path, content: str = "x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _extract_blocks(s: str):
    """
    Extract (header, body) blocks from the output.

    Each block begins with a line that starts with three double quotes followed
    immediately by the path, and ends when a line is exactly three double quotes.
    Returns a list of tuples (header_path, body_text).
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
                header = line[3:]  # strip the leading quotes
        else:
            if header is not None:
                body.append(line)

    if header is not None:
        blocks.append((header, "\n".join(body)))

    return blocks


def test_basic_inclusion_all_files(tmp_path: Path):
    _make_file(tmp_path / "a.txt", "Hello")
    _make_file(tmp_path / "b.py", "print('x')")
    _make_file(tmp_path / "c.md", "# Title")

    out = get_files_content(tmp_path)

    blocks = _extract_blocks(out)
    headers = [h for h, _ in blocks]

    expected = [
        f"{tmp_path.name}/a.txt",
        f"{tmp_path.name}/b.py",
        f"{tmp_path.name}/c.md",
    ]
    assert sorted(headers) == sorted(expected)

    d = {h: body for h, body in blocks}
    assert d[f"{tmp_path.name}/a.txt"] == "Hello"
    assert d[f"{tmp_path.name}/b.py"] == "print('x')"
    assert d[f"{tmp_path.name}/c.md"] == "# Title"


def test_exclusion_patterns(tmp_path: Path):
    _make_file(tmp_path / "keep.txt", "hi")
    _make_file(tmp_path / "drop.log", "should not appear")
    _make_file(tmp_path / "also_keep.py", "ok")

    out = get_files_content(tmp_path, exclude=["*.log"])

    blocks = _extract_blocks(out)
    headers = [h for h, _ in blocks]

    assert f"{tmp_path.name}/drop.log" not in headers
    assert f"{tmp_path.name}/keep.txt" in headers
    assert f"{tmp_path.name}/also_keep.py" in headers


def test_include_extensions(tmp_path: Path):
    _make_file(tmp_path / "a.txt", "hello")
    _make_file(tmp_path / "b.py", "print('x')")
    _make_file(tmp_path / "c.md", "# nope")

    out = get_files_content(tmp_path, include=[".txt", ".py"])

    blocks = _extract_blocks(out)
    headers = [h for h, _ in blocks]

    assert f"{tmp_path.name}/a.txt" in headers
    assert f"{tmp_path.name}/b.py" in headers
    assert f"{tmp_path.name}/c.md" not in headers


def test_nested_relative_paths(tmp_path: Path):
    (tmp_path / "src").mkdir()
    _make_file(tmp_path / "src/a.py", "x = 1")
    _make_file(tmp_path / "root.txt", "root-level")

    out = get_files_content(tmp_path)

    blocks = _extract_blocks(out)
    headers = [h for h, _ in blocks]

    assert f"{tmp_path.name}/root.txt" in headers
    assert f"{tmp_path.name}/src/a.py" in headers


def test_symlink_file_handling(tmp_path: Path):
    real = tmp_path / "real.txt"
    _make_file(real, "hello!")

    link = tmp_path / "link.txt"
    link.symlink_to(real)

    out = get_files_content(tmp_path)

    blocks = _extract_blocks(out)
    headers = [h for h, _ in blocks]

    assert f"{tmp_path.name}/real.txt" in headers
    assert f"{tmp_path.name}/link.txt" in headers

    d = {h: body for h, body in blocks}
    assert d[f"{tmp_path.name}/real.txt"] == "hello!"
    assert d[f"{tmp_path.name}/link.txt"] == "hello!"


@pytest.mark.skipif(os.name != "posix", reason="Permission bits test is POSIX-only")
def test_unreadable_file_behavior_ignore(tmp_path: Path):
    secret = tmp_path / "secret.txt"
    _make_file(secret, "hidden")

    # Make unreadable
    secret.chmod(0)
    try:
        out = get_files_content(tmp_path, ignore_file_type_error=True)
        blocks = _extract_blocks(out)
        headers = [h for h, _ in blocks]
        assert f"{tmp_path.name}/secret.txt" not in headers  # skipped
    finally:
        secret.chmod(stat.S_IRWXU)


@pytest.mark.skipif(os.name != "posix", reason="Permission bits test is POSIX-only")
def test_unreadable_file_behavior_error(tmp_path: Path):
    secret = tmp_path / "secret.txt"
    _make_file(secret, "hidden")

    secret.chmod(0)
    try:
        with pytest.raises(Exception):
            _ = get_files_content(tmp_path, ignore_file_type_error=False)
    finally:
        secret.chmod(stat.S_IRWXU)


def test_empty_directory_returns_empty_string(tmp_path: Path):
    out = get_files_content(tmp_path)
    assert out.strip() == ""
