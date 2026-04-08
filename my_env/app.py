# -*- coding: utf-8 -*-
"""
Root-level app.py for Hugging Face Spaces deployment.
This file imports and exposes the app from server/app.py
"""

import os
import sys

# Add current directory to path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Import the mounted FastAPI+Gradio app
from server.app import app

# The 'app' variable is what Hugging Face Spaces will look for
__all__ = ["app"]
