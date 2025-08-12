from PySide6.QtWidgets import QApplication
from gui import TradingBotWindow

if __name__ == "__main__":
    app = QApplication([])
    window = TradingBotWindow()
    window.show()
    app.exec()