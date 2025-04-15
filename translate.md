| Tcl/Tk Concept | PySide6 (Qt) Equivalent | Notes |
| -------------- | ----------------------- | ----- |
| `wish` (Tk application) | `QApplication` | The main application object.
|`.` (main window) | `QMainWindow` or `QWidget` | The main application window. `QMainWindow` provides standard features like menus and status bars.
| `frame` | `QFrame` or `QWidget` | Container widgets.
| `label` | `QLabel` | Displays text or images.
| `button` | `QPushButton` | Clickable buttons.
| `entry` | `QLineEdit` | Single-line text input.
| `checkbutton` | `QCheckBox` | Checkable box.
| `listbox` | `QListWidget` | Displays a list of items.
| `canvas` | `QGraphicsView` + `QGraphicsScene` or `QWidget` + `QPainter` | For drawing the game board and pieces. `QGraphicsView` is often better for managing many items.
| `toplevel` | `QDialog` or `QWidget` | Secondary windows.
| `scale` | `QSlider` | Slider control (used for multiplayer opponent height).
| `grid` (layout) | `QGridLayout`, `QVBoxLayout`, `QHBoxLayout` | Qt layout managers arrange widgets automatically.
| `bind` (event handling) | Signals and Slots | Connect widget signals (e.g., clicked(), keyPressed()) to custom methods (slots).
| `after` (timers) | `QTimer` | Used to schedule events like the piece falling (Fall) or rows growing (GrowRows).
| `proc` (procedures) | Python functions or class methods | Define the logic.
| `variable`, `array` | Python variables, lists, dictionaries, class attributes | Store game state.
| `socket` (networking) | `QTcpServer`, `QTcpSocket` | Classes for handling TCP network connections.
| `namespace` | Python classes and modules | Organize the code.
| `canvas` `create_`* | `QGraphicsScene`::addRect(), `QGraphicsScene`::addLine() etc. or `QPainter` drawing methods | Creating visual elements.
| `canvas` `itemconfig`/`move` | `QGraphicsItem` methods (setPos, setBrush, etc.) or redrawing with `QPainter` | Modifying visual elements.