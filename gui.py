# gui.py
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QObject, Signal, Slot
from typing import Dict
from trading_bot import TradingBot

# Bridge object to expose a Qt signal for logs and manage the TradingBot
class BotRunner(QObject):
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.bot: TradingBot | None = None

    def start_bot(self, config: Dict):
        # create bot with a callback that emits the Qt signal
        def log_cb(msg: str):
            # emit must be from Python thread-safe emitter
            self.log_signal.emit(msg)

        self.bot = TradingBot(config=config, log_cb=log_cb)
        self.bot.start()

    def stop_bot(self):
        if self.bot:
            self.bot.stop()
            self.bot = None

    def is_running(self) -> bool:
        return self.bot is not None and self.bot.is_running()


class TradingBotWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Bot GUI")
        self.setGeometry(200, 200, 1000, 600)

        main_layout = QHBoxLayout(self)

        # Left - log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output, 2)

        # Right - config panel
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

        # Start/Stop buttons
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_stop)

        config_layout.addWidget(self.start_btn)
        config_layout.addWidget(self.stop_btn)
        main_layout.addLayout(config_layout, 1)

        # Bot runner bridge
        self.runner = BotRunner()
        self.runner.log_signal.connect(self.append_log)

        # require validation of inputs before start
        # simple approach: connect textChanged to a validator
        for w in (
            self.api_key, self.api_secret, self.exchange_name, self.symbol,
            self.leverage, self.margin_percent, self.timeframe_seconds, self.contract_num
        ):
            w.textChanged.connect(self.validate_inputs)
        self.validate_inputs()

    @Slot()
    def validate_inputs(self):
        # if fixed amount is checked, CONTRACT_NUM must be filled; else leverage & margin must be filled
        if self.fixed_amount.isChecked():
            all_filled = all([
                self.api_key.text().strip(), self.api_secret.text().strip(),
                self.exchange_name.text().strip(), self.symbol.text().strip(),
                self.timeframe_seconds.text().strip(), self.contract_num.text().strip()
            ])
        else:
            all_filled = all([
                self.api_key.text().strip(), self.api_secret.text().strip(),
                self.exchange_name.text().strip(), self.symbol.text().strip(),
                self.timeframe_seconds.text().strip(), self.leverage.text().strip(),
                self.margin_percent.text().strip()
            ])
        self.start_btn.setEnabled(all_filled and not self.runner.is_running())

    @Slot()
    def toggle_fixed_amount(self):
        if self.fixed_amount.isChecked():
            self.leverage.setEnabled(False)
            self.margin_percent.setEnabled(False)
            self.contract_num.setEnabled(True)
        else:
            self.leverage.setEnabled(True)
            self.margin_percent.setEnabled(True)
            self.contract_num.setEnabled(False)
        self.validate_inputs()

    @Slot()
    def on_start(self):
        # collect config
        try:
            config = {
                "API_KEY": self.api_key.text().strip(),
                "API_SECRET": self.api_secret.text().strip(),
                "EXCHANGE_NAME": self.exchange_name.text().strip(),
                "SYMBOL": self.symbol.text().strip(),
                "TIMEFRAME_SECONDS": int(self.timeframe_seconds.text().strip()),
                "FIXED_AMOUNT": bool(self.fixed_amount.isChecked()),
            }
            if self.fixed_amount.isChecked():
                config["CONTRACT_NUM"] = int(self.contract_num.text().strip())
            else:
                config["LEVERAGE"] = float(self.leverage.text().strip())
                config["MARGIN_PERCENT"] = float(self.margin_percent.text().strip())
        except Exception as e:
            QMessageBox.critical(self, "Invalid Input", f"Invalid configuration: {e}")
            return

        # disable form while running
        for w in (
            self.api_key, self.api_secret, self.exchange_name, self.symbol,
            self.leverage, self.margin_percent, self.timeframe_seconds, self.contract_num,
            self.fixed_amount
        ):
            w.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.append_log("Starting bot...")
        self.runner.start_bot(config)

    @Slot()
    def on_stop(self):
        self.append_log("Stopping bot...")
        self.runner.stop_bot()
        # re-enable form
        for w in (
            self.api_key, self.api_secret, self.exchange_name, self.symbol,
            self.leverage, self.margin_percent, self.timeframe_seconds, self.contract_num,
            self.fixed_amount
        ):
            w.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)

    @Slot(str)
    def append_log(self, message: str):
        self.log_output.append(message)
        # auto-scroll
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
