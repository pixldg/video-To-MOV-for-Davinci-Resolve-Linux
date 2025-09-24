#!/usr/bin/env python3
import gi, subprocess, os, sys, time
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib

# --- Paths ---
HERE = os.path.dirname(os.path.realpath(__file__))
FFMPEG = os.path.join(HERE, "usr/bin/ffmpeg") if os.path.exists(os.path.join(HERE, "usr/bin/ffmpeg")) else "ffmpeg"
FFPROBE = os.path.join(HERE, "usr/bin/ffprobe") if os.path.exists(os.path.join(HERE, "usr/bin/ffprobe")) else "ffprobe"
ICON_PATH = os.path.join(HERE, "mp4tomov.png")

class Converter(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="MP4 to MOV Converter")
        self.set_border_width(10)
        self.set_default_size(550, 350)
        self.set_icon_from_file(ICON_PATH)

        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        self.add(grid)

        # --- Input file chooser ---
        self.file_chooser = Gtk.FileChooserButton(title="Select video file")
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Video files")
        for ext in ["mp4","mkv","m4v","mov","avi","wmv","hevc","3gp"]:
            filter_video.add_pattern(f"*.{ext}")
        self.file_chooser.add_filter(filter_video)
        grid.attach(Gtk.Label(label="Video File:"),0,0,1,1)
        grid.attach(self.file_chooser,1,0,2,1)

        # --- Destination folder chooser ---
        self.dest_chooser = Gtk.FileChooserButton(
            title="Select destination folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        grid.attach(Gtk.Label(label="Destination Folder:"),0,1,1,1)
        grid.attach(self.dest_chooser,1,1,2,1)

        # --- FPS options ---
        self.fps_store = Gtk.ListStore(str)
        for fps in ["Original","23.976","24","29.97","30","60"]:
            self.fps_store.append([fps])
        self.fps_combo = Gtk.ComboBox.new_with_model(self.fps_store)
        renderer_text = Gtk.CellRendererText()
        self.fps_combo.pack_start(renderer_text, True)
        self.fps_combo.add_attribute(renderer_text, "text", 0)
        self.fps_combo.set_active(0)
        grid.attach(Gtk.Label(label="FPS:"),0,2,1,1)
        grid.attach(self.fps_combo,1,2,2,1)

        # --- Size type checkboxes ---
        self.size_type_original = Gtk.CheckButton(label="Original")
        self.size_type_horizontal = Gtk.CheckButton(label="Horizontal")
        self.size_type_vertical = Gtk.CheckButton(label="Vertical")
        self.size_type_square = Gtk.CheckButton(label="Square")
        self.size_type_original.set_active(True)
        for cb in [self.size_type_original, self.size_type_horizontal, self.size_type_vertical, self.size_type_square]:
            cb.connect("toggled", self.on_size_type_toggled)
        grid.attach(self.size_type_original,0,3,1,1)
        grid.attach(self.size_type_horizontal,1,3,1,1)
        grid.attach(self.size_type_vertical,2,3,1,1)
        grid.attach(self.size_type_square,3,3,1,1)

        # --- Resolution combobox ---
        self.res_store = Gtk.ListStore(str)
        self.res_combo = Gtk.ComboBox.new_with_model(self.res_store)
        renderer_text = Gtk.CellRendererText()
        self.res_combo.pack_start(renderer_text, True)
        self.res_combo.add_attribute(renderer_text, "text", 0)
        grid.attach(Gtk.Label(label="Resolution:"),0,4,1,1)
        grid.attach(self.res_combo,1,4,2,1)
        self.update_resolution_list("Original")

        # --- Log file checkbox ---
        self.log_checkbox = Gtk.CheckButton(label="Create log file")
        grid.attach(self.log_checkbox,0,5,2,1)

        # --- Warning label ---
        self.warning_label = Gtk.Label(label="")
        self.warning_label.set_line_wrap(True)
        self.warning_label.set_justify(Gtk.Justification.LEFT)
        grid.attach(self.warning_label, 0, 6, 4, 1)

        # --- Start button ---
        self.start_button = Gtk.Button(label="Start Conversion")
        self.start_button.connect("clicked", self.on_start)
        grid.attach(self.start_button,1,7,2,1)

        # --- Progress bar ---
        self.progress = Gtk.ProgressBar()
        grid.attach(self.progress,0,8,4,1)

        self.show_all()

    def on_size_type_toggled(self, widget):
        # Only one can be active at a time
        if widget.get_active():
            for cb in [self.size_type_original, self.size_type_horizontal, self.size_type_vertical, self.size_type_square]:
                if cb != widget:
                    cb.set_active(False)
            size_type = widget.get_label()
            self.update_resolution_list(size_type)

    def update_resolution_list(self, size_type):
        self.res_store.clear()
        if size_type == "Original":
            self.res_combo.set_sensitive(False)
            self.res_store.append(["Original"])
        else:
            self.res_combo.set_sensitive(True)
            if size_type == "Horizontal":
                for res in ["1920x1080","2048x1080","3840x2160"]:
                    self.res_store.append([res])
            elif size_type == "Vertical":
                for res in ["1080x1920","1080x2048","2160x3840"]:
                    self.res_store.append([res])
            elif size_type == "Square":
                for res in ["1920x1920","2048x2048","3840x3840"]:
                    self.res_store.append([res])
        self.res_combo.set_active(0)

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

        res_iter = self.res_combo.get_active_iter()
        res_choice = self.res_store[res_iter][0] if res_iter else "Original"

        filename_base = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(dest_folder, filename_base + ".mov")

        # Auto rename if file exists
        counter = 1
        orig_output_file = output_file
        while os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            output_file = os.path.join(dest_folder, f"{filename_base}_copy{counter}.mov")
            counter += 1

        ffmpeg_cmd = [FFMPEG, "-i", input_file, "-vcodec", "prores_ks", "-acodec", "pcm_s16le", "-pix_fmt", "yuv422p"]
        if fps_choice != "Original":
            ffmpeg_cmd += ["-r", fps_choice]
        if res_choice != "Original":
            ffmpeg_cmd += ["-s", res_choice]
        ffmpeg_cmd.append(output_file)

        GLib.idle_add(self.run_conversion, ffmpeg_cmd, input_file, output_file)

    def run_conversion(self, cmd, input_file, output_file):
        try:
            duration = float(subprocess.check_output([FFPROBE,"-v","error","-select_streams","v:0",
                                                      "-show_entries","stream=duration","-of","default=noprint_wrappers=1:nokey=1",input_file],
                                                     text=True).strip())
        except:
            duration = 1

        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        start_time = time.time()
        for line in proc.stderr:
            if "time=" in line:
                t_str = line.split("time=")[1].split(" ")[0]
                h,m,s = [float(x) for x in t_str.split(":")]
                elapsed = h*3600 + m*60 + s
                frac = min(elapsed/duration,1.0)
                GLib.idle_add(self.progress.set_fraction, frac)
                eta_sec = (time.time()-start_time)*(duration/elapsed-1) if elapsed>0 else 0
                eta_str = time.strftime("%H:%M:%S remaining", time.gmtime(eta_sec)) if elapsed>0 else "Calculating ETA..."
                GLib.idle_add(self.progress.set_text, eta_str)
        proc.wait()
        GLib.idle_add(self.progress.set_fraction,1.0)
        GLib.idle_add(self.progress.set_text,"Conversion complete!")

        # Done conversion dialog
        self.show_message(f"Conversion complete:\n{output_file}")

    def show_message(self, msg):
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text=msg)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    win = Converter()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
