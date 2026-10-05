"""The framework's command line: python claw.py <command>. It works on this source."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

from fwbuild.cli import main  # noqa: E402

sys.exit(main())
