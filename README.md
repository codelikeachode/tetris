This is a PySide6 port from a tetris tcl script

## TODO:
Currently a bug where the bottom most row doesn't clear when it is supposed to. Most likely cause is the repaint triggered by `self.update()`. 