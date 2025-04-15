import sys
from PySide6.QtWidgets import(
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

# Constants (derived from Tcl script's setup)
BOARD_WIDTH_BLOCKS = 10
BOARD_HEIGHT_BLOCKS = 30
BLOCK_SIZE_PX = 15  # Default block size from Tcl script
BOARD_WIDTH_PX = BOARD_WIDTH_BLOCKS * BLOCK_SIZE_PX
BOARD_HEIGHT_PX = BOARD_HEIGHT_BLOCKS * BLOCK_SIZE_PX


class GameBoard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BOARD_WIDTH_PX, BOARD_HEIGHT_PX)
        self.setStyleSheet("background-color: grey; border: 1px solid black;")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # To receive key events
        
        # -- Game State Placeholder ---
        # This will hold the state of the board (fallen pieces)
        # In Tcl: represented by the 'block' array
        self.board_state = [[0 for _ in range(BOARD_WIDTH_BLOCKS)] for _ in range(BOARD_HEIGHT_BLOCKS)]
        # Add state for the current piece, its position, rotation, color, etc.
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # -- Draw Grid Lines (Optional, like Tcl 'back' lines) --
        # painter.setPen(QColor("lightgrey"))
        # for x in range(0, BOARD_WIDTH_PX, BLOCK_SIZE_PX):
        #     painter.drawLine(x, 0, x, BOARD_HEIGHT_PX)
        # for y in range(0, BOARD_HEIGHT_PX, BLOCK_SIZE_PX):
        #     painter.drawLine(0, y, BOARD_WIDTH_PX, y)

        # --- Draw Fallen Pieces (Structure) ---
        # Iterate through self.board_state and draw filled rectangles
        # for occupied blocks. In Tcl: items tagged 'struc'

        # --- Draw Current Piece ---
        # Get current piece's shape, position, color and draw its blocks
        # In Tcl: items tagged 'piece'

        # --- Draw Shadow Piece (Optional) ---
        # Calculate where the shadow would be and draw outlines or filled blocks
        # In Tcl: uses the 'shadow' canvas and tags
        
    def update_board(self):
        self.update()
        
    def reset_board(self):
        self.board_state = [[0 for _ in range(BOARD_WIDTH_BLOCKS)] for _ in range(BOARD_HEIGHT_BLOCKS)]
        self.update_board()
        
    def start_game(self):
        self.setFocus()
        
    def pause_game(self):
        pass
    
    def resume_game(self):
        self.setFocus()
        
        
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PySide6 Tetris")
        
        self.game_state = "Init"
        
        self.fall_timer = QTimer(self)
        self.fall_timer.timeout.connect(self.game_step)
        self.current_interval = 500
        
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        self.title_label = QLabel("Tetris v1.0")
        self.next_piece_label = QLabel("Next Object")
        self.next_piece_display = QFrame()
        self.next_piece_display.setFixedSize(BLOCK_SIZE_PX * 4 + 10, BLOCK_SIZE_PX * 2 + 10)
        self.next_piece_display.setStyleSheet("background-color: lightgrey; border: 1px solid black;")
        
        info_layout = QGridLayout()
        self.score_label = QLabel("Score:")
        self.score_value = QLabel("0")
        self.level_label = QLabel("Level:")
        self.level_value = QLabel("0")
        self.rows_label = QLabel("Rows:")
        self.rows_value = QLabel("0")
        info_layout.addWidget(self.score_label, 0, 0)
        info_layout.addWidget(self.score_value, 0, 1)
        info_layout.addWidget(self.level_label, 1, 0)
        info_layout.addWidget(self.level_value, 1, 1)
        info_layout.addWidget(self.rows_label, 2, 0)
        info_layout.addWidget(self.rows_value, 2, 1)
        
        self.start_pause_button = QPushButton("Start")
        self.reset_button = QPushButton("Reset")
        self.options_button = QPushButton("Options")
        self.quit_button = QPushButton("Quit")
        
        left_layout.addWidget(self.title_label)
        left_layout.addWidget(self.next_piece_label)
        left_layout.addWidget(self.next_piece_display, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addLayout(info_layout)
        left_layout.addWidget(self.start_pause_button)
        left_layout.addWidget(self.reset_button)
        left_layout.addWidget(self.options_button)
        left_layout.addWidget(self.quit_button)
        left_layout.addStretch()
        
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        self.shadow_display = QFrame()
        self.shadow_display.setFixedHeight(BLOCK_SIZE_PX)
        self.shadow_display.setStyleSheet("background-color: darkgrey; border: 1px solid black;")
        
        self.game_board = GameBoard()
        
        right_layout.addWidget(self.game_board)
        right_layout.addWidget(self.shadow_display)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(0)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.setCentralWidget(central_widget)
        
        self.start_pause_button.clicked.connect(self.toggle_game_state)
        self.reset_button.clicked.connect(self.reset_game)
        self.quit_button.clicked.connect(QApplication.instance().quit)
        
        self.reset_game()
        
    @Slot()
    def game_step(self):
        if self.game_state != "Playing":
            return
        
        print("Game Step")  # Placeholder
        self.game_board.update_board()
        
    @Slot()
    def toggle_game_state(self):
        if self.game_state == "Init" or self.game_state == "GameOver":
            self.game_state = "Playing"
            self.start_pause_button.setText("Pause")
            self.game_board.start_game()
            self.fall_timer.start(self.current_interval)
        elif self.game_state == "Playing":
            self.game_state = "Paused"
            self.start_pause_button.setText("Resume")
            self.game_board.pause_game()
            self.fall_timer.stop()
        elif self.game_state == "Paused":
            self.game_state = "Playing"
            self.start_pause_button.setText("Pause")
            self.game_board.resume_game()
            self.fall_timer.start(self.current_interval)
            
    @Slot()
    def reset_game(self):
        self.fall_timer.stop()
        self.game_state = "Init"
        self.start_pause_button.setText("Start")
        self.score_value.setText("0")
        self.level_value.setText("0")
        self.rows_value.setText("0")
        self.game_board.reset_board()
        print("Game Reset")  # Placeholder
        
    def keyPressEvent(self, event):
        if self.game_state != "Playing":
            event.ignore() # Don't handle keys if not playing
            return
        
        key = event.key()
        
        if key == Qt.Key.Key_Left:
            # self.game_logic.move_left()
            print("Key Left") # Placeholder
            self.game_board.update_board()
        elif key == Qt.Key.Key_Right:
            # self.game_logic.move_right()
            print("Key Right") # Placeholder
            self.game_board.update_board()
        elif key == Qt.Key.Key_Up: # Corresponds to Tcl 'Rotate Left'
            # self.game_logic.rotate_left()
            print("Key Up (Rotate Left)") # Placeholder
            self.game_board.update_board()
        elif key == Qt.Key.Key_Down: # Corresponds to Tcl 'Rotate Right'
            # self.game_logic.rotate_right()
            print("Key Down (Rotate Right)") # Placeholder
            self.game_board.update_board()
        elif key == Qt.Key.Key_Space: # Corresponds to Tcl 'Drop'
            # self.game_logic.drop_piece()
            print("Key Space (Drop)") # Placeholder
            # Drop usually triggers an immediate game step or sequence
            self.game_step() # Or a dedicated drop handler
        # Add other keys if needed (e.g., Enter for Slide in Tcl)
        else:
            super().keyPressEvent(event) # Pass unhandled keys up


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())