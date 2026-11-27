"""`python -m os_optics_lens` runs the command-line interface (same as the `os-optics-lens` script)."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
