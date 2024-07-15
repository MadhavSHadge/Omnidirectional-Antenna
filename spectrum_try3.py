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
        self.resize(1200, 800)  # Increase the size to accommodate the plot
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
        self.center_spinbox = self.create_spinbox(0, 10000, 1000, " MHz")
        self.span_spinbox = self.create_spinbox(0, 10000, 1000, " MHz")
        self.rbw_combobox = self.create_combobox(["100 Hz", "1 kHz", "10 kHz", "100 kHz", "1 MHz"])
        self.vbw_combobox = self.create_combobox(["100 Hz", "1 kHz", "10 kHz", "100 kHz", "1 MHz"])
        self.reference_level_spinbox = self.create_spinbox(-100, 100, 10, " dBm")
        self.attenuation_spinbox = self.create_spinbox(0, 70, 5, " dB")
        self.sweep_time_spinbox = self.create_double_spinbox(0, 1000, 0.1, " ms")
        self.amp_div_spinbox = self.create_double_spinbox(0, 100, 1, " dB/div")

        # Adding widgets to the layout
        spectrum_analyzer_settings_layout.addWidget(QLabel("Center"), 0, 0)
        spectrum_analyzer_settings_layout.addWidget(self.center_spinbox, 0, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("Span"), 1, 0)
        spectrum_analyzer_settings_layout.addWidget(self.span_spinbox, 1, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("RBW"), 2, 0)
        spectrum_analyzer_settings_layout.addWidget(self.rbw_combobox, 2, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("VBW"), 3, 0)
        spectrum_analyzer_settings_layout.addWidget(self.vbw_combobox, 3, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("Reference Level"), 4, 0)
        spectrum_analyzer_settings_layout.addWidget(self.reference_level_spinbox, 4, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("Attenuation"), 5, 0)
        spectrum_analyzer_settings_layout.addWidget(self.attenuation_spinbox, 5, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("Sweep Time"), 6, 0)
        spectrum_analyzer_settings_layout.addWidget(self.sweep_time_spinbox, 6, 1)
        spectrum_analyzer_settings_layout.addWidget(QLabel("Amp Div"), 7, 0)
        spectrum_analyzer_settings_layout.addWidget(self.amp_div_spinbox, 7, 1)

        spectrum_analyzer_settings_group.setLayout(spectrum_analyzer_settings_layout)

        # Antenna Control Settings
        antenna_control_group = QGroupBox("ANTENNA CONTROL SETTINGS")
        antenna_control_layout = QVBoxLayout()

        antenna_path_settings_group = QGroupBox("Antenna Path Settings")
        antenna_path_settings_layout = QGridLayout()
        antenna_path_settings_layout.setHorizontalSpacing(5)
        antenna_path_settings_layout.setVerticalSpacing(3)

        self.line_edit_1 = QLineEdit()
        self.line_edit_2 = QLineEdit()
        self.line_edit_3 = QLineEdit()
        self.line_edit_4 = QLineEdit()
        self.line_edit_5 = QLineEdit()
        self.line_edit_6 = QLineEdit()

        antenna_path_settings_layout.addWidget(QLabel("Antenna 1"), 0, 0)
        antenna_path_settings_layout.addWidget(self.line_edit_1, 0, 1)
        antenna_path_settings_layout.addWidget(QLabel("Antenna 2"), 1, 0)
        antenna_path_settings_layout.addWidget(self.line_edit_2, 1, 1)
        antenna_path_settings_layout.addWidget(QLabel("Antenna 3"), 2, 0)
        antenna_path_settings_layout.addWidget(self.line_edit_3, 2, 1)
        antenna_path_settings_layout.addWidget(QLabel("Antenna 4"), 3, 0)
        antenna_path_settings_layout.addWidget(self.line_edit_4, 3, 1)
        antenna_path_settings_layout.addWidget(QLabel("Antenna 5"), 4, 0)
        antenna_path_settings_layout.addWidget(self.line_edit_5, 4, 1)
        antenna_path_settings_layout.addWidget(QLabel("Antenna 6"), 5, 0)
        antenna_path_settings_layout.addWidget(self.line_edit_6, 5, 1)

        antenna_path_settings_group.setLayout(antenna_path_settings_layout)

        # Add the group to the main layout
        antenna_control_layout.addWidget(antenna_path_settings_group)
        antenna_control_group.setLayout(antenna_control_layout)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(application_settings_group)
        main_layout.addWidget(spectrum_analyzer_settings_group)
        main_layout.addWidget(antenna_control_group)

        # Add SpectrumAnalyzerApp to the layout
        self.spectrum_analyzer_app = SpectrumAnalyzerApp()
        main_layout.addWidget(self.spectrum_analyzer_app)

        self.setLayout(main_layout)

    def load_setting_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Setting File", "", "Setting Files (*.set);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    data = file.read()
                    # Parse the setting file and update the UI elements
                    # Update the UI elements with the loaded settings
                    settings = data.split("\n")
                    self.center_spinbox.setValue(float(settings[0].split(":")[1].strip()))
                    self.span_spinbox.setValue(float(settings[1].split(":")[1].strip()))
                    self.rbw_combobox.setCurrentText(settings[2].split(":")[1].strip())
                    self.vbw_combobox.setCurrentText(settings[3].split(":")[1].strip()))
                    self.reference_level_spinbox.setValue(float(settings[4].split(":")[1].strip()))
                    self.attenuation_spinbox.setValue(float(settings[5].split(":")[1].strip()))
                    self.sweep_time_spinbox.setValue(float(settings[6].split(":")[1].strip()))
                    self.amp_div_spinbox.setValue(float(settings[7].split(":")[1].strip()))
                    self.line_edit_1.setText(settings[8].split(":")[1].strip())
                    self.line_edit_2.setText(settings[9].split(":")[1].strip())
                    self.line_edit_3.setText(settings[10].split(":")[1].strip())
                    self.line_edit_4.setText(settings[11].split(":")[1].strip())
                    self.line_edit_5.setText(settings[12].split(":")[1].strip())
                    self.line_edit_6.setText(settings[13].split(":")[1].strip())
                    QMessageBox.information(self, "Success", "Settings loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load setting file: {str(e)}")

    def create_spinbox(self, min_value, max_value, step, suffix):
        spinbox = QSpinBox()
        spinbox.setRange(min_value, max_value)
        spinbox.setSingleStep(step)
        spinbox.setSuffix(suffix)
        return spinbox

    def create_double_spinbox(self, min_value, max_value, step, suffix):
        double_spinbox = QDoubleSpinBox()
        double_spinbox.setRange(min_value, max_value)
        double_spinbox.setSingleStep(step)
        double_spinbox.setSuffix(suffix)
        return double_spinbox

    def create_combobox(self, items):
        combobox = QComboBox()
        combobox.addItems(items)
        return combobox

if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = Form()
    form.show()
    sys.exit(app.exec_())
