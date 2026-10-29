# Chess Analyzer - Offline chess position analysis
# Copyright (C) 2026 Robert Morgan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see https://www.gnu.org/licenses/.

"""Shared locations for bundled resources and writable application data."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if os.name == 'nt':
    DATA_ROOT = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')) / 'ChessAnalyzer'
else:
    DATA_ROOT = Path.home() / '.local' / 'share' / 'ChessAnalyzer'
DATA_ROOT.mkdir(parents=True, exist_ok=True)
