"""Convert a script in "percent" format (# %%) into a Jupyter notebook, then execute it.

Usage: python tools/py2nb.py source.py destination.ipynb

The notebooks of the repository are produced this way: the output shown in each cell
always comes from one complete run, from top to bottom.
"""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def convert(source: Path) -> nbformat.NotebookNode:
    cells, current, buffer = [], None, []

    def flush():
        if current is None:
            return
        text = "\n".join(buffer).strip("\n")
        if not text.strip():
            return
        if current == "markdown":
            lines = [l[2:] if l.startswith("# ") else l.lstrip("#") for l in text.split("\n")]
            cells.append(nbformat.v4.new_markdown_cell("\n".join(lines)))
        else:
            cells.append(nbformat.v4.new_code_cell(text))

    for line in source.read_text(encoding="utf-8").split("\n"):
        if line.startswith("# %%"):
            flush()
            current = "markdown" if "[markdown]" in line else "code"
            buffer = []
        else:
            buffer.append(line)
    flush()
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    return nb


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    nb = convert(src)
    NotebookClient(nb, timeout=3600, kernel_name="python3",
                   resources={"metadata": {"path": str(dst.parent)}}).execute()
    for i, c in enumerate(nb.cells):
        c["id"] = f"cell-{i:03d}"
        if c.cell_type == "code":      # drop technical logs (stderr) from the outputs
            c["outputs"] = [o for o in c["outputs"]
                            if not (o.get("output_type") == "stream" and o.get("name") == "stderr")]
    nbformat.write(nb, dst)
    print(f"{dst}: {len(nb.cells)} cells executed")
