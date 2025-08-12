import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QCheckBox,
    QFormLayout,
)
from PySide6.QtCore import Qt, QThread, Signal
import time


# --- Worker Thread to run the bot ---
class BotWorker(QThread):
    log_signal = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True

    def run(self):
        # Simulate bot work, replace with your trading bot main loop
        self.log_signal.emit("Bot started with config:\n" + str(self.config))
        counter = 0
        while self.running:
            self.log_signal.emit(f"Processing... {counter}")
            counter += 1
            time.sleep(1)
        self.log_signal.emit("Bot stopped.")

    def stop(self):
        self.running = False


# --- Main GUI ---
class TradingBotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Bot")
        self.setGeometry(200, 200, 900, 600)

        main_layout = QHBoxLayout(self)

        # Left: Log Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output, 2)

        # Right: Config Panel
        config_layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.api_key = QLineEdit()
        self.api_secret = QLineEdit()
        self.api_secret.setEchoMode(QLineEdit.EchoMode.Password)

        self.exchange_name = QLineEdit()
        self.symbol = QLineEdit()
        self.leverage = QLineEdit()
        self.margin_percent = QLineEdit()
        self.timeframe_seconds = QLineEdit()
        self.contract_num = QLineEdit()

        self.fixed_amount = QCheckBox("Fixed amount?")
        self.fixed_amount.stateChanged.connect(self.toggle_fixed_amount)

        form_layout.addRow("API Key:", self.api_key)
        form_layout.addRow("API Secret:", self.api_secret)
        form_layout.addRow("Exchange:", self.exchange_name)
        form_layout.addRow("Symbol:", self.symbol)
        form_layout.addRow("Leverage:", self.leverage)
        form_layout.addRow("Margin %:", self.margin_percent)
        form_layout.addRow("Timeframe (sec):", self.timeframe_seconds)
        form_layout.addRow("Contract Num:", self.contract_num)
        form_layout.addRow("", self.fixed_amount)

        config_layout.addLayout(form_layout)

        # Start / Stop Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_bot)
        self.stop_btn.clicked.connect(self.stop_bot)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        config_layout.addLayout(btn_layout)

        main_layout.addLayout(config_layout, 1)

        # --- Require all fields ---
        def validate_fields():
            all_filled = all(
                [
                    self.api_key.text().strip(),
                    self.api_secret.text().strip(),
                    self.exchange_name.text().strip(),
                    self.symbol.text().strip(),
                    self.leverage.text().strip(),
                    self.margin_percent.text().strip(),
                    self.timeframe_seconds.text().strip(),
                    self.contract_num.text().strip(),
                ]
            )
            self.start_btn.setEnabled(all_filled)

        # Connect text change signals
        for field in [
            self.api_key,
            self.api_secret,
            self.exchange_name,
            self.symbol,
            self.leverage,
            self.margin_percent,
            self.timeframe_seconds,
            self.contract_num,
        ]:
            field.textChanged.connect(validate_fields)

        self.bot_thread = None

    def toggle_fixed_amount(self):
        if self.fixed_amount.isChecked():
            self.leverage.setEnabled(False)
            self.margin_percent.setEnabled(False)
            self.contract_num.setEnabled(True)
        else:
            self.leverage.setEnabled(True)
            self.margin_percent.setEnabled(True)
            self.contract_num.setEnabled(False)

    def start_bot(self):
        config = {
            "API_KEY": self.api_key.text(),
            "API_SECRET": self.api_secret.text(),
            "EXCHANGE_NAME": self.exchange_name.text(),
            "SYMBOL": self.symbol.text(),
            "LEVERAGE": (
                float(self.leverage.text())
                if not self.fixed_amount.isChecked()
                else None
            ),
            "MARGIN_PERCENT": (
                float(self.margin_percent.text())
                if not self.fixed_amount.isChecked()
                else None
            ),
            "TIMEFRAME_SECONDS": int(self.timeframe_seconds.text()),
            "CONTRACT_NUM": (
                int(self.contract_num.text()
                    ) if self.fixed_amount.isChecked() else None
            ),
        }

        # Freeze config while running
        for widget in [
            self.api_key,
            self.api_secret,
            self.exchange_name,
            self.symbol,
            self.leverage,
            self.margin_percent,
            self.timeframe_seconds,
            self.contract_num,
            self.fixed_amount,
        ]:
            widget.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.bot_thread = BotWorker(config)
        self.bot_thread.log_signal.connect(self.update_log)
        self.bot_thread.start()

    def stop_bot(self):
        if self.bot_thread:
            self.bot_thread.stop()
            self.bot_thread.wait()

        # Unfreeze config
        for widget in [
            self.api_key,
            self.api_secret,
            self.exchange_name,
            self.symbol,
            self.leverage,
            self.margin_percent,
            self.timeframe_seconds,
            self.contract_num,
            self.fixed_amount,
        ]:
            widget.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_log(self, message):
        self.log_output.append(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = TradingBotGUI()
    gui.show()
    sys.exit(app.exec())
