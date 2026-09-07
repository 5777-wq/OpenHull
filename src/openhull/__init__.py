"""OpenHull — agent-orchestrated parametric ship preliminary design.

From a task book (ship type, deadweight, service speed, trading range)
to principal dimensions, hydrostatics, a lines plan, performance
estimates, and drawing outputs — with every quantity validated against
published benchmark ships (see AGENTS.md for the binding conventions).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openhull")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
