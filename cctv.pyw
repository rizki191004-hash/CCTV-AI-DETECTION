#!/usr/bin/env pythonw
"""
cctv.pyw — Windowless Desktop Launcher for CCTV AI Detection.
Double-click this file from File Explorer or Desktop to Start or Stop CCTV AI.
"""

import os
import sys

# Ensure root directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cctv import main

if __name__ == "__main__":
    main()

