# treeproject

**treeproject** is a lightweight Python library providing simple, deterministic
utilities to:

- render a directory structure as a readable Unicode tree,
- extract and concatenate file contents into a single structured text bundle.

It is designed for documentation, debugging, tooling, and building compact
filesystem context bundles (for example, for LLM prompts).

The API is intentionally minimal, dependency-free, and based on `pathlib.Path`.

---

## Installation

```bash
pip install treeproject
```

Requires **Python 3.10+**.

---

## Features

- Unicode tree rendering (similar to the Unix `tree` command)
- Deterministic traversal (directories first, case-insensitive sorting)
- Strict pruning-based filtering
- Optional symbolic link traversal
- Text content extraction with stable formatting
- Binary file detection and skipping
- Configurable encoding and error handling
- Zero runtime dependencies

---

## Quick Start

### Print a directory tree

```python
from pathlib import Path
from treeproject import print_tree

print_tree(Path("./my_project"))
```

Example output:

```
my_project
├── README.md
├── pyproject.toml
└── src
    ├── __init__.py
    └── app.py
```

---

### Extract file contents

```python
from pathlib import Path
from treeproject import path_content

bundle = path_content(Path("./my_project"))
print(bundle)
```

Example output format:

```
===== FILE: README.md =====
# My Project
...
===== END FILE =====

===== FILE: src/app.py =====
print("hello")
===== END FILE =====
```

---

## Filtering and Pruning

Filtering is controlled via an `include(Path) -> bool` predicate.

If the predicate returns `False` for a directory, the directory is **pruned**
and none of its descendants are visited.

```python
IGNORE = {".git", "__pycache__", ".pytest_cache"}

def include(p: Path) -> bool:
    return p.name not in IGNORE

print_tree(Path("."), include=include)
```

The same predicate can be reused for content extraction.

---

## API Reference

### `print_tree(root, *, follow_symlinks=False, include=lambda p: True) -> None`

Print a Unicode directory tree to standard output.

- Directories are listed before files
- Sorting is case-insensitive
- Excluded directories are fully pruned

---

### `path_content(root, *, follow_symlinks=False, include=lambda p: True,
skip_binary=True, encoding="utf-8", errors="raise") -> str`

Walk a filesystem path and return a single string containing the formatted
contents of all selected files.

- Files are processed in deterministic order
- Binary files can be skipped automatically
- Errors can be raised or ignored per file

---

## Design Notes

- Uses `pathlib.Path.walk` for traversal
- No global state
- No side effects except explicit printing in `print_tree`
- Suitable for programmatic use and automation

---

## Development

```bash
git clone https://github.com/dylan-lebreton/treeproject
cd treeproject
poetry install
pytest
```

---

## License

MIT License

Copyright (c) 2025 Dylan Lebreton
