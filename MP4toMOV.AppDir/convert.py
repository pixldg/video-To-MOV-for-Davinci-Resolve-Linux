#!/usr/bin/env python3
import gi, subprocess, os, signal
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# --- Paths ---
HERE = os.path.dirname(os.path.realpath(__file__))
FFMPEG = os.path.join(HERE, "usr/bin/ffmpeg") if os.path.exists(os.path.join(HERE, "usr/bin/ffmpeg")) else "ffmpeg"
FFPROBE = os.path.join(HERE, "usr/bin/ffprobe") if os.path.exists(os.path.join(HERE, "usr/bin/ffprobe")) else "ffprobe"
ICON_PATH = os.path.join(HERE, "mp4tomov.png")

class Converter(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="MP4 to MOV Converter")
        self.set_border_width(10)
        self.set_default_size(550, 250)
        if os.path.exists(ICON_PATH):
            self.set_icon_from_file(ICON_PATH)

        self.proc = None
        self.output_file = None
        self.popup = None

        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        self.add(grid)

        # --- Input file chooser ---
        self.file_chooser = Gtk.FileChooserButton(title="Select video file")
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Video files")
        for ext in ["mp4","mkv","m4v","mov","avi","wmv","hevc","3gp"]:
            filter_video.add_pattern(f"*.{ext}")
        self.file_chooser.add_filter(filter_video)
        grid.attach(Gtk.Label(label="Video File:"), 0, 0, 1, 1)
        grid.attach(self.file_chooser, 1, 0, 2, 1)

        # --- Destination folder chooser ---
        self.dest_chooser = Gtk.FileChooserButton(title="Select destination folder",
                                                  action=Gtk.FileChooserAction.SELECT_FOLDER)
        grid.attach(Gtk.Label(label="Destination Folder:"), 0, 1, 1, 1)
        grid.attach(self.dest_chooser, 1, 1, 2, 1)

        # --- FPS options ---
        self.fps_store = Gtk.ListStore(str)
        for fps in ["Original","23.976","24","29.97","30","60"]:
            self.fps_store.append([fps])
        self.fps_combo = Gtk.ComboBox.new_with_model(self.fps_store)
        renderer_text = Gtk.CellRendererText()
        self.fps_combo.pack_start(renderer_text, True)
        self.fps_combo.add_attribute(renderer_text, "text", 0)
        self.fps_combo.set_active(0)
        grid.attach(Gtk.Label(label="FPS:"), 0, 2, 1, 1)
        grid.attach(self.fps_combo, 1, 2, 2, 1)

        # --- Codec combobox ---
        self.codec_store = Gtk.ListStore(str)
        for codec in ["ProRes","DNxHD","Cineform"]:
            self.codec_store.append([codec])
        self.codec_combo = Gtk.ComboBox.new_with_model(self.codec_store)
        renderer_text = Gtk.CellRendererText()
        self.codec_combo.pack_start(renderer_text, True)
        self.codec_combo.add_attribute(renderer_text, "text", 0)
        self.codec_combo.set_active(0)
        grid.attach(Gtk.Label(label="Codec:"), 0, 3, 1, 1)
        grid.attach(self.codec_combo, 1, 3, 2, 1)

        # --- Start and Stop buttons ---
        self.start_button = Gtk.Button(label="Start Conversion")
        self.start_button.connect("clicked", self.on_start)
        grid.attach(self.start_button, 1, 4, 1, 1)

        self.stop_button = Gtk.Button(label="Stop Conversion")
        self.stop_button.connect("clicked", self.on_stop)
        self.stop_button.set_sensitive(False)
        grid.attach(self.stop_button, 2, 4, 1, 1)

        self.show_all()

    def on_start(self, widget):
        input_file = self.file_chooser.get_filename()
        if not input_file:
            self.show_message("Please select a video file.")
            return

        dest_folder = self.dest_chooser.get_filename()
        if not dest_folder:
            self.show_message("Please select a destination folder.")
            return

        fps_iter = self.fps_combo.get_active_iter()
        fps_choice = self.fps_store[fps_iter][0] if fps_iter else "Original"

        codec_iter = self.codec_combo.get_active_iter()
        codec_choice = self.codec_store[codec_iter][0] if codec_iter else "ProRes"

        filename_base = os.path.splitext(os.path.basename(input_file))[0]
        self.output_file = os.path.join(dest_folder, filename_base + ".mov")

        # Auto-rename if file exists
        counter = 1
        while os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
            self.output_file = os.path.join(dest_folder, f"{filename_base}_copy{counter}.mov")
            counter += 1

        # FFmpeg command
        ffmpeg_cmd = [FFMPEG, "-y", "-i", input_file]
        if codec_choice == "ProRes":
            ffmpeg_cmd += ["-c:v","prores_ks","-profile:v","3","-pix_fmt","yuv422p10le","-c:a","pcm_s16le"]
        elif codec_choice == "DNxHD":
            ffmpeg_cmd += ["-c:v","dnxhd","-b:v","36M","-pix_fmt","yuv422p","-c:a","pcm_s16le"]
        elif codec_choice == "Cineform":
            ffmpeg_cmd += ["-c:v","cfhd","-qscale:v","3","-c:a","pcm_s16le"]

        if fps_choice != "Original":
            ffmpeg_cmd += ["-r", fps_choice]

        ffmpeg_cmd.append(self.output_file)

        # Disable start, enable stop
        self.start_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)

        # Show converting popup
        self.popup = Gtk.Window(title="Converting")
        self.popup.set_default_size(250, 80)
        label = Gtk.Label(label="Converting, please wait...")
        self.popup.add(label)
        self.popup.show_all()

        # Start FFmpeg asynchronously
        self.proc = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, text=True)
        GLib.timeout_add(500, self.check_process)

    def check_process(self):
        if self.proc.poll() is None:
            return True  # still running, check again in 500ms
        else:
            # Close converting popup
            if self.popup:
                self.popup.destroy()
                self.popup = None
            # Show completion dialog
            if self.proc.returncode == 0:
                self.show_message(f"Conversion complete:\n{self.output_file}")
            else:
                self.show_message("Conversion failed or stopped!")
                if self.output_file and os.path.exists(self.output_file):
                    os.remove(self.output_file)
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            return False  # stop checking

    def on_stop(self, widget):
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            if self.popup:
                self.popup.destroy()
                self.popup = None
            if self.output_file and os.path.exists(self.output_file):
                os.remove(self.output_file)
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)

    def show_message(self, msg):
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text=msg)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    win = Converter()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
