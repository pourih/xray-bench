"""One-click launcher for xray-bench Modern GUI."""
import os
import sys
from pathlib import Path

# Change working directory to 'program' directory so all relative paths resolve seamlessly
root_dir = Path(__file__).resolve().parent
program_dir = root_dir / "program"
os.chdir(program_dir)

if str(program_dir) not in sys.path:
    sys.path.insert(0, str(program_dir))

from src.gui.app import main

if __name__ == "__main__":
    main()
