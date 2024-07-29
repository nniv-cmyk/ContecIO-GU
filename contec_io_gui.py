import sys
import logging
from typing import List, Callable, Optional
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout, QTextEdit
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt, QTimer
import ctypes
import cdio

# Constants
DEVICE_NAME = "DIO000"
NUM_BITS_PER_PORT = 8
BUTTON_SIZE = 30
UPDATE_INTERVAL = 1000  # ms
MAX_REINIT_ATTEMPTS = 3

class DIODevice:
    def __init__(self):
        self.dio_id: Optional[ctypes.c_short] = None
        self.err_str = ctypes.create_string_buffer(256)

    def initialize(self) -> bool:
        self.dio_id = ctypes.c_short()
        lret = cdio.DioInit(DEVICE_NAME.encode(), ctypes.byref(self.dio_id))
        if lret != cdio.DIO_ERR_SUCCESS:
            self._handle_error(lret, "Init Error")
            return False
        return True

    def exit(self) -> None:
        if self.dio_id is not None:
            lret = cdio.DioExit(self.dio_id)
            if lret != cdio.DIO_ERR_SUCCESS:
                self._handle_error(lret, "Exit Error")
            self.dio_id = None

    def get_max_ports(self) -> int:
        if self.dio_id is None:
            raise RuntimeError("Device not initialized")
        num_ports = ctypes.c_short()
        lret = cdio.DioGetMaxPorts(self.dio_id, ctypes.byref(num_ports), None)
        if lret != cdio.DIO_ERR_SUCCESS:
            self._handle_error(lret, "Error Getting Ports")
        return num_ports.value

    def read_bit(self, bit_no: int) -> int:
        if self.dio_id is None:
            raise RuntimeError("Device not initialized")
        io_data = ctypes.c_ubyte()
        lret = cdio.DioInpBit(self.dio_id, ctypes.c_short(bit_no), ctypes.byref(io_data))
        if lret != cdio.DIO_ERR_SUCCESS:
            self._handle_error(lret, f"Read Error on bit {bit_no}")
        return io_data.value

    def write_bit(self, bit_no: int, value: int) -> None:
        if self.dio_id is None:
            raise RuntimeError("Device not initialized")
        lret = cdio.DioOutBit(self.dio_id, ctypes.c_short(bit_no), ctypes.c_ubyte(value))
        if lret != cdio.DIO_ERR_SUCCESS:
            self._handle_error(lret, f"Write Error on bit {bit_no}")

    def _handle_error(self, lret: int, prefix: str) -> None:
        cdio.DioGetErrorString(lret, self.err_str)
        error_message = f"{prefix}: {self.err_str.value.decode('sjis')}"
        logging.error(error_message)
        raise RuntimeError(error_message)

class ContecIODemo(QWidget):
    def __init__(self):
        super().__init__()
        self.device = DIODevice()
        self.bit_buttons: List[QPushButton] = []
        self.num_ports = 0
        self.reinit_attempts = 0
        self.bit_states = []  # Initialize as an empty list
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Contec I/O GUI')
        layout = QVBoxLayout()

        self.status_label = QLabel('Status: Not Initialized', self)
        layout.addWidget(self.status_label)

        self.init_button = QPushButton('Initialize', self)
        self.init_button.clicked.connect(self.initialize_device)
        layout.addWidget(self.init_button)

        self.exit_button = QPushButton('Exit', self)
        self.exit_button.clicked.connect(self.exit_device)
        layout.addWidget(self.exit_button)

        self.off_button = QPushButton('Turn All Off', self)
        self.off_button.clicked.connect(self.turn_all_off)
        layout.addWidget(self.off_button)

        self.grid_layout = QGridLayout()
        layout.addLayout(self.grid_layout)

        self.log = QTextEdit(self)
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logging_handler = logging.StreamHandler(stream=sys.stdout)
        logging_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logging_handler)

        # Set up timer for periodic updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_bit_buttons)

    def initialize_device(self):
        try:
            if self.device.initialize():
                self.num_ports = self.device.get_max_ports()
                self.bit_states = [0] * (self.num_ports * NUM_BITS_PER_PORT)  # Initialize bit states
                self.status_label.setText('Status: Initialized')
                logging.info('Device Initialized')
                self.create_bit_buttons()
                self.update_timer.start(UPDATE_INTERVAL)
                self.reinit_attempts = 0
                self.set_buttons_enabled(True)
            else:
                self.status_label.setText('Status: Initialization Failed')
        except RuntimeError as e:
            self.status_label.setText(f'Status: {str(e)}')

    def create_bit_buttons(self):
        self.bit_buttons = []
        for i in range(self.num_ports * NUM_BITS_PER_PORT):
            button = QPushButton(f'{i}', self)
            button.setAutoFillBackground(True)
            button.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
            button.clicked.connect(self.make_toggle_bit_function(i))
            button.setToolTip(f"Toggle bit {i}")
            self.grid_layout.addWidget(button, i // NUM_BITS_PER_PORT, i % NUM_BITS_PER_PORT)
            self.bit_buttons.append(button)
        self.update_bit_buttons()

    def make_toggle_bit_function(self, bit_no: int) -> Callable[[], None]:
        def toggle_bit():
            try:
                new_value = 1 if self.bit_states[bit_no] == 0 else 0
                self.device.write_bit(bit_no, new_value)
                self.bit_states[bit_no] = new_value
                status_message = f'Bit {bit_no} {"On" if new_value else "Off"}'
                self.status_label.setText(f'Status: {status_message}')
                logging.info(status_message)
                self.update_button_color(bit_no, new_value)
            except RuntimeError as e:
                self.handle_device_error(str(e))
        return toggle_bit

    def update_bit_buttons(self):
        if not self.bit_buttons:
            return
        try:
            for i, button in enumerate(self.bit_buttons):
                # Read the actual state of the bit from the device
                current_value = self.device.read_bit(i)
                # Update the internal state for consistency
                self.bit_states[i] = current_value
                # Update the button color based on the current value
                self.update_button_color(i, current_value)
        except RuntimeError as e:
            self.handle_device_error(str(e))


    def update_button_color(self, bit_no: int, value: int):
        button = self.bit_buttons[bit_no]
        color = Qt.red if value else Qt.green
        palette = button.palette()
        palette.setColor(QPalette.Button, color)
        button.setPalette(palette)
        button.update()

    def turn_all_off(self):
        try:
            for i in range(self.num_ports * NUM_BITS_PER_PORT):
                self.device.write_bit(i, 0)
                self.bit_states[i] = 0
            self.update_bit_buttons()
            logging.info("All bits turned off")
        except RuntimeError as e:
            self.handle_device_error(str(e))

    def exit_device(self):
        self.update_timer.stop()
        self.device.exit()
        self.status_label.setText('Status: Exited')
        logging.info('Device Exited')
        self.set_buttons_enabled(False)

    def handle_device_error(self, error_message: str):
        self.status_label.setText(f'Status: Error - {error_message}')
        logging.error(f"Device error: {error_message}")
        self.update_timer.stop()
        self.set_buttons_enabled(False)
        
        if self.reinit_attempts < MAX_REINIT_ATTEMPTS:
            self.reinit_attempts += 1
            logging.info(f"Attempting to reinitialize device (attempt {self.reinit_attempts})")
            self.initialize_device()
        else:
            logging.error("Max reinitialization attempts reached. Please check the device connection.")

    def set_buttons_enabled(self, enabled: bool):
        self.off_button.setEnabled(enabled)
        for button in self.bit_buttons:
            button.setEnabled(enabled)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ContecIODemo()
    ex.show()
    sys.exit(app.exec_())