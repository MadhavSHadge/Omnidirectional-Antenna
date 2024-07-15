import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QMessageBox, QFileDialog, QLabel, QLineEdit, QRadioButton, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pyvisa
from datetime import datetime

rfi_file_path = '12_july.rfi'

class LiveSpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Live Spectrum")
        self.ax.set_xlabel("Frequency (MHz)")
        self.ax.set_ylabel("Amplitude (dBm)")

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.data = None

    def update_data(self, data):
        self.data = data
        self.plot_data()

    def plot_data(self):
        self.ax.clear()
        if self.data is not None:
            self.ax.plot(self.data)
        self.canvas.draw()

class SpectrumAnalyzerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.fig, self.ax = Figure(figsize=(10, 6)), None
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

        # Buttons
        self.pause_button = QPushButton('Pause')
        self.pause_button.clicked.connect(self.pause_updates)
        self.resume_button = QPushButton('Resume')
        self.resume_button.clicked.connect(self.resume_updates)
        self.save_image_button = QPushButton('Save Image')
        self.save_image_button.clicked.connect(self.save_plot_image)
        self.reset_params_button = QPushButton('Reset Parameters')
        self.reset_params_button.clicked.connect(self.reset_parameters)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.save_image_button)
        button_layout.addWidget(self.reset_params_button)
        layout.addLayout(button_layout)

        # PyVISA setup for Spectrum Analyzer
        self.rm = pyvisa.ResourceManager()
        try:
            self.sa = self.rm.open_resource('TCPIP0::192.168.8.36::inst0::INSTR')
        except pyvisa.VisaIOError as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to spectrum analyzer: {str(e)}")
            return

        # Initial state
        self.pause = False

        # Timer for updating plot
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)  # Update plot every second

    def update_plot(self):
        if not self.pause:
            try:
                # Query spectrum analyzer for data
                trace_data = self.sa.query_ascii_values('TRACE:DATA? TRACE1')
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                center_freq = float(self.sa.query(':SENSE:FREQ:CENTER?')) / 1e6
                span = float(self.sa.query(':SENSE:FREQ:SPAN?')) / 1e9
                rbw = float(self.sa.query(':SENSE:BAND:RES?')) / 1e3
                vbw = float(self.sa.query(':SENSE:BAND:VID?')) / 1e3
                ref_level = float(self.sa.query(':DISP:WIND:TRAC:Y:RLEV?'))
                sweep_time_sec = float(self.sa.query(':SWE:TIME?'))
                amp_div = float(self.sa.query(':DISP:WIND:TRAC:Y:SCAL?'))
                att = float(self.sa.query(':INP:ATT?'))
                avg_num = float(self.sa.query(':AVER:COUN?'))
                sweep_time_ms = sweep_time_sec * 1000.0

                # Write data to file
                with open(rfi_file_path, 'a') as file:
                    file.write(f"{current_time},{center_freq:.6f},{span:.9f},{rbw:.3f},{vbw:.3f},{ref_level},{sweep_time_ms},{amp_div},{att},{avg_num},*\n")
                    file.write(','.join(map(lambda x: f"{x:.2f}", trace_data)) + ',@\n\n')

                # Update plot
                if self.ax is None:
                    self.ax = self.fig.add_subplot(111)
                self.ax.clear()
                self.ax.plot(trace_data)
                self.ax.set_xlabel('Frequency (MHz)')
                self.ax.set_ylabel('Amplitude (dBm)')
                self.ax.set_title('Live Spectrum Monitor')
                self.ax.grid(True)
                self.canvas.draw()

            except Exception as e:
                print(f"Error updating plot: {e}")
                QMessageBox.critical(self, "Error", f"Error updating plot: {str(e)}")

    def pause_updates(self):
        self.pause = True

    def resume_updates(self):
        self.pause = False
        self.update_plot()

    def save_plot_image(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Plot Image", "", "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)")
            if file_path:
                self.fig.savefig(file_path)
                QMessageBox.information(self, "Saved", "Plot image saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving plot image: {str(e)}")

    def reset_parameters(self):
        try:
            # Reset the spectrum analyzer to default settings
            self.sa.write("*RST")

            # Default values for parameters
            default_center_freq = 100e6  # 100 MHz
            default_span = 1e9  # 1 GHz
            default_rbw = 100e3  # 100 kHz
            default_vbw = 100e3  # 100 kHz
            default_ref_level = -10.0  # dBm
            default_amp_div = 10.0  # dB
            default_att = 0.0  # dB
            default_avg_num = 1.0

            # Set default values on spectrum analyzer
            self.sa.write(f":SENSE:FREQ:CENTER {default_center_freq}")
            self.sa.write(f":SENSE:FREQ:SPAN {default_span}")
            self.sa.write(f":SENSE:BAND:RES {default_rbw}")
            self.sa.write(f":SENSE:BAND:VID {default_vbw}")
            self.sa.write(f":DISP:WIND:TRAC:Y:RLEV {default_ref_level}")
            self.sa.write(f":DISP:WIND:TRAC:Y:SCAL {default_amp_div}")
            self.sa.write(f":INP:ATT {default_att}")
            self.sa.write(f":AVER:COUN {default_avg_num}")

            QMessageBox.information(self, "Success", "Parameters reset to default values.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset parameters: {str(e)}")

class Form(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RFI Monitoring Server")
        self.resize(900, 600)
        self.create_widgets()

    def create_widgets(self):
        # Application Settings
        application_settings_group = QGroupBox("APPLICATION SETTINGS")
        application_settings_layout = QVBoxLayout()
        application_settings_layout.setSpacing(0)
        application_settings_layout.setContentsMargins(2, 2, 2, 2)

        spectrum_dump_radio = QRadioButton("Spectrum Dump with Antenna Switching")
        all_antennae_checkbox = QCheckBox("All Antennae in Single Plot")
        normal_spectrum_dump_radio = QRadioButton("Normal Spectrum Dump Only")

        # Buttons
        load_setting_button = QPushButton("Load Setting File")
        load_setting_button.clicked.connect(self.load_setting_file)
        save_setting_button = QPushButton("Save Setting File")

        # Add widgets to the layout
        application_settings_layout.addWidget(spectrum_dump_radio)
        application_settings_layout.addWidget(all_antennae_checkbox)
        application_settings_layout.addWidget(normal_spectrum_dump_radio)

        # Horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(load_setting_button)
        button_layout.addWidget(save_setting_button)

        application_settings_layout.addLayout(button_layout)
        application_settings_group.setLayout(application_settings_layout)

        # Spectrum Analyzer Settings
        spectrum_analyzer_settings_group = QGroupBox("SPECTRUM ANALYZER SETTINGS")
        spectrum_analyzer_settings_layout = QGridLayout()
        spectrum_analyzer_settings_layout.setHorizontalSpacing(5)
        spectrum_analyzer_settings_layout.setVerticalSpacing(3)

        # Creating spinboxes, labels and comboboxes
        self.center_spinbox = self.create_spinbox(0, 1000, 750, "Center Frequency (MHz):", spectrum_analyzer_settings_layout, 0, 0)
        self.span_spinbox = self.create_spinbox(0, 1000, 750, "Span (MHz):", spectrum_analyzer_settings_layout, 1, 0)
        self.rbw_combobox = self.create_combobox(["3", "10", "30", "100", "300", "1000"], "RBW (kHz):", spectrum_analyzer_settings_layout, 0, 2)
        self.vbw_combobox = self.create_combobox(["3", "10", "30", "100", "300", "1000"], "VBW (kHz):", spectrum_analyzer_settings_layout, 1, 2)
        self.ref_level_spinbox = self.create_spinbox(-100, 30, -30, "Reference Level (dBm):", spectrum_analyzer_settings_layout, 2, 0)
        self.amp_div_spinbox = self.create_spinbox(0, 20, 10, "Amplitude Division (dB):", spectrum_analyzer_settings_layout, 2, 2)
        self.att_combobox = self.create_combobox(["0", "5", "10", "15", "20", "25", "30"], "Attenuation (dB):", spectrum_analyzer_settings_layout, 3, 0)
        self.avg_number_spinbox = self.create_spinbox(0, 100, 1, "Average Number:", spectrum_analyzer_settings_layout, 3, 2)
        self.sweep_time_spinbox = self.create_spinbox(0, 1000, 500, "Sweep Time (ms):", spectrum_analyzer_settings_layout, 4, 0)

        spectrum_analyzer_settings_group.setLayout(spectrum_analyzer_settings_layout)

        # Plot Settings
        plot_settings_group = QGroupBox("PLOT SETTINGS")
        plot_settings_layout = QGridLayout()
        plot_settings_layout.setHorizontalSpacing(5)
        plot_settings_layout.setVerticalSpacing(3)

        self.ylim_upper_spinbox = self.create_spinbox(-200, 30, 10, "Y-axis Upper Limit:", plot_settings_layout, 0, 0)
        self.ylim_lower_spinbox = self.create_spinbox(-200, 30, -100, "Y-axis Lower Limit:", plot_settings_layout, 0, 2)

        plot_settings_group.setLayout(plot_settings_layout)

        # Spectrum Canvas
        spectrum_canvas_group = QGroupBox("SPECTRUM CANVAS")
        spectrum_canvas_layout = QVBoxLayout()
        spectrum_canvas = SpectrumAnalyzerApp()
        spectrum_canvas_layout.addWidget(spectrum_canvas)
        spectrum_canvas_group.setLayout(spectrum_canvas_layout)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(application_settings_group)
        main_layout.addWidget(spectrum_analyzer_settings_group)
        main_layout.addWidget(plot_settings_group)
        main_layout.addWidget(spectrum_canvas_group)

        self.setLayout(main_layout)

    def create_spinbox(self, min_value, max_value, default_value, label_text, layout, row, col):
        label = QLabel(label_text)
        spinbox = QDoubleSpinBox()
        spinbox.setRange(min_value, max_value)
        spinbox.setValue(default_value)
        spinbox.setSingleStep(1)
        layout.addWidget(label, row, col)
        layout.addWidget(spinbox, row, col + 1)
        return spinbox

    def create_combobox(self, options, label_text, layout, row, col):
        label = QLabel(label_text)
        combobox = QComboBox()
        combobox.addItems(options)
        layout.addWidget(label, row, col)
        layout.addWidget(combobox, row, col + 1)
        return combobox

    def load_setting_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Setting File", "", "All Files (*);;Text Files (*.txt)", options=options)
        if file_name:
            # Load and parse settings from the file
            pass

    def save_setting_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Setting File", "", "All Files (*);;Text Files (*.txt)", options=options)
        if file_name:
            # Save current settings to the file
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = Form()
    form.show()
    sys.exit(app.exec_())
