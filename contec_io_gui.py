import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout, QMessageBox
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt
import ctypes
import cdio

class ContecIODemo(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Contec I/O GUI')
        self.layout = QVBoxLayout()

        self.status_label = QLabel('Status: Not Initialized', self)
        self.layout.addWidget(self.status_label)

        self.init_button = QPushButton('Initialize', self)
        self.init_button.clicked.connect(self.initialize_device)
        self.layout.addWidget(self.init_button)

        self.exit_button = QPushButton('Exit', self)
        self.exit_button.clicked.connect(self.exit_device)
        self.layout.addWidget(self.exit_button)

        self.off_button = QPushButton('Turn All Off', self)
        self.off_button.clicked.connect(self.turn_all_off)
        self.layout.addWidget(self.off_button)

        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.setLayout(self.layout)

    def initialize_device(self):
        self.dio_id = ctypes.c_short()
        self.err_str = ctypes.create_string_buffer(256)

        dev_name = "DIO000"
        lret = cdio.DioInit(dev_name.encode(), ctypes.byref(self.dio_id))
        if lret == cdio.DIO_ERR_SUCCESS:
            self.status_label.setText('Status: Initialized')
            self.create_bit_buttons()
        else:
            cdio.DioGetErrorString(lret, self.err_str)
            self.status_label.setText(f'Status: Init Error {self.err_str.value.decode("sjis")}')

    def create_bit_buttons(self):
        num_ports = ctypes.c_short()
        lret = cdio.DioGetMaxPorts(self.dio_id, ctypes.byref(num_ports), None)
        if lret == cdio.DIO_ERR_SUCCESS:
            self.num_ports = num_ports.value
            self.bit_buttons = []
            for i in range(self.num_ports * 8):  # Assuming 8 bits per port
                button = QPushButton(f'{i}', self)
                button.setAutoFillBackground(True)
                palette = button.palette()
                palette.setColor(QPalette.Button, Qt.green)
                button.setPalette(palette)
                button.setFixedSize(30, 30)
                button.clicked.connect(self.make_toggle_bit_function(i))
                self.grid_layout.addWidget(button, i // 8, i % 8)
                self.bit_buttons.append(button)
            self.update_bit_buttons()
        else:
            cdio.DioGetErrorString(lret, self.err_str)
            self.status_label.setText(f'Status: Error Getting Ports {self.err_str.value.decode("sjis")}')

    def make_toggle_bit_function(self, bit_no):
        def toggle_bit():
            bit_no_c = ctypes.c_short(bit_no)
            io_data = ctypes.c_ubyte()
            lret = cdio.DioInpBit(self.dio_id, bit_no_c, ctypes.byref(io_data))
            if lret != cdio.DIO_ERR_SUCCESS:
                cdio.DioGetErrorString(lret, self.err_str)
                self.status_label.setText(f'Status: Read Error {self.err_str.value.decode("sjis")}')
                return

            new_val = 0 if io_data.value else 1
            io_data = ctypes.c_ubyte(new_val)
            lret = cdio.DioOutBit(self.dio_id, bit_no_c, io_data)
            if lret == cdio.DIO_ERR_SUCCESS:
                self.status_label.setText(f'Status: Bit {bit_no} {"On" if new_val else "Off"}')
                self.update_bit_buttons()
            else:
                cdio.DioGetErrorString(lret, self.err_str)
                self.status_label.setText(f'Status: Write Error {self.err_str.value.decode("sjis")}')
        return toggle_bit

    def update_bit_buttons(self):
        for i in range(self.num_ports * 8):
            bit_no = ctypes.c_short(i)
            io_data = ctypes.c_ubyte()
            lret = cdio.DioInpBit(self.dio_id, bit_no, ctypes.byref(io_data))
            if lret == cdio.DIO_ERR_SUCCESS:
                palette = self.bit_buttons[i].palette()
                color = Qt.red if io_data.value else Qt.green
                palette.setColor(QPalette.Button, color)
                self.bit_buttons[i].setPalette(palette)
            else:
                cdio.DioGetErrorString(lret, self.err_str)
                self.status_label.setText(f'Status: Error Reading Bit {self.err_str.value.decode("sjis")}')

    def turn_all_off(self):
        for i in range(self.num_ports * 8):
            bit_no = ctypes.c_short(i)
            io_data = ctypes.c_ubyte(0)
            lret = cdio.DioOutBit(self.dio_id, bit_no, io_data)
            if lret != cdio.DIO_ERR_SUCCESS:
                cdio.DioGetErrorString(lret, self.err_str)
                self.status_label.setText(f'Status: Error Turning Off Bit {i} {self.err_str.value.decode("sjis")}')
        self.update_bit_buttons()

    def exit_device(self):
        reply = QMessageBox.question(self, 'Message', 'Are you sure you want to exit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            lret = cdio.DioExit(self.dio_id)
            if lret == cdio.DIO_ERR_SUCCESS:
                self.status_label.setText('Status: Exited')
            else:
                cdio.DioGetErrorString(lret, self.err_str)
                self.status_label.setText(f'Status: Exit Error {self.err_str.value.decode("sjis")}')
            QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ContecIODemo()
    ex.show()
    sys.exit(app.exec_())
