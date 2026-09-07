"""Smoke tests — plan task 0.5.

Asserts the package installs and imports, reports a version, and
registers the seven design-stage modules, each with a docstring
stating its purpose, inputs and outputs.
"""

import importlib

import openhull

STAGE_MODULES = [
    "main_dimensions",
    "hydrostatics",
    "linesplan",
    "resistance",
    "propeller",
    "stability",
    "drawing",
]


def test_package_imports_with_docstring():
    assert openhull.__doc__


def test_version_exists():
    assert isinstance(openhull.__version__, str)
    # installed package metadata resolves; the source-tree fallback
    # ("0.0.0.dev0") must not leak into a proper environment
    assert openhull.__version__ != "0.0.0.dev0"


def test_seven_stage_modules_registered():
    for name in STAGE_MODULES:
        module = importlib.import_module(f"openhull.{name}")
        assert module.__doc__, f"openhull.{name} lacks a docstring"
