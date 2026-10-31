"""One-click launcher for xray-bench Modern GUI."""
import os
import sys
from pathlib import Path

program_dir = Path(__file__).resolve().parent
os.chdir(program_dir)

if str(program_dir) not in sys.path:
    sys.path.insert(0, str(program_dir))

from src.gui.app import main

if __name__ == "__main__":
    main()
