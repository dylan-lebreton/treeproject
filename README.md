# treeproject

**treeproject** is a lightweight Python library that scans a directory and builds an **anytree-based** hierarchy of its filesystem structure. It provides utilities for:

- Building a tree (`build_tree`)
- Rendering the tree as readable text (`draw_tree`, `build_and_draw_tree`)
- Extracting file contents (`get_files_content`, `get_files_content_from_node`)
- Combining the tree + selected file contents (`build_tree_and_contents`)

It is useful for documentation, tooling, debugging, or generating compact context bundles for LLMs. It supports `.gitignore`-style exclusion patterns via `pathspec`.

---

## Installation

```bash
pip install treeproject
```

Requires **Python 3.10+**. Dependencies: `anytree` and `pathspec`.

---

## Quick Examples

### 1) Render a directory tree

```python
from treeproject import build_and_draw_tree

print(build_and_draw_tree(
    "./my_project",
    exclude=["__pycache__/", ".git/", "*.log"]
))
```

Example output:

```
my_project
├── docs
│   └── readme.md
└── src
    ├── app.py
    └── utils.py
```

---

### 2) Extract file contents (filtered)

```python
from treeproject import get_files_content

bundle = get_files_content(
    "./my_project",
    exclude=[".venv/", "build/", "*.pyc"],
    include=[".py", ".md"],
    ignore_file_type_error=True
)

print(bundle)
```

Output format (example):

```
"""my_project/src/app.py
print("hello")
"""

"""my_project/docs/readme.md
# My Project
"""
```

---

### 3) Combine tree + file contents

```python
from treeproject import build_tree_and_contents

summary = build_tree_and_contents(
    "./my_project",
    tree_exclude=[".git/", "__pycache__/"],
    content_include=[".py", ".md"],
    content_ignore_file_type_error=True,
)

print(summary)
```

---

## API Overview

### `build_tree(root, *, follow_symlinks=False, exclude=None) -> anytree.Node`
Builds an anytree `Node` hierarchy from a filesystem path.

Node attributes:
- `fs_path: pathlib.Path`
- `is_dir: bool`
- `is_symlink: bool`

Supports gitignore-style exclusions:
- `*`, `?`, `[]`, `**`
- `pattern/` matches directories
- `/pattern` is root-relative

---

### `draw_tree(node) -> str`
Renders an anytree node into a human-readable ASCII/UTF-8 tree using Unicode connectors.

---

### `build_and_draw_tree(root, *, follow_symlinks=False, exclude=None) -> str`
Convenience wrapper: builds a tree, then renders it.

---

### `get_files_content(root, *, exclude=None, include=None, ignore_file_type_error=False, encoding="utf-8") -> str`
Returns concatenated file contents (sorted by relative path).  
Output is a list of blocks:

```
"""root/relative/path
<file content>
"""
```

---

### `get_files_content_from_node(node, *, exclude=None, include=None, ignore_file_type_error=False, encoding="utf-8") -> str`
Same as above, but using an already-built tree.

---

### `build_tree_and_contents(...) -> str`
Builds the tree once, prints:

1. The rendered tree  
2. A blank line  
3. File content blocks, filtered independently  

---

## Exclusion Patterns

All exclusions use `pathspec` with gitignore-style syntax.

Examples:

- `".*/"` → all dot-directories  
- `"__pycache__/"`  
- `"*.pyc"`  
- `"build/"`  
- `"*.log"`  
- `"/README.md"` → match root-relative file  

---

## Behavior

- Directories appear before files, sorted case-insensitively.
- Symbolic links:
  - directory symlinks followed only if `follow_symlinks=True`
  - file symlinks treated as leaf nodes
- Unreadable directories are skipped safely
- Non-text files are skipped when `ignore_file_type_error=True`
- UTF-8 encoding by default

---

## Development

```bash
git clone https://github.com/dylan-lebreton/treeproject
cd treeproject
poetry install
pytest -q
```

---

## Roadmap

- Tree export to JSON/YAML
- Alternate rendering styles
- Advanced filtering (glob sets, regexes, ignore vs allow priority rules)
- CLI interface

---

## License

MIT License  
Copyright (c)  
Dylan Lebreton  
