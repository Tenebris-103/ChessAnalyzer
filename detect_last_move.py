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

import chess
import cv2
import numpy as np
from chess_paths import DATA_ROOT

def detect_turn():
    board_path = DATA_ROOT / "board.png"
    position_path = DATA_ROOT / "recognized_position.txt"
    turn_path = DATA_ROOT / "detected_turn.txt"
    turn_path.unlink(missing_ok=True)
    image = cv2.imread(str(board_path))
    if image is None:
        raise FileNotFoundError("board.png was not found.")
    if not position_path.exists():
        raise FileNotFoundError("recognized_position.txt was not found.")
    image = cv2.resize(image, (800, 800))
    square_colors = {}
    for row in range(8):
        for col in range(8):
            square = image[row * 100:(row + 1) * 100,
                           col * 100:(col + 1) * 100]
            samples = np.array([
                square[5, 5], square[5, 94], square[94, 5], square[94, 94]
            ], dtype=np.float32)
            name = f"{chr(ord('a') + col)}{8 - row}"
            square_colors[name] = {
                "color": np.median(samples, axis=0),
                "parity": (row + col) % 2
            }
    normal_colors = {}
    for parity in (0, 1):
        colors = [data["color"] for data in square_colors.values()
                  if data["parity"] == parity]
        normal_colors[parity] = np.median(np.array(colors), axis=0)
    results = []
    for name, data in square_colors.items():
        normal = normal_colors[data["parity"]]
        distance = float(np.linalg.norm(data["color"] - normal))
        results.append((name, distance))
    results.sort(key=lambda item: item[1], reverse=True)
    placement = position_path.read_text(encoding="utf-8").strip()
    board = chess.Board(f"{placement} w - - 0 1")
    white_king = board.king(chess.WHITE)
    black_king = board.king(chess.BLACK)
    white_in_check = (white_king is not None and
                      board.is_attacked_by(chess.BLACK, white_king))
    black_in_check = (black_king is not None and
                      board.is_attacked_by(chess.WHITE, black_king))
    if white_in_check != black_in_check:
        next_turn = "w" if white_in_check else "b"
        turn_path.write_text(next_turn, encoding="utf-8")
        return next_turn
    if white_in_check and black_in_check:
        return None
    if (len(results) < 3 or results[1][1] < 25 or
            results[1][1] < results[2][1] * 1.5):
        return None
    square_a = chess.parse_square(results[0][0])
    square_b = chess.parse_square(results[1][0])
    piece_a = board.piece_at(square_a)
    piece_b = board.piece_at(square_b)
    if piece_a is None and piece_b is not None:
        last_piece = piece_b
    elif piece_b is None and piece_a is not None:
        last_piece = piece_a
    else:
        return None
    next_turn = "b" if last_piece.color else "w"
    turn_path.write_text(next_turn, encoding="utf-8")
    return next_turn

if __name__ == "__main__":
    print("Detected turn:", detect_turn() or "Unknown")
