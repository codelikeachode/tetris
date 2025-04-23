# -*- coding: utf-8 -*-
# Add encoding declaration for potential special characters in comments/strings

import sys
import random
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import QPoint, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

# --- Constants ---
BOARD_WIDTH_BLOCKS = 10
BOARD_HEIGHT_BLOCKS = 22
BLOCK_SIZE_PX = 20
BOARD_WIDTH_PX = BOARD_WIDTH_BLOCKS * BLOCK_SIZE_PX
BOARD_HEIGHT_PX = BOARD_HEIGHT_BLOCKS * BLOCK_SIZE_PX
TETRIS_SHAPES = (  # Defines the 7 Tetris pieces (coords relative to a pivot)
    ((0, 0), (0, 1), (1, 0), (1, 1)),  # Square (O) - Index 1
    ((0, -1), (0, 0), (0, 1), (0, 2)),  # Line (I) - Index 2
    ((0, -1), (0, 0), (1, 0), (-1, 0)),  # T-shape - Index 3
    ((0, 0), (-1, 0), (1, 0), (1, 1)),  # L-shape - Index 4
    ((0, 0), (-1, 0), (1, 0), (-1, 1)),  # Mirrored L-shape (J) - Index 5
    ((0, 0), (1, 0), (0, 1), (-1, 1)),  # S-shape - Index 6
    ((0, 0), (-1, 0), (0, 1), (1, 1)),  # Z-shape - Index 7
)
TETRIS_COLORS = ( # Neon-style Colors (fully opaque - alpha 255)
    QColor(255, 255, 51),   # Bright Yellow (O)
    QColor(51, 255, 255),   # Bright Cyan (I)
    QColor(255, 51, 255),   # Bright Magenta (T)
    QColor(255, 153, 51),   # Bright Orange (L)
    QColor(51, 102, 255),   # Bright Blue (J)
    QColor(102, 255, 51),   # Bright Green (S)
    QColor(255, 51, 51)     # Bright Red (Z)
)
NO_BLOCK = 0
NEXT_PIECE_AREA_WIDTH_BLOCKS = 4  # How many blocks wide the next piece area is
NEXT_PIECE_AREA_HEIGHT_BLOCKS = 4  # How many blocks high


# --- Next Piece Widget ---
class NextPieceWidget(QFrame):
    """Widget to display the upcoming Tetris piece."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Calculate size based on blocks it needs to contain + padding
        width = NEXT_PIECE_AREA_WIDTH_BLOCKS * BLOCK_SIZE_PX + 10
        height = NEXT_PIECE_AREA_HEIGHT_BLOCKS * BLOCK_SIZE_PX + 10
        self.setFixedSize(width, height)
        self.setStyleSheet("background-color: lightgrey; border: 1px solid black;")
        self.next_piece_index = -1  # Index (1-7) of the piece to draw, -1 for none

    @Slot(int)
    def set_next_piece(self, shape_index):
        """Sets the piece to display and triggers a repaint."""
        if 1 <= shape_index <= len(TETRIS_SHAPES):
            self.next_piece_index = shape_index
        else:
            self.next_piece_index = -1
        self.update()  # Trigger paintEvent

    def paintEvent(self, event):
        """Draws the specified next piece, centered."""
        super().paintEvent(event)  # Draw frame background/border
        if self.next_piece_index == -1:
            return  # Nothing to draw

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        shape_coords_rel = TETRIS_SHAPES[self.next_piece_index - 1]
        color = TETRIS_COLORS[self.next_piece_index - 1]

        # Find bounds of the piece to center it
        min_x = min(p[0] for p in shape_coords_rel)
        max_x = max(p[0] for p in shape_coords_rel)
        min_y = min(p[1] for p in shape_coords_rel)
        max_y = max(p[1] for p in shape_coords_rel)
        piece_width_blocks = max_x - min_x + 1
        piece_height_blocks = max_y - min_y + 1

        # Calculate top-left position for drawing to center the piece
        start_x_px = (self.width() - piece_width_blocks * BLOCK_SIZE_PX) // 2
        start_y_px = (self.height() - piece_height_blocks * BLOCK_SIZE_PX) // 2

        # Adjust for the piece's internal origin (relative coords)
        offset_x_px = -min_x * BLOCK_SIZE_PX
        offset_y_px = -min_y * BLOCK_SIZE_PX

        painter.setPen(color.darker(120))
        painter.setBrush(QBrush(color))

        for point_offset in shape_coords_rel:
            rect_x = start_x_px + offset_x_px + point_offset[0] * BLOCK_SIZE_PX
            rect_y = start_y_px + offset_y_px + point_offset[1] * BLOCK_SIZE_PX
            painter.drawRect(rect_x, rect_y, BLOCK_SIZE_PX - 1, BLOCK_SIZE_PX - 1)


# Game Board Widget
class GameBoard(QFrame):
    update_score_signal = Signal(int)
    update_level_signal = Signal(int)
    update_rows_signal = Signal(int)
    game_over_signal = Signal()
    next_piece_ready_signal = Signal(int)  # Signal for the next piece index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BOARD_WIDTH_PX, BOARD_HEIGHT_PX)
        # self.setStyleSheet("background-color: #DDDDDD; border: 1px solid black;") # Old light grey
        self.setStyleSheet("background-color: #1C1C1C; border: 1px solid #444444;") # New dark grey background, slightly lighter border
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.board_state = []  # Initialized in reset_board
        self.current_piece_shape_index = -1
        self.current_piece_coords = []
        self.current_pos = QPoint(0, 0)
        self.next_piece_shape_index = -1  # Store the index of the next piece
        self.is_started = False
        self.is_paused = False
        self.show_shadow = True  # Option to toggle shadow piece (from Tcl)
        self.score = 0
        self.level = 0
        self.rows_cleared_total = 0

        self.reset_board()

    def get_color_for_index(self, index):
        if 1 <= index <= len(TETRIS_COLORS):
            return TETRIS_COLORS[index - 1]
        return QColor("black")

    def reset_board(self):
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
        self.update_score_signal.emit(self.score)
        self.update_level_signal.emit(self.level)
        self.update_rows_signal.emit(self.rows_cleared_total)
        self.next_piece_ready_signal.emit(
            self.next_piece_shape_index
        )  # Show initial next piece
        self.update()

    def start_game(self):
        self.reset_board()
        self.is_started = True
        self.is_paused = False
        self.create_new_piece()  # This will use & update next_piece_shape_index
        self.setFocus()

    def pause_game(self):
        if not self.is_started or self.is_paused:
            return
        self.is_paused = True
        self.update()

    def resume_game(self):
        if not self.is_started or not self.is_paused:
            return
        self.is_paused = False
        self.setFocus()
        self.update()

    def create_new_piece(self):
        # The 'next' piece becomes the 'current' piece
        self.current_piece_shape_index = self.next_piece_shape_index
        shape_coords = TETRIS_SHAPES[self.current_piece_shape_index - 1]
        self.current_pos = QPoint(BOARD_WIDTH_BLOCKS // 2, 1)
        self.current_piece_coords = []
        for point_offset in shape_coords:
            coord = QPoint(
                self.current_pos.x() + point_offset[0],
                self.current_pos.y() + point_offset[1],
            )
            self.current_piece_coords.append(coord)

        # Select the *new* next piece and signal it
        self.next_piece_shape_index = random.randint(1, len(TETRIS_SHAPES))
        self.next_piece_ready_signal.emit(self.next_piece_shape_index)

        # Check for immediate collision (Game Over condition)
        if not self.check_collision(self.current_piece_coords):
            self.is_started = False
            self.current_piece_coords = []
            self.game_over_signal.emit()
        self.update()

    def check_collision(self, piece_coords):
        for point in piece_coords:
            x = point.x()
            y = point.y()
            if x < 0 or x >= BOARD_WIDTH_BLOCKS or y < 0 or y >= BOARD_HEIGHT_BLOCKS:
                return False
            # Check board_state bounds before accessing
            if 0 <= y < BOARD_HEIGHT_BLOCKS and self.board_state[y][x] != NO_BLOCK:
                return False
        return True

    def move_piece(self, dx, dy):
        if not self.current_piece_coords or self.is_paused:
            return False
        new_coords = [QPoint(p.x() + dx, p.y() + dy) for p in self.current_piece_coords]
        if self.check_collision(new_coords):
            self.current_piece_coords = new_coords
            self.current_pos += QPoint(dx, dy)
            self.update()
            return True
        else:
            return False

    def rotate_piece(self):
        if not self.current_piece_coords or self.is_paused:
            return
        if self.current_piece_shape_index == 1:  # Square
            return
        pivot = self.current_pos
        new_coords = []
        for point in self.current_piece_coords:
            rel_x = point.x() - pivot.x()
            rel_y = point.y() - pivot.y()
            new_rel_x = -rel_y
            new_rel_y = rel_x
            new_coords.append(QPoint(pivot.x() + new_rel_x, pivot.y() + new_rel_y))
        if self.check_collision(new_coords):
            self.current_piece_coords = new_coords
            self.update()

    def slide_down(self):
        if not self.move_piece(0, 1):
            self.cement_piece()
            return False
        return True

    def drop_piece(self):
        if not self.current_piece_coords or self.is_paused:
            return
        # Calculate final position directly using shadow logic helper
        shadow_coords = self._calculate_shadow_position()
        if shadow_coords:
            # Update current piece position and cement it
            dy = shadow_coords[0].y() - self.current_piece_coords[0].y()
            self.current_pos += QPoint(0, dy)
            self.current_piece_coords = shadow_coords
            self.cement_piece()  # Cement immediately after dropping
            self.update()

    def cement_piece(self):
        if not self.current_piece_coords:
            return
        for point in self.current_piece_coords:
            if (
                0 <= point.y() < BOARD_HEIGHT_BLOCKS
                and 0 <= point.x() < BOARD_WIDTH_BLOCKS
            ):
                self.board_state[point.y()][point.x()] = self.current_piece_shape_index
        self.clear_lines()
        
        self.current_piece_coords = []
        self.current_piece_shape_index = -1
        # Only create next piece if game hasn't ended
        if self.is_started:
            self.create_new_piece()
        # No need for another self.update() here, create_new_piece calls it.

    def clear_lines(self):
        lines_to_clear = []
        for y in range(BOARD_HEIGHT_BLOCKS):
            if all(
                self.board_state[y][x] != NO_BLOCK for x in range(BOARD_WIDTH_BLOCKS)
            ):
                lines_to_clear.append(y)
        if not lines_to_clear:
            return
        num_cleared = len(lines_to_clear)
        self.rows_cleared_total += num_cleared
        score_gain = num_cleared * num_cleared * (self.level + 1) * 10
        self.score += score_gain
        new_level = self.rows_cleared_total // 10
        if new_level > self.level:
            self.level = new_level
            
        # Rebuild board state instead of shifting
        new_board_state = [[NO_BLOCK for _ in range(BOARD_WIDTH_BLOCKS)]
                           for _ in range(BOARD_HEIGHT_BLOCKS)]
        
        new_row_index = BOARD_HEIGHT_BLOCKS - 1
        for old_row_index in range(BOARD_HEIGHT_BLOCKS - 1, -1, -1):
            if old_row_index not in lines_to_clear:
                if new_row_index >= 0:
                    new_board_state[new_row_index] = list(self.board_state[old_row_index])
                    new_row_index -= 1
                    
        self.board_state = new_board_state
        
        self.update_score_signal.emit(self.score)
        self.update_level_signal.emit(self.level)
        self.update_rows_signal.emit(self.rows_cleared_total)
        # self.update()
        self.repaint()  # Hopefully making the widget redraw iself immediately and synchronously before the clear_lines function returns

    def _calculate_shadow_position(self):
        """Finds the lowest valid position for the current piece."""
        if not self.current_piece_coords:
            return []

        shadow_coords = list(self.current_piece_coords)  # Start with current pos
        dy = 0
        while True:
            dy += 1
            potential_coords = [
                QPoint(p.x(), p.y() + dy) for p in self.current_piece_coords
            ]
            if not self.check_collision(potential_coords):
                dy -= 1  # Last valid position was one step above
                break
        # Return the coordinates at the final valid position
        return [QPoint(p.x(), p.y() + dy) for p in self.current_piece_coords]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Fallen Pieces
        for y in range(BOARD_HEIGHT_BLOCKS):
            for x in range(BOARD_WIDTH_BLOCKS):
                block_index = self.board_state[y][x]
                if block_index != NO_BLOCK:
                    color = self.get_color_for_index(block_index)
                    rect_x = x * BLOCK_SIZE_PX
                    rect_y = y * BLOCK_SIZE_PX
                    painter.fillRect(
                        rect_x, rect_y, BLOCK_SIZE_PX, BLOCK_SIZE_PX, color
                    )
                    painter.setPen(color.darker(120))
                    painter.drawRect(
                        rect_x, rect_y, BLOCK_SIZE_PX - 1, BLOCK_SIZE_PX - 1
                    )

        # Draw Shadow Piece (if enabled and piece exists)
        if self.show_shadow and self.current_piece_coords:
            shadow_coords = self._calculate_shadow_position()
            if shadow_coords:
                color = self.get_color_for_index(self.current_piece_shape_index)
                # Use a more transparent / outline style for shadow
                shadow_pen = QPen(color.darker(110), 1)
                shadow_brush = QBrush(Qt.BrushStyle.NoBrush)  # No fill
                painter.setPen(shadow_pen)
                painter.setBrush(shadow_brush)
                for point in shadow_coords:
                    rect_x = point.x() * BLOCK_SIZE_PX
                    rect_y = point.y() * BLOCK_SIZE_PX
                    painter.drawRect(
                        rect_x + 1, rect_y + 1, BLOCK_SIZE_PX - 2, BLOCK_SIZE_PX - 2
                    )  # Inset slightly

        # Draw Current Piece (on top of shadow)
        if self.current_piece_coords:
            color = self.get_color_for_index(self.current_piece_shape_index)
            painter.setBrush(QBrush(color))  # Set brush for fill
            painter.setPen(color.darker(120))  # Keep border
            for point in self.current_piece_coords:
                rect_x = point.x() * BLOCK_SIZE_PX
                rect_y = point.y() * BLOCK_SIZE_PX
                painter.fillRect(rect_x, rect_y, BLOCK_SIZE_PX, BLOCK_SIZE_PX, color)
                painter.drawRect(rect_x, rect_y, BLOCK_SIZE_PX - 1, BLOCK_SIZE_PX - 1)
                
                
class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.stats_button = QPushButton("Stats")
        self.keys_button = QPushButton("Keys Bindings")
        self.multiplayer_button = QPushButton("Multi Player")
        self.gametypes_button = QPushButton("Game Types")
        self.about_button = QPushButton("About")
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.dismiss_button = QPushButton("Dismiss")
        
        layout.addWidget(self.stats_button)
        layout.addWidget(self.keys_button)
        layout.addWidget(self.multiplayer_button)
        layout.addWidget(self.gametypes_button)
        layout.addWidget(self.about_button)
        layout.addWidget(separator)
        layout.addWidget(self.dismiss_button)
        
        self.stats_button.clicked.connect(self.show_stats)
        self.keys_button.clicked.connect(self.show_keys)
        self.multiplayer_button.clicked.connect(self.show_multiplayer)
        self.gametypes_button.clicked.connect(self.show_gametypes)
        self.about_button.clicked.connect(self.show_about)
        self.dismiss_button.clicked.connect(self.accept)
        
        self.multiplayer_button.setEnabled(False)
        self.gametypes_button.setEnabled(False)
        
    # Placeholder Slots
    # These will open other specific dialogs later
    @Slot()
    def show_stats(self):
        print("Stats button clicked - not implemented yet")
        
    @Slot()
    def show_keys(self):
        print("Keys button clicked - not implemented yet")

    @Slot()
    def show_multiplayer(self):
        print("Multiplayer button clicked - not implemented yet")

    @Slot()
    def show_gametypes(self):
        print("Game Types button clicked - not implemented yet")
    
    @Slot()
    def show_about(self):
        print("About button clicked - not implemented yet")


# MainWindow
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"PySide6 Tetris (from Tcl)")
        self.game_state = "Init"
        self.current_interval = 500
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
        # Use the new NextPieceWidget
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
        )  # Add widget
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
        self.options_button.clicked.connect(self.show_options_dialog)
        self.game_board.update_score_signal.connect(self.update_score_display)
        self.game_board.update_level_signal.connect(self.update_level_display)
        self.game_board.update_rows_signal.connect(self.update_rows_display)
        self.game_board.game_over_signal.connect(self.handle_game_over)
        # Connect GameBoard signal to NextPieceWidget slot
        self.game_board.next_piece_ready_signal.connect(
            self.next_piece_display.set_next_piece
        )
        
        self.options_dialog = None

        self.reset_game()

    @Slot()
    def show_options_dialog(self):
        dialog = OptionsDialog(self)
        dialog.exec()
        
    @Slot()
    def game_step(self):
        if self.game_state == "Playing" and not self.game_board.is_paused:
            self.game_board.slide_down()

    @Slot()
    def toggle_game_state(self):
        # State logic remains the same as before
        if self.game_state == "Init" or self.game_state == "GameOver":
            self.game_state = "Playing"
            self.start_pause_button.setText("Pause")
            self.update_timer_interval()
            self.game_board.start_game()  # This now sets up first piece AND next piece
            self.fall_timer.start(self.current_interval)
        elif self.game_state == "Playing":
            # Pause the game
            self.game_state = "Paused"
            self.start_pause_button.setText("Resume")
            self.game_board.pause_game()
            self.fall_timer.stop()
        elif self.game_state == "Paused":
            # Resume the game
            self.game_state = "Playing"
            self.start_pause_button.setText("Pause")
            self.game_board.resume_game()
            self.fall_timer.start(self.current_interval)

    @Slot()
    def reset_game(self):
        self.fall_timer.stop()
        self.game_state = "Init"
        self.start_pause_button.setText("Start")
        self.game_board.reset_board()  # Resets board and emits initial signals

    @Slot()
    def handle_game_over(self):
        self.fall_timer.stop()
        self.game_state = "GameOver"
        self.start_pause_button.setText("Game Over")
        print("Game Over!")

    @Slot(int)
    def update_score_display(self, score):
        self.score_value.setText(str(score))

    @Slot(int)
    def update_level_display(self, level):
        self.level_value.setText(str(level))
        self.update_timer_interval()

    @Slot(int)
    def update_rows_display(self, rows):
        self.rows_value.setText(str(rows))

    def update_timer_interval(self):
        base_interval = 500
        level_factor = base_interval / 20
        new_interval = base_interval - (level_factor * self.game_board.level)
        self.current_interval = max(50, int(new_interval))
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
