import sys
import random
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QPoint, Qt, QTimer, Slot, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

# Constants (derived from Tcl script's setup)
BOARD_WIDTH_BLOCKS = 10
BOARD_HEIGHT_BLOCKS = 22  # Standard Tetris height
BLOCK_SIZE_PX = 20  # Slightly larger blocks for better visiblity
BOARD_WIDTH_PX = BOARD_WIDTH_BLOCKS * BLOCK_SIZE_PX
BOARD_HEIGHT_PX = BOARD_HEIGHT_BLOCKS * BLOCK_SIZE_PX
TETRIS_SHAPES = (  # Defines the 7 Tetris pieces (coords relative to a pivot)
    ((0, 0), (0, 1), (1, 0), (1, 1)),  # Square (O)
    ((0, -1), (0, 0), (0, 1), (0, 2)),  # Line (I) - Vertical
    ((0, -1), (0, 0), (1, 0), (-1, 0)),  # T-shape
    ((0, 0), (-1, 0), (1, 0), (1, 1)),  # L-shape
    ((0, 0), (-1, 0), (1, 0), (-1, 1)),  # Mirrored L-shape (J)
    ((0, 0), (1, 0), (0, 1), (-1, 1)),  # S-shape
    ((0, 0), (-1, 0), (0, 1), (1, 1)),  # Z-shape
)
TETRIS_COLORS = (  # Colors for each shape (RGBA)
    QColor(255, 0, 0, 200),  # Red
    QColor(0, 255, 0, 200),  # Green
    QColor(0, 0, 255, 200),  # Blue
    QColor(255, 255, 0, 200),  # Yellow
    QColor(255, 0, 255, 200),  # Magenta
    QColor(0, 255, 255, 200),  # Cyan
    QColor(255, 165, 0, 200),  # Orange (replaced White from Tcl)
)

# Sentinel value for empty cells in board_state
NO_BLOCK = 0
NEXT_PIECE_AREA_WIDTH_BLOCKS = 4
NEXT_PIECE_AREA_HEIGHT_BLOCKS = 4


class NextPieceWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        width = NEXT_PIECE_AREA_WIDTH_BLOCKS * BLOCK_SIZE_PX + 10
        height = NEXT_PIECE_AREA_HEIGHT_BLOCKS * BLOCK_SIZE_PX + 10
        self.setFixedSize(width, height)
        self.setStyleSheet("background-color: lightgrey; border: 1px solid black;")
        self.next_piece_index = -1

    @Slot(int)
    def set_next_piece(self, shape_index):
        if 1 <= shape_index <= len(TETRIS_SHAPES):
            self.next_piece_index = shape_index
        else:
            self.next_piece_index = -1
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.next_piece_index == -1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        shape_coords_rel = TETRIS_SHAPES[self.next_piece_index - 1]
        color = TETRIS_COLORS[self.next_piece_index - 1]

        min_x = min(p[0] for p in shape_coords_rel)
        max_x = max(p[0] for p in shape_coords_rel)
        min_y = min(p[1] for p in shape_coords_rel)
        max_y = max(p[1] for p in shape_coords_rel)
        piece_width_blocks = max_x - min_x + 1
        piece_height_blocks = max_y - min_y + 1

        start_x_px = (self.width() - piece_width_blocks * BLOCK_SIZE_PX) // 2
        start_y_px = (self.height() - piece_height_blocks * BLOCK_SIZE_PX) // 2

        offset_x_px = -min_x * BLOCK_SIZE_PX
        offset_y_px = -min_y * BLOCK_SIZE_PX

        painter.setPen(color.darker(120))
        painter.setBrush(QBrush(color))

        for point_offset in shape_coords_rel:
            rect_x = start_x_px + offset_x_px + point_offset[0] * BLOCK_SIZE_PX
            rect_y = start_y_px + offset_y_px + point_offset[1] * BLOCK_SIZE_PX
            painter.drawRect(rect_x, rect_y, BLOCK_SIZE_PX - 1, BLOCK_SIZE_PX - 1)


class GameBoard(QFrame):
    update_score_signal = Signal(int)
    update_level_signal = Signal(int)
    update_rows_signal = Signal(int)
    game_over_signal = Signal()
    next_piece_ready_signal = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BOARD_WIDTH_PX, BOARD_HEIGHT_PX)
        self.setStyleSheet("background-color: #DDDDDD; border: 1px solid black;")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.board_state = []
        self.current_piece_shape_index = -1
        self.current_piece_coords = []
        self.current_pos = QPoint(0, 0)
        self.next_piece_shape_index = -1
        self.is_started = False
        self.is_paused = False
        self.show_shadow = True  # Option to toggle shadow piece (from Tcl)
        self.score = 0
        self.level = 0
        self.rows_cleared_total = 0

        self.reset_board()

    def get_color_for_index(self, index):
        """Safely get color, return black if index is invalid (e.g., NO_BLOCK)."""
        if 1 <= index <= len(TETRIS_COLORS):
            return TETRIS_COLORS[index - 1]  # Use index-1 as shape indices are 1-based
        return QColor("black")  # Should not happen for pieces

    def reset_board(self):
        """Clears the board and resets piece state."""
        self.board_state = [
            [NO_BLOCK for _ in range(BOARD_WIDTH_BLOCKS)]
            for _ in range(BOARD_HEIGHT_BLOCKS)
        ]
        self.current_piece_coords = []
        self.current_piece_shape_index = -1
        self.next_piece_shape_index = random.randint(
            1, len(TETRIS_SHAPES)
        )  # Pre-select first 'next'
        self.is_started = False
        self.is_paused = False
        self.score = 0
        self.level = 0
        self.rows_cleared_total = 0
        # Emit signals to reset display in MainWindow
        self.update_score_signal.emit(self.score)
        self.update_level_signal.emit(self.level)
        self.update_rows_signal.emit(self.rows_cleared_total)
        self.next_piece_ready_signal.emit(self.next_piece_shape_index)
        self.update()

    def start_game(self):
        """Starts a new game."""
        self.reset_board()
        self.is_started = True
        self.is_paused = False
        self.create_new_piece()  # This will use and update next_piece_shape_index
        self.setFocus()

    def pause_game(self):
        if not self.is_started or self.is_paused:
            return
        self.is_paused = True
        self.update()  # Optional: redraw to show paused state?

    def resume_game(self):
        if not self.is_started or not self.is_paused:
            return
        self.is_paused = False
        self.setFocus()
        self.update()

    def create_new_piece(self):
        """Selects a new random piece and places it at the top."""
        # The 'next' piece becomes the 'current' piece
        self.current_piece_shape_index = self.next_piece_shape_index
        shape_coords = TETRIS_SHAPES[self.current_piece_shape_index - 1]
        # Start position: center horizontally, slightly above visible board
        self.current_pos = QPoint(BOARD_WIDTH_BLOCKS // 2, 1)

        self.current_piece_coords = []
        for point_offset in shape_coords:
            # Add piece's relative coords to current board position
            coord = QPoint(
                self.current_pos.x() + point_offset[0],
                self.current_pos.y() + point_offset[1],
            )
            self.current_piece_coords.append(coord)

        # Select the 'new' next piece and signal it
        self.next_piece_shape_index = random.randint(1, len(TETRIS_SHAPES))
        self.next_piece_ready_signal.emit(self.next_piece_shape_index)

        # Check for immediate collision (Game Over condition)
        if not self.check_collision(self.current_piece_coords):
            self.is_started = False  # Game Over
            self.current_piece_coords = []  # Don't draw invalid piece
            self.game_over_signal.emit()
        self.update()

    def check_collision(self, piece_coords):
        """Checks if the proposed piece coordinates are valid."""
        # In Tcl: checks against the 'block' array boundaries and values
        for point in piece_coords:
            x = point.x()
            y = point.y()
            # Check boundaries
            if x < 0 or x >= BOARD_WIDTH_BLOCKS or y < 0 or y >= BOARD_HEIGHT_BLOCKS:
                return False  # Out of bounds
            # Check board_state bounds before accessing
            if 0 <= y < BOARD_HEIGHT_BLOCKS and self.board_state[y][x] != NO_BLOCK:
                return False
        return True

    def move_piece(self, dx, dy):
        """Attempts to move the current piece by dx, dy."""
        if not self.current_piece_coords or self.is_paused:
            return False

        new_coords = [QPoint(p.x() + dx, p.y() + dy) for p in self.current_piece_coords]
        if self.check_collision(new_coords):
            self.current_piece_coords = new_coords
            self.current_pos += QPoint(dx, dy)  # Update pivot position
            self.update()
            return True
        else:
            return False

    def rotate_piece(self):
        """Rotates the current piece clockwise."""
        # In Tcl: 'Rotate' proc (more complex with left/right)
        if not self.current_piece_coords or self.is_paused:
            return

        # Cannot rotate the square piece
        if self.current_piece_shape_index == 1:  # Index 1 is the Square
            return

        pivot = self.current_pos
        new_coords = []
        for point in self.current_piece_coords:
            # Translate point relative to pivot, rotate, translate back
            rel_x = point.x() - pivot.x()
            rel_y = point.y() - pivot.y()
            # Clockwise rotation matrix: new_x = -rel_y; new_y = rel_x
            new_rel_x = -rel_y
            new_rel_y = rel_x
            new_coords.append(QPoint(pivot.x() + new_rel_x, pivot.y() + new_rel_y))

        if self.check_collision(new_coords):
            self.current_piece_coords = new_coords
            self.update()
        # Optional: Add wall kick logic here if needed

    def slide_down(self):
        """Moves the piece down one step. Returns False if it collides."""
        # In Tcl: 'Slide' proc (just moves down)
        if not self.move_piece(0, 1):
            # Collision occurred, piece cannot move down further
            self.cement_piece()
            return False
        return True

    def drop_piece(self):
        """Drops the piece straight down until it collides."""
        # In Tcl: 'Drop' proc
        if not self.current_piece_coords or self.is_paused:
            return
        # Calculate final position directly using shadow logic helper
        shadow_coords = self._calculate_shadow_position()
        if shadow_coords:
            dy = shadow_coords[0].y() - self.current_piece_coords[0].y()
            self.current_pos += QPoint(0, dy)
            self.current_piece_coords = shadow_coords
            self.cement_piece()
            self.update()

    def cement_piece(self):
        """Adds the current piece blocks to the board state."""
        # In Tcl: 'CementPiece' proc
        if not self.current_piece_coords:
            return

        for point in self.current_piece_coords:
            # Ensure point is within bounds before setting board state
            if (
                0 <= point.y() < BOARD_HEIGHT_BLOCKS
                and 0 <= point.x() < BOARD_WIDTH_BLOCKS
            ):
                self.board_state[point.y()][point.x()] = self.current_piece_shape_index

        self.clear_lines()  # Check for and clear completed lines
        self.current_piece_coords = []  # Piece is now part of the board
        self.current_piece_shape_index = -1
        # Only create next piece if game hasn't ended
        if self.is_started:
            self.create_new_piece()

    def clear_lines(self):
        """Checks for and removes completed lines."""
        # In Tcl: 'DropRows' proc
        lines_to_clear = []
        for y in range(BOARD_HEIGHT_BLOCKS):
            if all(
                self.board_state[y][x] != NO_BLOCK for x in range(BOARD_WIDTH_BLOCKS)
            ):
                lines_to_clear.append(y)

        if not lines_to_clear:
            return  # No lines cleared

        num_cleared = len(lines_to_clear)
        self.rows_cleared_total += num_cleared

        # Update Score (example scoring, Tcl script uses pow(num_cleared, 2)*(level+1))
        score_gain = num_cleared * num_cleared * (self.level + 1) * 10  # Simple scoring
        self.score += score_gain

        # Check Level Up (every 10 rows in Tcl)
        new_level = self.rows_cleared_total // 10
        if new_level > self.level:
            self.level = new_level
            # Optional: Increase game speed here by adjusting timer interval

        # Remove lines and shift blocks down
        # Iterate downwards from the bottom-most cleared line
        lines_to_clear.sort(reverse=True)
        for line_y in lines_to_clear:
            # Shift all rows above it down by one
            for y in range(line_y, 0, -1):
                self.board_state[y] = list(self.board_state[y - 1])  # Copy row above
            # Clear the top row
            self.board_state[0] = [NO_BLOCK for _ in range(BOARD_WIDTH_BLOCKS)]

        # Emit signals to update MainWindow display
        self.update_score_signal.emit(self.score)
        self.update_level_signal.emit(self.level)
        self.update_rows_signal.emit(self.rows_cleared_total)
        self.update()

    def _calculate_shadow_position(self):
        if not self.current_piece_coords:
            return []

        shadow_coords = list(self.current_piece_coords)
        dy = 0
        while True:
            dy += 1
            potential_coords = [
                QPoint(p.x(), p.y() + dy) for p in self.current_piece_coords
            ]
            if not self.check_collision(potential_coords):
                dy -= 1
                break
        return [QPoint(p.x(), p.y(), +dy) for p in self.current_piece_coords]

    def paintEvent(self, event):
        """Draws the board grid, fallen pieces, and current piece."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw fallen pieces
        for y in range(BOARD_HEIGHT_BLOCKS):
            for x in range(BOARD_WIDTH_BLOCKS):
                block_index = self.board_state[y][x]
                if block_index != NO_BLOCK:
                    color = self.get_color_for_index(block_index)
                    # Draw rectangle for the block
                    rect_x = x * BLOCK_SIZE_PX
                    rect_y = y * BLOCK_SIZE_PX
                    painter.fillRect(
                        rect_x, rect_y, BLOCK_SIZE_PX, BLOCK_SIZE_PX, color
                    )
                    painter.setPen(color.darker(120))  # Slightly darker border
                    painter.drawRect(
                        rect_x, rect_y, BLOCK_SIZE_PX - 1, BLOCK_SIZE_PX - 1
                    )

        # Draw shadow piece (if enabled and piece exists)
        if self.show_shadow and self.current_piece_coords:
            shadow_coords = self._calculate_shadow_position()
            if shadow_coords:
                color = self.get_color_for_index(self.current_piece_shape_index)
                shadow_pen = QPen(color.darker(110), 1)
                shadow_brush = QBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(shadow_pen)
                painter.setBrush(shadow_brush)
                for point in shadow_coords:
                    rect_x = point.x() * BLOCK_SIZE_PX
                    rect_y = point.y() * BLOCK_SIZE_PX
                    painter.drawRect(
                        rect_x + 1, rect_y + 1, BLOCK_SIZE_PX - 2, BLOCK_SIZE_PX - 2
                    )

        # Draw Current Piece  (on top of shadow)
        if self.current_piece_coords:
            color = self.get_color_for_index(self.current_piece_shape_index)
            painter.setBrush(QBrush(color))
            painter.setPen(color.darker(120))
            for point in self.current_piece_coords:
                # Draw rectangle for the block
                rect_x = point.x() * BLOCK_SIZE_PX
                rect_y = point.y() * BLOCK_SIZE_PX
                painter.fillRect(rect_x, rect_y, BLOCK_SIZE_PX, BLOCK_SIZE_PX, color)
                painter.drawRect(rect_x, rect_y, BLOCK_SIZE_PX - 1, BLOCK_SIZE_PX - 1)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PySide6 Tetris")
        self.game_state = "Init"
        self.current_interval = 500  # ms

        # Timers
        self.fall_timer = QTimer(self)
        self.fall_timer.timeout.connect(self.game_step)

        # Central Widget and Layouts
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)

        # Left Panel
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.title_label = QLabel(f"Tetris v?.? (PySide6)")
        self.next_piece_label = QLabel("Next Object")
        self.next_piece_display = NextPieceWidget()

        info_layout = QGridLayout()
        self.score_label = QLabel("Score:")
        self.score_value = QLabel("0")
        self.level_label = QLabel("Level:")
        self.level_value = QLabel("0")
        self.rows_label = QLabel("Rows:")
        self.rows_value = QLabel("0")
        info_layout.addWidget(self.score_label, 0, 0)
        info_layout.addWidget(self.score_value, 0, 1, Qt.AlignmentFlag.AlignRight)
        info_layout.addWidget(self.level_label, 1, 0)
        info_layout.addWidget(self.level_value, 1, 1, Qt.AlignmentFlag.AlignRight)
        info_layout.addWidget(self.rows_label, 2, 0)
        info_layout.addWidget(self.rows_value, 2, 1, Qt.AlignmentFlag.AlignRight)
        self.start_pause_button = QPushButton("Start")
        self.reset_button = QPushButton("Reset")
        self.options_button = QPushButton("Options")  # Still placeholder
        self.quit_button = QPushButton("Quit")
        left_layout.addWidget(self.title_label)
        left_layout.addWidget(self.next_piece_label)
        left_layout.addWidget(
            self.next_piece_display, alignment=Qt.AlignmentFlag.AlignCenter
        )
        left_layout.addLayout(info_layout)
        left_layout.addWidget(self.start_pause_button)
        left_layout.addWidget(self.reset_button)
        left_layout.addWidget(self.options_button)
        left_layout.addWidget(self.quit_button)
        left_layout.addStretch()

        # Right Panel
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        # No shadow display for now
        self.game_board = GameBoard()
        right_layout.addWidget(self.game_board)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        self.setCentralWidget(central_widget)

        # Connections
        self.start_pause_button.clicked.connect(self.toggle_game_state)
        self.reset_button.clicked.connect(self.reset_game)
        self.quit_button.clicked.connect(QApplication.instance().quit)
        self.game_board.update_score_signal.connect(self.update_score_display)
        self.game_board.update_level_signal.connect(self.update_level_display)
        self.game_board.update_rows_signal.connect(self.update_rows_display)
        self.game_board.game_over_signal.connect(self.handle_game_over)
        self.game_board.next_piece_ready_signal.connect(
            self.next_piece_display.set_next_piece
        )

        self.reset_game()

    @Slot()
    def game_step(self):
        """Called by the fall_timer timeout."""
        if self.game_state == "Playing" and not self.game_board.is_paused:
            self.game_board.slide_down()

    @Slot()
    def toggle_game_state(self):
        if self.game_state == "Init" or self.game_state == "GameOver":
            self.game_state = "Playing"
            self.start_pause_button.setText("Pause")
            # Reset interval based on level (starts at 0 -> 500ms)
            self.update_timer_interval()
            self.game_board.start_game()
            self.fall_timer.start(self.current_interval)
        elif self.game_state == "Playing":
            if self.game_board.is_paused:  # Currently paused, resume
                self.game_state = "Playing"
                self.start_pause_button.setText("Pause")
                self.game_board.resume_game()
                self.fall_timer.start(self.current_interval)
            else:  # Currently playing, pause
                self.game_state = "Paused"  # Use a distinct state
                self.start_pause_button.setText("Resume")
                self.game_board.pause_game()
                self.fall_timer.stop()
        elif self.game_state == "Paused":  # Explicitly handle resuming from Paused
            self.game_state = "Playing"
            self.start_pause_button.setText("Pause")
            self.game_board.resume_game()
            self.fall_timer.start(self.current_interval)

    @Slot()
    def reset_game(self):
        self.fall_timer.stop()
        self.game_state = "Init"
        self.start_pause_button.setText("Start")
        self.game_board.reset_board()  # Will emit signals to reset labels

    @Slot()
    def handle_game_over(self):
        self.fall_timer.stop()
        self.game_state = "GameOver"
        self.start_pause_button.setText("Game Over")
        # Optionally show a message box
        print("Game Over!")

    @Slot(int)
    def update_score_display(self, score):
        self.score_value.setText(str(score))

    @Slot(int)
    def update_level_display(self, level):
        self.level_value.setText(str(level))
        self.update_timer_interval()  # Speed up timer as level increases

    @Slot(int)
    def update_rows_display(self, rows):
        self.rows_value.setText(str(rows))

    def update_timer_interval(self):
        base_interval = 500
        level_factor = base_interval / 20
        new_interval = base_interval - (level_factor * self.game_board.level)
        self.current_interval = max(30, int(new_interval))
        if self.fall_timer.isActive():
            self.fall_timer.setInterval(self.current_interval)

    def keyPressEvent(self, event):
        if self.game_state != "Playing" or self.game_board.is_paused:
            event.ignore()
            return
        key = event.key()
        board = self.game_board
        if key == Qt.Key.Key_Left:
            board.move_piece(-1, 0)
        elif key == Qt.Key.Key_Right:
            board.move_piece(1, 0)
        elif key == Qt.Key.Key_Up:
            board.rotate_piece()
        elif key == Qt.Key.Key_Down:
            board.slide_down()
        elif key == Qt.Key.Key_Space:
            board.drop_piece()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
