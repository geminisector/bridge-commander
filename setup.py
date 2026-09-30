"""Build hook: put the shipped ``core`` flavor inside the wheel.

Player-facing mods live in the project-root ``mods/`` folder, which is not part
of the importable ``bridge`` package.  An installed wheel has no project root,
so the loader falls back to ``bridge/flavors/``; this copies the shipped default
(and the authoring schemas) into that location in the build tree.  The example
settings (``wc``, ``stk``, ``sw``) are deliberately not shipped.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterator

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent

#: Directories copied into ``bridge/flavors/`` in the wheel.
SHIPPED_DIRS = ("core", "schema")
#: Loose files copied into ``bridge/flavors/`` in the wheel.
SHIPPED_FILES = ("README.md",)


class build_py(_build_py):
    """Copy the packaged flavor tree after the normal build_py run."""

    def run(self) -> None:
        super().run()
        target = Path(self.build_lib) / "bridge" / "flavors"
        for name in SHIPPED_DIRS:
            source = ROOT / "mods" / name
            if source.is_dir():
                shutil.copytree(source, target / name, dirs_exist_ok=True)
        for name in SHIPPED_FILES:
            source = ROOT / "mods" / name
            if source.is_file():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target / name)

    def get_outputs(self, include_bytecode: bool = True) -> Iterator[str]:
        yield from super().get_outputs(include_bytecode=include_bytecode)
        target = Path(self.build_lib) / "bridge" / "flavors"
        if target.is_dir():
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    yield str(path)


setup(cmdclass={"build_py": build_py})
