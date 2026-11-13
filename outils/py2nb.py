"""Convertit un script au format « percent » (# %%) en notebook Jupyter, puis l'exécute.

Usage : python outils/py2nb.py source.py destination.ipynb

Les notebooks du dépôt sont produits ainsi : le résultat affiché dans chaque
cellule est donc toujours celui d'une exécution complète, du début à la fin.
"""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def convertir(source: Path) -> nbformat.NotebookNode:
    cellules, type_courant, tampon = [], None, []

    def vider():
        if type_courant is None:
            return
        texte = "\n".join(tampon).strip("\n")
        if not texte.strip():
            return
        if type_courant == "markdown":
            lignes = [l[2:] if l.startswith("# ") else l.lstrip("#") for l in texte.split("\n")]
            cellules.append(nbformat.v4.new_markdown_cell("\n".join(lignes)))
        else:
            cellules.append(nbformat.v4.new_code_cell(texte))

    for ligne in source.read_text(encoding="utf-8").split("\n"):
        if ligne.startswith("# %%"):
            vider()
            type_courant = "markdown" if "[markdown]" in ligne else "code"
            tampon = []
        else:
            tampon.append(ligne)
    vider()
    nb = nbformat.v4.new_notebook(cells=cellules)
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    return nb


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    nb = convertir(src)
    NotebookClient(nb, timeout=3600, kernel_name="python3",
                   resources={"metadata": {"path": str(dst.parent)}}).execute()
    for i, c in enumerate(nb.cells):
        c["id"] = f"cellule-{i:03d}"
    nbformat.write(nb, dst)
    print(f"{dst} : {len(nb.cells)} cellules exécutées")
