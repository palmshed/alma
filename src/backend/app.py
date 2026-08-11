# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT
#
# This is the main entry point for the Gemini AI Search Flask application.
# It creates and runs the app using the factory pattern.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from palmshed_ai import create_app

# Load environment variables from .env file
load_dotenv()

app = create_app()


# This is for Vercel serverless deployment
app.debug = False

if __name__ == "__main__":
    app.run(port=8000)
