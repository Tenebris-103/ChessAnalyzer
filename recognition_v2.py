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

import cv2
import numpy as np
from chess_paths import ROOT, DATA_ROOT

SQUARES = ROOT / "assets" / "squares"
BOARD = DATA_ROOT / "board.png"

EXAMPLES = {
    "R": ["a1", "h1"], "N": ["b1", "g1"], "B": ["c1", "f1"],
    "Q": ["d1"], "K": ["e1"], "P": ["a2", "b2"],
    "r": ["a8", "h8"], "n": ["b8", "g8"], "b": ["c8", "f8"],
    "q": ["d8"], "k": ["e8"], "p": ["a7", "b7"]
}

def silhouette(image):
    image = cv2.resize(image, (100, 100))
    background = np.median(np.array([
        image[5, 5], image[5, 94], image[94, 5], image[94, 94]
    ], dtype=np.float32), axis=0)
    distance = np.linalg.norm(image.astype(np.float32) - background, axis=2)
    mask = (distance > 35).astype(np.uint8) * 255
    mask[:15, :] = 0
    mask[85:, :] = 0
    mask[:, :15] = 0
    mask[:, 85:] = 0
    return mask

templates = []
for piece, squares in EXAMPLES.items():
    for square in squares:
        image = cv2.imread(str(SQUARES / f"{square}.png"))
        if image is None:
            raise FileNotFoundError(square)
        templates.append((piece, silhouette(image)))

def recognize(image):
    target = silhouette(image)
    if np.mean(target > 0) < 0.08:
        return "."
    best_piece = "?"
    best_score = float("inf")
    for piece, template in templates:
        score = np.mean(cv2.absdiff(target, template))
        if score < best_score:
            best_score = score
            best_piece = piece
    image = cv2.resize(image, (100, 100))
    corners = np.array([
        image[5, 5], image[5, 94], image[94, 5], image[94, 94]
    ], dtype=np.float32)
    background = np.median(corners, axis=0)
    distance = np.linalg.norm(image.astype(np.float32) - background, axis=2)
    region = image[25:75, 25:75]
    mask = distance[25:75, 25:75] > 35
    pixels = region[mask]
    if len(pixels) == 0:
        return "?"
    gray = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    piece_type = best_piece.upper()
    return piece_type if brightness > 125 else piece_type.lower()

def generate_fen(rows):
    fen_rows = []
    for row in rows:
        result = ""
        empty = 0
        for piece in row:
            if piece == ".":
                empty += 1
            else:
                if empty:
                    result += str(empty)
                    empty = 0
                result += piece
        if empty:
            result += str(empty)
        fen_rows.append(result)
    return "/".join(fen_rows)

def recognize_board():
    board = cv2.imread(str(BOARD))
    if board is None:
        raise FileNotFoundError(BOARD)
    board = cv2.resize(board, (800, 800))
    rows = []
    for row in range(8):
        pieces = []
        for col in range(8):
            square = board[row * 100:(row + 1) * 100,
                           col * 100:(col + 1) * 100]
            pieces.append(recognize(square))
        rows.append(pieces)
    placement = generate_fen(rows)
    (DATA_ROOT / "recognized_position.txt").write_text(placement, encoding="utf-8")
    return placement

if __name__ == "__main__":
    print("Recognized FEN:", recognize_board())
