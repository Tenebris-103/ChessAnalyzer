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

import sys
import json
import math
import os
import time
import subprocess
from pathlib import Path
import chess
import chess.svg
import chess.engine
import mss
import cv2
from detect_last_move import detect_turn
from recognition_v2 import recognize_board
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
)

from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QFileDialog,
    QMessageBox,
    QGridLayout,
    QCheckBox,
)

from chess_paths import ROOT, DATA_ROOT
LOG_PATH = DATA_ROOT / "ChessAnalyzer_timing.log"

def timing_log(message):
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")
    except OSError:
        pass



class ChessAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.best_arrow = None
        self.show_move_arrow = False
        self.engine = None
        self.setWindowTitle("Chess Analyzer")
        self.resize(1230, 810)
        self.setMinimumSize(1030, 720)

        self.setup_ui()

    def setup_ui(self):
        """Chess-focused layout; analysis and screenshot logic are unchanged."""
        self.setStyleSheet("""
            QMainWindow, QWidget#root { background: #0b1220; }
            QWidget { color: #edf2fa; font: 13px 'Segoe UI'; }
            QLabel { background: transparent; }
            QFrame#panel { background: #172235; border: 1px solid #27364c;
                           border-radius: 16px; }
            QFrame#moveCard { background: #101c2c; border: 1px solid #35577c;
                              border-radius: 12px; }
            QLabel#heading { font-size: 27px; font-weight: 750; }
            QLabel#section { font-size: 16px; font-weight: 700; }
            QLabel#muted { color: #9aacc3; font-size: 12px; }
            QLabel#evaluation { color: #86efac; font-size: 43px; font-weight: 750; }
            QLabel#moveTitle { color: #f8fafc; font-size: 21px; font-weight: 750; }
            QPushButton { background: #25364f; border: 1px solid #344963;
                          border-radius: 9px; padding: 11px 13px;
                          font-weight: 650; }
            QPushButton:hover { background: #344a68; }
            QPushButton:pressed { background: #1b2a3f; }
            QPushButton#primary { background: #2563eb; border: 1px solid #3673f1; }
            QPushButton#primary:hover { background: #3978f5; }
            QCheckBox { color: #b9c8da; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
        """)

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(24, 20, 24, 22)
        main.setSpacing(16)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.setSpacing(3)
        title = QLabel("Chess Analyzer")
        title.setObjectName("heading")
        brand.addWidget(title)
        subtitle = QLabel("Saved-position review  •  Powered by Stockfish")
        subtitle.setObjectName("muted")
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        main.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)
        main.addLayout(content, 1)

        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left = QVBoxLayout(left_panel)
        left.setContentsMargins(20, 18, 20, 18)
        left.setSpacing(13)
        board_header = QHBoxLayout()
        board_title = QLabel("BOARD PREVIEW")
        board_title.setObjectName("section")
        board_header.addWidget(board_title)
        board_header.addStretch()
        self.arrow_toggle = QCheckBox("Show arrow")
        self.arrow_toggle.setChecked(self.show_move_arrow)
        self.arrow_toggle.toggled.connect(self.toggle_move_arrow)
        board_header.addWidget(self.arrow_toggle)
        left.addLayout(board_header)

        self.board_widget = QWidget()
        self.board_layout = QGridLayout(self.board_widget)
        self.board_layout.setSpacing(0)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.draw_board()
        left.addWidget(self.board_widget, 1, Qt.AlignCenter)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.select_board_button = QPushButton("Select Board")
        self.select_board_button.clicked.connect(self.select_board)
        tools.addWidget(self.select_board_button)
        self.load_button = QPushButton("Load Screenshot")
        self.load_button.clicked.connect(self.load_screenshot)
        tools.addWidget(self.load_button)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_position)
        tools.addWidget(self.refresh_button)
        left.addLayout(tools)
        content.addWidget(left_panel, 6)

        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right = QVBoxLayout(right_panel)
        right.setContentsMargins(22, 20, 22, 20)
        right.setSpacing(13)
        analysis_title = QLabel("ENGINE ANALYSIS")
        analysis_title.setObjectName("section")
        right.addWidget(analysis_title)
        self.engine_status = QLabel("Stockfish · Not analyzed")
        self.engine_status.setObjectName("muted")
        right.addWidget(self.engine_status)
        self.evaluation = QLabel("—")
        self.evaluation.setObjectName("evaluation")
        right.addWidget(self.evaluation)
        self.best_move = QLabel("Suggested move: —")
        self.best_move.setStyleSheet("font-size: 15px; font-weight: 650;")
        right.addWidget(self.best_move)

        move_card = QFrame()
        move_card.setObjectName("moveCard")
        move_card_layout = QVBoxLayout(move_card)
        move_card_layout.setContentsMargins(15, 13, 15, 13)
        move_card_layout.setSpacing(7)
        move_label = QLabel("RECOMMENDED MOVE")
        move_label.setObjectName("muted")
        move_card_layout.addWidget(move_label)
        self.move_instruction = QLabel("Select a saved position to analyze")
        self.move_instruction.setObjectName("moveTitle")
        self.move_instruction.setWordWrap(True)
        move_card_layout.addWidget(self.move_instruction)
        self.promotion_notice = QLabel("")
        self.promotion_notice.setStyleSheet("color: #facc15; font-size: 18px; font-weight: 750;")
        self.promotion_notice.setWordWrap(True)
        move_card_layout.addWidget(self.promotion_notice)
        right.addWidget(move_card)

        self.move_explanation = QLabel("Move explanation: —")
        self.move_explanation.setObjectName("muted")
        self.move_explanation.setWordWrap(True)
        right.addWidget(self.move_explanation)
        pv_label = QLabel("ENGINE LINE")
        pv_label.setObjectName("section")
        right.addWidget(pv_label)
        self.variation = QLabel("Principal variation: —")
        self.variation.setObjectName("muted")
        self.variation.setWordWrap(True)
        right.addWidget(self.variation)
        right.addStretch(1)
        status_title = QLabel("POSITION STATUS")
        status_title.setObjectName("section")
        right.addWidget(status_title)
        self.position_status = QLabel("No screenshot loaded")
        self.position_status.setObjectName("muted")
        self.position_status.setWordWrap(True)
        right.addWidget(self.position_status)
        self.analyze_button = QPushButton("Capture New Screenshot")
        self.analyze_button.setObjectName("primary")
        self.analyze_button.clicked.connect(self.capture_screenshot)
        right.addWidget(self.analyze_button)
        content.addWidget(right_panel, 4)

    def refresh_position(self):
        position_file = DATA_ROOT / "recognized_position.txt"

        if not position_file.exists():
            QMessageBox.warning(
                self,
                "Position Not Found",
                "No recognized position was found.\n"
                "Run recognition_v2.py first."
            )
            return

        try:
            placement = position_file.read_text(
                encoding="utf-8"
            ).strip()

            # Verify that the saved piece placement is readable.
            chess.Board(f"{placement} w - - 0 1")

            self.draw_board()

            self.position_status.setText(
                "Recognized position loaded successfully."
            )

            self.best_arrow = None
            self.move_explanation.setText("Move explanation: —")
            self.move_instruction.setText("Select a saved position to analyze")

            # Clear results from the previous position.
            self.engine_status.setText(
                "Stockfish · Not analyzed"
            )
            self.evaluation.setText("—")
            self.best_move.setText("Suggested move: —")
            self.promotion_notice.setText("")
            self.variation.setText("Principal variation: —")

        except (ValueError, OSError) as error:
            QMessageBox.warning(
                self,
                "Invalid Position",
                str(error)
            )


    
    def toggle_move_arrow(self, checked):
        """Allow the arrow to be enabled or disabled without rerunning Stockfish."""
        self.show_move_arrow = checked
        self.draw_board()

    def draw_board(self):
        """Show the best move using distinct origin/destination highlights."""
        position_file = DATA_ROOT / "recognized_position.txt"
        if position_file.exists():
            placement = position_file.read_text(encoding="utf-8").strip()
            try:
                board = chess.Board(f"{placement} w - - 0 1")
            except ValueError:
                board = chess.Board()
        else:
            board = chess.Board()

        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        fill = {}
        if self.best_arrow is not None:
            # Semi-transparent overlays preserve piece visibility.
            fill[self.best_arrow.from_square] = "#3b82f6a0"  # blue = FROM
            fill[self.best_arrow.to_square] = "#22c55ea0"    # green = TO

        svg_text = chess.svg.board(
            board=board,
            fill=fill,
            size=480,
            coordinates=False,
            colors={
                "square light": "#eeeed2",
                "square dark": "#769656",
            }
        )

        # Chess.com-inspired arrow: thick, rounded orange shaft and
        # a broad triangular head. Drawn above the pieces for clarity.
        if self.best_arrow is not None and self.show_move_arrow:
            start = self.best_arrow.from_square
            end = self.best_arrow.to_square
            # python-chess SVG uses 45 internal units per square.
            # The widget scales the complete 360x360 SVG to 480x480.
            # Drawing with 52 here would misalign the arrow.
            square_units = 45
            x1 = (chess.square_file(start) + 0.5) * square_units
            y1 = (7 - chess.square_rank(start) + 0.5) * square_units
            x2 = (chess.square_file(end) + 0.5) * square_units
            y2 = (7 - chess.square_rank(end) + 0.5) * square_units
            dx, dy = x2 - x1, y2 - y1
            distance = math.hypot(dx, dy)
            if distance > 0:
                ux, uy = dx / distance, dy / distance
                # Shaft stops at the head; head tip stays within target square.
                tip_x, tip_y = x2 - ux * 6, y2 - uy * 6
                base_x, base_y = tip_x - ux * 23, tip_y - uy * 23
                perp_x, perp_y = -uy, ux
                shaft_x = base_x - ux * 2
                shaft_y = base_y - uy * 2
                left_x, left_y = base_x + perp_x * 17, base_y + perp_y * 17
                right_x, right_y = base_x - perp_x * 17, base_y - perp_y * 17
                arrow_svg = f"""
                <g opacity="0.87" fill="#e69b24" stroke="#e69b24">
                  <line x1="{x1:.2f}" y1="{y1:.2f}"
                        x2="{shaft_x:.2f}" y2="{shaft_y:.2f}"
                        stroke-width="12" stroke-linecap="round" />
                  <polygon points="{tip_x:.2f},{tip_y:.2f}
                                   {left_x:.2f},{left_y:.2f}
                                   {right_x:.2f},{right_y:.2f}"
                           stroke="none" />
                </g>
                """
                svg_text = svg_text.replace("</svg>", arrow_svg + "</svg>")

        svg_data = svg_text.encode("utf-8")

        board_view = QSvgWidget()
        board_view.setFixedSize(480, 480)
        board_view.load(svg_data)
        self.board_layout.addWidget(board_view, 0, 0)

    def describe_move(self, board, move):
        """Explain a legal chess move using its origin and destination."""
        piece = board.piece_at(move.from_square)
        if piece is None:
            return "Move details unavailable."

        side = "White" if piece.color == chess.WHITE else "Black"
        piece_name = chess.piece_name(piece.piece_type)
        origin = chess.square_name(move.from_square)
        destination = chess.square_name(move.to_square)

        if board.is_castling(move):
            direction = "kingside" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "queenside"
            return f"{side} castles {direction}."

        if board.is_en_passant(move):
            return f"{side} pawn from {origin} captures en passant on {destination}."

        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            captured_name = chess.piece_name(captured.piece_type) if captured else "piece"
            description = f"{side} {piece_name} from {origin} captures a {captured_name} on {destination}"
        else:
            description = f"{side} {piece_name} moves from {origin} to {destination}"

        if move.promotion:
            description += f", promoting to a {chess.piece_name(move.promotion)}"
        return description + "."

    def detect_turn_or_assume_white(self):
        """Use the detected turn, or explicitly fall back to White.

        Persist the fallback so the existing analysis action can read it.
        """
        detected = detect_turn()
        if detected in ("w", "b"):
            return detected, False

        (DATA_ROOT / "detected_turn.txt").write_text("w", encoding="utf-8")
        return "w", True

    def select_board(self):
        screenshot_path = DATA_ROOT / "screenshot.png"

        if not screenshot_path.exists():
            QMessageBox.warning(self, "No Screenshot", "Capture a screenshot first.")
            return

        image = cv2.imread(str(screenshot_path))
        if image is None:
            QMessageBox.warning(self, "Image Error", "Could not open the screenshot.")
            return

        selection = cv2.selectROI(
            "Select Chessboard - ENTER to Confirm",
            image,
            showCrosshair=True,
            fromCenter=False
        )
        cv2.destroyAllWindows()
        x, y, width, height = map(int, selection)

        if width <= 0 or height <= 0:
            self.position_status.setText("Board selection canceled.")
            return

        try:
            # Save only a confirmed selection. Coordinates are tied to
            # this screenshot size and must be reselected if layout changes.
            coordinates = {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "screenshot_width": image.shape[1],
                "screenshot_height": image.shape[0],
            }
            (DATA_ROOT / "board_coordinates.json").write_text(
                json.dumps(coordinates, indent=4), encoding="utf-8"
            )

            board_image = image[y:y + height, x:x + width]
            if board_image.size == 0:
                raise ValueError("The selected board area is empty.")

            board_image = cv2.resize(
                board_image, (800, 800), interpolation=cv2.INTER_AREA
            )
            output_path = DATA_ROOT / "board.png"
            if not cv2.imwrite(str(output_path), board_image):
                raise OSError("Could not save board.png.")

            self.position_status.setText("Recognizing chess pieces...")
            QApplication.processEvents()

            step = time.perf_counter()
            placement = recognize_board()
            timing_log(f"recognition: {time.perf_counter()-step:.3f}s")
            step = time.perf_counter()
            chess.Board(f"{placement} w - - 0 1")
            self.refresh_position()

            detected, assumed = self.detect_turn_or_assume_white()
            if assumed:
                status = "Position recognized. Assuming White to move."
            else:
                side = "White" if detected == "w" else "Black"
                status = f"Position recognized. {side} to move (detected)."
            self.position_status.setText(status)

            print(f"Board updated: {output_path}")
            print(f"Recognized position: {placement}")

        except Exception as error:
            self.position_status.setText("Board update failed.")
            QMessageBox.critical(self, "Board Update Error", str(error))


    def reuse_board_coordinates(self, screenshot_path):
        """Crop a saved screenshot using the previously selected board area.

        Returns True when saved coordinates were available and applied.
        Does not perform recognition or engine analysis.
        """
        coordinates_path = DATA_ROOT / "board_coordinates.json"
        if not coordinates_path.exists():
            return False

        coordinates = json.loads(coordinates_path.read_text(encoding="utf-8"))
        image = cv2.imread(str(screenshot_path))
        if image is None:
            raise ValueError("Could not read the screenshot.")

        height, width = image.shape[:2]
        if (width != coordinates["screenshot_width"] or
                height != coordinates["screenshot_height"]):
            raise ValueError("Screenshot size changed. Select the board again.")

        x = int(coordinates["x"])
        y = int(coordinates["y"])
        w = int(coordinates["width"])
        h = int(coordinates["height"])
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
            raise ValueError("Saved board coordinates are invalid.")

        board_image = cv2.resize(
            image[y:y + h, x:x + w], (800, 800), interpolation=cv2.INTER_AREA
        )
        if not cv2.imwrite(str(DATA_ROOT / "board.png"), board_image):
            raise OSError("Could not save board.png.")
        return True


    def capture_screenshot(self):
        try:
            output_path = DATA_ROOT / "screenshot.png"

            started = time.perf_counter()
            with mss.mss() as screen:
                screen.shot(mon=1, output=str(output_path))

            timing_log(f"capture: {time.perf_counter()-started:.3f}s")
            step = time.perf_counter()
            if not self.reuse_board_coordinates(output_path):
                self.position_status.setText(
                    "Screenshot saved. Select Board once to set its location."
                )
                return

            timing_log(f"crop: {time.perf_counter()-step:.3f}s")
            step = time.perf_counter()
            # A new screenshot must never inherit an old turn result.
            (DATA_ROOT / "detected_turn.txt").unlink(missing_ok=True)
            self.position_status.setText("Recognizing updated board...")
            QApplication.processEvents()

            placement = recognize_board()
            chess.Board(f"{placement} w - - 0 1")
            self.refresh_position()

            detected, assumed = self.detect_turn_or_assume_white()
            timing_log(f"turn+refresh: {time.perf_counter()-step:.3f}s")
            if assumed:
                status = "Board updated. Assuming White to move."
            else:
                side = "White" if detected == "w" else "Black"
                status = f"Board updated. {side} to move (detected)."
            self.position_status.setText(status)
            print(f"New screenshot recognized: {placement}")
            # Analyze the saved position even when turn detection is uncertain.
            self.analyze_position()
            timing_log(f"TOTAL capture+analysis: {time.perf_counter()-started:.3f}s")

        except Exception as error:
            self.position_status.setText(
                "Automatic update failed. Select Board to reset its location."
            )
            QMessageBox.warning(
                self,
                "Screenshot Update Error",
                f"{error}\n\nYou can use Select Board to choose the board again."
            )


    def load_screenshot(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Saved Chessboard Screenshot",
            str(DATA_ROOT),
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            self.position_status.setText(
                f"Selected: {Path(file_path).name}"
            )

            QMessageBox.information(
                self,
                "Screenshot Selected",
                "Screenshot selected successfully.\n\n"
                "We'll connect image recognition in the next step."
            )

   
   
    def analyze_position(self):
        position_file = DATA_ROOT / "recognized_position.txt"
        turn_file = DATA_ROOT / "detected_turn.txt"

        if not position_file.exists():
            QMessageBox.warning(
                self,
                "No Position",
                "Please recognize a chessboard first."
            )
            return

        try:
            placement = position_file.read_text(
                encoding="utf-8"
            ).strip()

            # Automatically use the detected side to move.
            # If detection failed, don't silently assume White.
            if not turn_file.exists():
                QMessageBox.warning(
                    self,
                    "Turn Unknown",
                    "The side to move couldn't be detected.\n"
                    "Please use a screenshot with visible last-move highlights."
                )
                return

            turn = turn_file.read_text(
                encoding="utf-8"
            ).strip().lower()

            if turn not in ("w", "b"):
                raise ValueError("Invalid detected turn.")

            # Conservative defaults when move history is unavailable.
            # Castling and en passant are disabled unless known.
            fen = f"{placement} {turn} - - 0 1"
            board = chess.Board(fen)

            if not board.is_valid():
                raise ValueError(
                    "The recognized position is not valid."
                )

            # Use an exact path instead of recursively scanning the entire
            # PyInstaller _internal directory on every analysis.
            engine_name = "stockfish-windows-x86-64-universal.exe"
            candidates = [
                ROOT / engine_name,  # PyInstaller --onedir: bundled in _internal
                ROOT / "stockfish" / "stockfish" / engine_name,  # development
                ROOT / "stockfish" / engine_name,
            ]
            engine_path = next((p for p in candidates if p.is_file()), None)
            if engine_path is None:
                raise FileNotFoundError(
                    "Stockfish was not found. Checked:\n" +
                    "\n".join(str(p) for p in candidates)
                )

            self.engine_status.setText(
                "Stockfish · Analyzing..."
            )
            QApplication.processEvents()

            # Prevent a visible console window for the bundled UCI engine.
            popen_options = {}
            if os.name == "nt":
                popen_options["creationflags"] = subprocess.CREATE_NO_WINDOW
            analysis_started = time.perf_counter()
            if self.engine is None:
                self.engine = chess.engine.SimpleEngine.popen_uci(str(engine_path), **popen_options)
                timing_log(f"engine startup: {time.perf_counter()-analysis_started:.3f}s")
            engine_started = time.perf_counter()
            try:
                info = self.engine.analyse(board, chess.engine.Limit(depth=15))
            except (chess.engine.EngineTerminatedError, chess.engine.EngineError):
                # Restart the engine if it unexpectedly stops.
                try:
                    self.engine.quit()
                except Exception:
                    pass
                self.engine = chess.engine.SimpleEngine.popen_uci(str(engine_path), **popen_options)
                info = self.engine.analyse(board, chess.engine.Limit(depth=15))

            timing_log(f"engine analysis: {time.perf_counter()-engine_started:.3f}s")
            score = info["score"].white().score(
                mate_score=100000
            )

            self.evaluation.setText(
                f"{score / 100:+.2f}"
                if score is not None else "—"
            )

            variation = info.get("pv", [])

            if variation:
                best = variation[0]

                self.best_move.setText(
                    f"Suggested move: {board.san(best)}"
                )
                explanation = self.describe_move(board, best)
                self.move_explanation.setText(explanation)
                from_name = chess.square_name(best.from_square)
                to_name = chess.square_name(best.to_square)
                self.move_instruction.setText(
                    f"FROM {from_name}  →  TO {to_name}\n{explanation}"
                )
                if best.promotion:
                    promotion_name = chess.piece_name(best.promotion).upper()
                    self.promotion_notice.setText(
                        f"PROMOTE TO {promotion_name}"
                    )
                else:
                    self.promotion_notice.setText("")
                self.best_arrow = best
                self.draw_board()

                temp = board.copy()
                moves = []

                for move in variation[:8]:
                    moves.append(
                        f"{temp.fullmove_number}"
                        f"{'.' if temp.turn else '...'} "
                        f"{temp.san(move)}"
                    )
                    temp.push(move)

                self.variation.setText(
                    "Principal variation: " + " ".join(moves)
                )
            else:
                self.best_arrow = None
                self.draw_board()
                self.move_explanation.setText("Move explanation: —")
                self.move_instruction.setText("No move available")
                self.best_move.setText("Suggested move: —")
                self.promotion_notice.setText("")
                self.variation.setText(
                    "Principal variation: —"
                )

            self.engine_status.setText(
                "Stockfish · Depth 15"
            )
            timing_log(f"analysis total (including display): {time.perf_counter()-analysis_started:.3f}s")

        except Exception as error:
            self.engine_status.setText(
                "Stockfish · Analysis failed"
            )

            QMessageBox.critical(
                self,
                "Analysis Error",
                str(error)
            )




    def closeEvent(self, event):
        if self.engine is not None:
            try:
                self.engine.quit()
            except Exception:
                pass
            self.engine = None
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ChessAnalyzer()
    window.show()

    sys.exit(app.exec())
