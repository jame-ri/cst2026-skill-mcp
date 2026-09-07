"""Compatibility entry point; implementation lives in cst_api."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cst_api.worker import main

if __name__ == "__main__":
    main()
