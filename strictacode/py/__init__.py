from . import patch

patch.radon()
del patch

from .loader import PyLoder

__all__ = ["PyLoder"]
