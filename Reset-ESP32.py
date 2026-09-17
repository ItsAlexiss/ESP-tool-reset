import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import subprocess
import sys
import threading
import time
from datetime import datetime
import queue


APP_NAME = "ESP TOOL PRO"
APP_VERSION = "2.0.0"
CREATOR = "Created by Alexis"

BG = "#080b10"
CARD = "#10151d"
CARD_2 = "#151b24"
BORDER = "#222b38"

TEXT = "#f4f7fb"
MUTED = "#7f8b9d"

BLUE = "#4c8dff"
GREEN = "#27d17f"
RED = "#ff4f64"
YELLOW = "#ffc857"
PURPLE = "#9b7cff"

FONT = "Segoe UI"


class ESPToolPro:

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME}  {APP_VERSION}")
        self.root.geometry("1180x720")
        self.root.minsize(1000, 650)
        self.root.configure(bg=BG)

        self.devices = []
        self.selected_port = None
        self.detected_chip = None
        self.busy = False
        self.log_queue = queue.Queue()

        self.setup_style()
        self.build_ui()
        self.refresh_ports()
        self.process_logs()

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Dark.TCombobox",
            fieldbackground=CARD_2,
            background=CARD_2,
            foreground=TEXT,
            bordercolor=BORDER,
            arrowcolor=MUTED
        )

        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", CARD_2)],
            foreground=[("readonly", TEXT)]
        )

        style.configure(
            "Pro.Horizontal.TProgressbar",
            troughcolor=CARD_2,
            background=BLUE,
            bordercolor=CARD_2,
            lightcolor=BLUE,
            darkcolor=BLUE
        )

    def build_ui(self):

        self.build_header()

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        self.build_sidebar(body)
        self.build_main(body)

        self.build_footer()

    def build_header(self):

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=28, pady=(22, 18))

        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")

        icon = tk.Label(
            brand,
            text="⚡",
            bg=BG,
            fg=BLUE,
            font=(FONT, 25, "bold")
        )
        icon.pack(side="left", padx=(0, 10))

        title_box = tk.Frame(brand, bg=BG)
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text=APP_NAME,
            bg=BG,
            fg=TEXT,
            font=(FONT, 22, "bold")
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text=f"{APP_VERSION}  •  {CREATOR}",
            bg=BG,
            fg=MUTED,
            font=(FONT, 9)
        ).pack(anchor="w")

        status = tk.Frame(header, bg=BG)
        status.pack(side="right", pady=8)

        self.status_dot = tk.Label(
            status,
            text="●",
            bg=BG,
            fg=RED,
            font=(FONT, 12)
        )
        self.status_dot.pack(side="left")

        self.status_label = tk.Label(
            status,
            text="DISCONNECTED",
            bg=BG,
            fg=MUTED,
            font=(FONT, 9, "bold")
        )
        self.status_label.pack(side="left", padx=7)

    def build_sidebar(self, parent):

        sidebar = tk.Frame(
            parent,
            bg=CARD,
            highlightthickness=1,
            highlightbackground=BORDER,
            width=340
        )

        sidebar.pack(
            side="left",
            fill="y",
            padx=(0, 14)
        )

        sidebar.pack_propagate(False)

        self.section(sidebar, "DEVICE")

        self.port_combo = ttk.Combobox(
            sidebar,
            state="readonly",
            style="Dark.TCombobox",
            font=(FONT, 9)
        )

        self.port_combo.pack(
            fill="x",
            padx=20,
            pady=(0, 8),
            ipady=6
        )

        self.port_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.port_changed()
        )

        self.make_button(
            sidebar,
            "⟳   REFRESH DEVICES",
            self.refresh_ports,
            BLUE
        )

        self.make_button(
            sidebar,
            "⌕   DETECT CHIP",
            self.start_detection,
            PURPLE
        )

        self.section(sidebar, "DEVICE INFORMATION")

        info = tk.Frame(
            sidebar,
            bg=CARD
        )

        info.pack(
            fill="x",
            padx=20
        )

        self.info_port = self.info_item(info, "PORT", "---")
        self.info_chip = self.info_item(info, "CHIP", "---")
        self.info_desc = self.info_item(info, "DEVICE", "---")
        self.info_manufacturer = self.info_item(info, "MANUFACTURER", "---")
        self.info_vid = self.info_item(info, "VID / PID", "---")

        self.section(sidebar, "FLASH OPERATIONS")

        self.erase_button = self.make_button(
            sidebar,
            "⚠   ERASE FLASH",
            self.start_erase,
            RED
        )

        self.erase_button.config(
            state="disabled"
        )

        self.make_button(
            sidebar,
            "↻   RESET DEVICE",
            self.manual_reset,
            GREEN
        )

        self.section(sidebar, "SUPPORTED")

        supported = [
            "ESP32",
            "ESP32-S2",
            "ESP32-S3",
            "ESP32-C3",
            "ESP32-C6",
            "ESP8266"
        ]

        for item in supported:

            row = tk.Frame(
                sidebar,
                bg=CARD
            )

            row.pack(
                fill="x",
                padx=22,
                pady=2
            )

            tk.Label(
                row,
                text="●",
                bg=CARD,
                fg=GREEN,
                font=(FONT, 7)
            ).pack(side="left")

            tk.Label(
                row,
                text=item,
                bg=CARD,
                fg=MUTED,
                font=(FONT, 8)
            ).pack(side="left", padx=8)

    def build_main(self, parent):

        main = tk.Frame(
            parent,
            bg=CARD,
            highlightthickness=1,
            highlightbackground=BORDER
        )

        main.pack(
            side="right",
            fill="both",
            expand=True
        )

        top = tk.Frame(
            main,
            bg=CARD
        )

        top.pack(
            fill="x",
            padx=22,
            pady=(20, 15)
        )

        tk.Label(
            top,
            text="SYSTEM CONSOLE",
            bg=CARD,
            fg=TEXT,
            font=(FONT, 11, "bold")
        ).pack(side="left")

        self.console_status = tk.Label(
            top,
            text="READY",
            bg=CARD,
            fg=GREEN,
            font=(FONT, 8, "bold")
        )

        self.console_status.pack(
            side="right"
        )

        console_box = tk.Frame(
            main,
            bg="#06080c",
            highlightthickness=1,
            highlightbackground=BORDER
        )

        console_box.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=(0, 15)
        )

        self.console = tk.Text(
            console_box,
            bg="#06080c",
            fg="#cbd5e1",
            insertbackground=TEXT,
            selectbackground="#263143",
            font=("Cascadia Mono", 9),
            relief="flat",
            borderwidth=0,
            wrap="word"
        )

        self.console.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=14
        )

        bottom = tk.Frame(
            main,
            bg=CARD
        )

        bottom.pack(
            fill="x",
            padx=22,
            pady=(0, 20)
        )

        self.progress = ttk.Progressbar(
            bottom,
            style="Pro.Horizontal.TProgressbar",
            mode="indeterminate"
        )

        self.progress.pack(
            fill="x",
            ipady=2
        )

    def build_footer(self):

        footer = tk.Frame(
            self.root,
            bg=BG
        )

        footer.pack(
            fill="x",
            padx=28,
            pady=(0, 12)
        )

        tk.Label(
            footer,
            text=CREATOR,
            bg=BG,
            fg=MUTED,
            font=(FONT, 8)
        ).pack(side="left")

        tk.Label(
            footer,
            text="ESP32 / ESP8266 FLASH UTILITY",
            bg=BG,
            fg=MUTED,
            font=(FONT, 8)
        ).pack(side="right")

    def section(self, parent, text):

        tk.Label(
            parent,
            text=text,
            bg=CARD,
            fg=MUTED,
            font=(FONT, 8, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 8)
        )

    def make_button(
        self,
        parent,
        text,
        command,
        color
    ):

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=CARD_2,
            fg=TEXT,
            activebackground=color,
            activeforeground="white",
            disabledforeground="#454e5c",
            relief="flat",
            bd=0,
            font=(FONT, 8, "bold"),
            cursor="hand2",
            padx=10,
            pady=10
        )

        button.pack(
            fill="x",
            padx=20,
            pady=4
        )

        return button

    def info_item(
        self,
        parent,
        name,
        value
    ):

        frame = tk.Frame(
            parent,
            bg=CARD
        )

        frame.pack(
            fill="x",
            pady=4
        )

        tk.Label(
            frame,
            text=name,
            bg=CARD,
            fg=MUTED,
            font=(FONT, 7, "bold")
        ).pack(side="left")

        value_label = tk.Label(
            frame,
            text=value,
            bg=CARD,
            fg=TEXT,
            font=(FONT, 8, "bold")
        )

        value_label.pack(
            side="right"
        )

        return value_label

    def log(self, text):

        timestamp = datetime.now().strftime("%H:%M:%S")

        self.log_queue.put(
            f"[{timestamp}] {text}"
        )

    def process_logs(self):

        try:

            while True:

                text = self.log_queue.get_nowait()

                self.console.insert(
                    tk.END,
                    text + "\n"
                )

                self.console.see(
                    tk.END
                )

        except queue.Empty:
            pass

        self.root.after(
            80,
            self.process_logs
        )

    def set_status(
        self,
        text,
        color
    ):

        self.status_dot.config(
            fg=color
        )

        self.status_label.config(
            text=text
        )

    def set_console_status(
        self,
        text,
        color
    ):

        self.console_status.config(
            text=text,
            fg=color
        )

    def refresh_ports(self):

        if self.busy:
            return

        self.devices = list(
            serial.tools.list_ports.comports()
        )

        values = []

        for device in self.devices:

            description = (
                device.description
                or "USB Serial Device"
            )

            values.append(
                f"{device.device}  •  {description}"
            )

        self.port_combo["values"] = values

        if values:

            self.port_combo.current(0)

            self.port_changed()

            self.set_status(
                "DEVICE FOUND",
                YELLOW
            )

            self.log(
                f"Detected {len(values)} serial device(s)."
            )

        else:

            self.port_combo.set(
                "No serial devices"
            )

            self.selected_port = None

            self.set_status(
                "DISCONNECTED",
                RED
            )

            self.log(
                "No serial devices detected."
            )

    def port_changed(self):

        index = self.port_combo.current()

        if index < 0:
            return

        if index >= len(self.devices):
            return

        device = self.devices[index]

        self.selected_port = device.device
        self.detected_chip = None

        self.info_port.config(
            text=device.device
        )

        self.info_desc.config(
            text=device.description or "---"
        )

        self.info_manufacturer.config(
            text=device.manufacturer or "---"
        )

        vid = (
            f"{device.vid:04X}"
            if device.vid is not None
            else "---"
        )

        pid = (
            f"{device.pid:04X}"
            if device.pid is not None
            else "---"
        )

        self.info_vid.config(
            text=f"{vid} / {pid}"
        )

        self.info_chip.config(
            text="Not detected"
        )

        self.erase_button.config(
            state="disabled"
        )

    def start_detection(self):

        if self.busy:
            return

        if not self.selected_port:

            messagebox.showwarning(
                APP_NAME,
                "Select a COM port first."
            )

            return

        confirm = messagebox.askyesno(
            "Confirm device",
            f"Detected serial port:\n\n"
            f"{self.selected_port}\n\n"
            f"Is this your ESP device?"
        )

        if not confirm:
            return

        threading.Thread(
            target=self.detect_chip,
            daemon=True
        ).start()

    def detect_chip(self):

        self.busy = True

        self.progress.start(8)

        self.set_status(
            "CONNECTING",
            YELLOW
        )

        self.set_console_status(
            "DETECTING",
            YELLOW
        )

        self.erase_button.config(
            state="disabled"
        )

        self.log("=" * 58)
        self.log("ESP TOOL PRO - CHIP DETECTION")
        self.log(f"Serial port: {self.selected_port}")
        self.log("Initializing esptool...")

        try:

            command = [
                sys.executable,
                "-m",
                "esptool",
                "--port",
                self.selected_port,
                "chip_id"
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            output = ""

            for line in process.stdout:

                line = line.rstrip()

                output += line + "\n"

                self.log(
                    line
                )

            process.wait()

            if process.returncode != 0:

                self.log(
                    "Connection failed."
                )

                self.set_status(
                    "CONNECTION ERROR",
                    RED
                )

                self.set_console_status(
                    "ERROR",
                    RED
                )

                messagebox.showerror(
                    APP_NAME,
                    "Could not communicate with the ESP.\n\n"
                    "Try holding the BOOT button while "
                    "starting the detection."
                )

                return

            chip = self.identify_chip(
                output
            )

            self.detected_chip = chip

            self.info_chip.config(
                text=chip
            )

            self.set_status(
                "CONNECTED",
                GREEN
            )

            self.set_console_status(
                "CONNECTED",
                GREEN
            )

            self.erase_button.config(
                state="normal"
            )

            self.log(
                f"Detected chip: {chip}"
            )

            self.log(
                "Device communication established."
            )

            messagebox.showinfo(
                APP_NAME,
                f"ESP detected successfully.\n\n"
                f"Port: {self.selected_port}\n"
                f"Chip: {chip}"
            )

        except Exception as error:

            self.log(
                f"ERROR: {error}"
            )

            self.set_status(
                "ERROR",
                RED
            )

            self.set_console_status(
                "ERROR",
                RED
            )

            messagebox.showerror(
                APP_NAME,
                str(error)
            )

        finally:

            self.progress.stop()
            self.busy = False

    def identify_chip(
        self,
        output
    ):

        text = output.lower()

        if "esp32-s3" in text:
            return "ESP32-S3"

        if "esp32-s2" in text:
            return "ESP32-S2"

        if "esp32-c6" in text:
            return "ESP32-C6"

        if "esp32-c3" in text:
            return "ESP32-C3"

        if "esp32-h2" in text:
            return "ESP32-H2"

        if "esp8266" in text:
            return "ESP8266"

        if "esp32" in text:
            return "ESP32 / WROVER"

        return "ESP COMPATIBLE"

    def start_erase(self):

        if self.busy:
            return

        if not self.selected_port:
            return

        if not self.detected_chip:

            messagebox.showwarning(
                APP_NAME,
                "Detect the ESP chip before erasing the flash."
            )

            return

        confirm = messagebox.askyesno(
            "ERASE FLASH",
            f"WARNING\n\n"
            f"This will completely erase the flash "
            f"memory of the device.\n\n"
            f"Device: {self.detected_chip}\n"
            f"Port: {self.selected_port}\n\n"
            f"All firmware and stored data will be removed.\n\n"
            f"Continue?",
            icon="warning"
        )

        if not confirm:
            return

        threading.Thread(
            target=self.erase_flash,
            daemon=True
        ).start()

    def erase_flash(self):

        self.busy = True

        self.progress.start(8)

        self.erase_button.config(
            state="disabled"
        )

        self.set_status(
            "ERASING FLASH",
            YELLOW
        )

        self.set_console_status(
            "ERASING",
            YELLOW
        )

        self.log("=" * 58)
        self.log("FLASH ERASE OPERATION")
        self.log(f"Device: {self.detected_chip}")
        self.log(f"Port: {self.selected_port}")
        self.log("Starting esptool erase_flash...")

        try:

            command = [
                sys.executable,
                "-m",
                "esptool",
                "--port",
                self.selected_port,
                "erase_flash"
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            for line in process.stdout:

                self.log(
                    line.rstrip()
                )

            process.wait()

            if process.returncode == 0:

                self.log(
                    "FLASH ERASE COMPLETED SUCCESSFULLY."
                )

                self.set_status(
                    "FLASH ERASED",
                    GREEN
                )

                self.set_console_status(
                    "SUCCESS",
                    GREEN
                )

                self.reset_device()

                messagebox.showinfo(
                    APP_NAME,
                    "Flash erased successfully."
                )

            else:

                self.log(
                    f"esptool exited with code "
                    f"{process.returncode}"
                )

                self.set_status(
                    "ERASE FAILED",
                    RED
                )

                self.set_console_status(
                    "FAILED",
                    RED
                )

                messagebox.showerror(
                    APP_NAME,
                    "Flash erase failed.\n\n"
                    "Try holding BOOT while connecting "
                    "to the device."
                )

        except Exception as error:

            self.log(
                f"ERROR: {error}"
            )

            self.set_status(
                "ERROR",
                RED
            )

            self.set_console_status(
                "ERROR",
                RED
            )

        finally:

            self.progress.stop()
            self.busy = False

            if self.detected_chip:

                self.erase_button.config(
                    state="normal"
                )

    def manual_reset(self):

        if not self.selected_port:

            messagebox.showwarning(
                APP_NAME,
                "Select a COM port first."
            )

            return

        self.reset_device()

    def reset_device(self):

        self.log(
            "Sending hardware reset..."
        )

        try:

            port = serial.Serial(
                self.selected_port,
                115200,
                timeout=1
            )

            port.dtr = False
            port.rts = True

            time.sleep(0.15)

            port.rts = False
            port.dtr = True

            time.sleep(0.15)

            port.close()

            self.log(
                "Hardware reset signal sent."
            )

            self.set_status(
                "RESET SENT",
                GREEN
            )

        except Exception as error:

            self.log(
                f"Reset failed: {error}"
            )

            self.set_status(
                "RESET FAILED",
                RED
            )


def main():

    root = tk.Tk()

    app = ESPToolPro(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()