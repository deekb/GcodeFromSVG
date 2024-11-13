import sys
import serial
import glob

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal

from ui import Ui_MainWindow  # Import the generated UI code

FINISHED_RESPONSE = "OK"


class SerialCommunicator:
    def __init__(self, port, baudrate=115200):
        self.serial_port = serial.Serial(port, baudrate)

    def send(self, command):
        self.serial_port.reset_output_buffer()
        self.serial_port.reset_input_buffer()
        if not command.endswith("\n"):
            command += "\n"
        self.serial_port.write(command.encode())

    def read(self):
        return self.serial_port.readline().decode().strip()

    def wait_for_ok(self):
        response = ""
        while True:
            response += self.read()
            print(response)
            if FINISHED_RESPONSE in response:
                return response

    def close(self):
        if self.serial_port.is_open:
            self.serial_port.close()

class GCodeUploader(QThread):
    progress_signal = pyqtSignal(str)

    def __init__(self, serial_communicator, file_path):
        super().__init__()
        self.serial_communicator = serial_communicator
        self.file_path = file_path

    def run(self):
        with open(self.file_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                self.serial_communicator.send(line)
                received = self.serial_communicator.wait_for_ok()
                self.progress_signal.emit(f"Received: {received}")


class SerialApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)  # This sets up the layout from the .ui file

        self.serial_communicator: SerialCommunicator | None = None
        self.uploader_thread = None

        # Connect signals and slots
        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.sendButton.clicked.connect(self.send_command)
        self.ui.homeButton.clicked.connect(self.send_home_command)
        self.ui.stopButton.clicked.connect(self.send_stop_command)
        self.ui.laserOnButton.clicked.connect(self.laser_on)
        self.ui.laserOffButton.clicked.connect(self.laser_off)
        self.ui.fileButton.clicked.connect(self.upload_file)

        self.ui.commandEntry.returnPressed.connect(self.send_command)

        self.update_ports()

    def show_no_open_port_warning(self):
        QMessageBox.warning(self, "Warning", "Please connect a device first")

    def update_ports(self):
        ports = glob.glob('/dev/ttyUSB*')
        self.ui.portCombo.clear()
        if ports:
            self.ui.portCombo.addItems(ports)
        else:
            self.ui.portCombo.addItem("No ports available")

    def connect(self):
        if self.serial_communicator and self.serial_communicator.serial_port.is_open:
            self.send_stop_command()
            self.serial_communicator.close()
            self.ui.connectButton.setText("Connect")
            self.ui.responseText.append("Disconnected from port\n")
            return

        port = self.ui.portCombo.currentText()
        try:
            self.serial_communicator = SerialCommunicator(port)
            self.ui.responseText.append(f"Connected to port: {self.serial_communicator.serial_port.name}\n")
            self.ui.connectButton.setText("Disconnect")
        except Exception as e:
            self.ui.responseText.append(f"Error: {str(e)}\n")

    def send_command(self):
        if not self.serial_communicator or not self.serial_communicator.serial_port.is_open:
            return self.show_no_open_port_warning()

        command = self.ui.commandEntry.text()
        if command:
            self.serial_communicator.send(command)
            self.ui.responseText.append(f"Sent: {command}")
            response = self.serial_communicator.wait_for_ok()
            self.ui.responseText.append(f"Received: {response}")

        self.ui.commandEntry.clear()

    def send_home_command(self):
        if self.serial_communicator and self.serial_communicator.serial_port.is_open:
            self.serial_communicator.send("G28")
            self.ui.responseText.append("Sent: G28 (Homing)\n")
            response = self.serial_communicator.wait_for_ok()
            self.ui.responseText.append(f"Received: {response}\n")
        else:
            return self.show_no_open_port_warning()

    def send_stop_command(self):
        if self.serial_communicator and self.serial_communicator.serial_port.is_open:
            self.serial_communicator.send("M4\nG28")
            self.ui.responseText.append("Sent: M4 + G28 (Emergency Stop)\n")
            response = self.serial_communicator.wait_for_ok()
            self.ui.responseText.append(f"Received: {response}\n")
        else:
            return self.show_no_open_port_warning()

    def laser_on(self):
        if self.serial_communicator and self.serial_communicator.serial_port.is_open:
            power = self.ui.laserPowerSlider.value()
            self.serial_communicator.send(f"M4 {power}\n")
            self.ui.responseText.append(f"Sent: M4 {power} (Laser On)\n")
            response = self.serial_communicator.wait_for_ok()
            self.ui.responseText.append(f"Received: {response}\n")
        else:
            return self.show_no_open_port_warning()

    def laser_off(self):
        if self.serial_communicator and self.serial_communicator.serial_port.is_open:
            self.serial_communicator.send("M4")
            self.ui.responseText.append("Sent: M4 (Laser Off)\n")
            response = self.serial_communicator.wait_for_ok()
            self.ui.responseText.append(f"Received: {response}\n")
        else:
            return self.show_no_open_port_warning()

    def upload_file(self):
        if not self.serial_communicator or not self.serial_communicator.serial_port.is_open:
            return self.show_no_open_port_warning()

        file_path, _ = QFileDialog.getOpenFileName(self, "Open Gcode File", "", "Gcode Files (*.gcode)")
        if not file_path:
            return

        self.ui.responseText.append(f"Uploading file: {file_path}\n")

        # Ensure previous thread is cleaned up
        if self.uploader_thread is not None and self.uploader_thread.isRunning():
            self.uploader_thread.quit()
            self.uploader_thread.wait()

        # Start the G-code upload in a separate thread
        self.uploader_thread = QThread()
        self.uploader_worker = GCodeUploader(self.serial_communicator, file_path)
        self.uploader_worker.moveToThread(self.uploader_thread)

        self.uploader_thread.started.connect(self.uploader_worker.run)
        self.uploader_worker.progress_signal.connect(self.update_response)
        self.uploader_worker.finished.connect(self.on_upload_finished)  # Improved handling
        self.uploader_worker.finished.connect(self.uploader_worker.deleteLater)
        self.uploader_thread.finished.connect(self.uploader_thread.deleteLater)

        self.uploader_thread.start()

    def on_upload_finished(self):
        self.ui.responseText.append("File upload finished.\n")

    def update_response(self, message):
        self.ui.responseText.append(message)

def apply_dark_theme(app):
    with open("dark.qss", "r") as file:
        qss = file.read()
    app.setStyleSheet(qss)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = SerialApp()
    window.setWindowIcon(QIcon("./device_serial.svg"))
    window.show()
    sys.exit(app.exec_())
