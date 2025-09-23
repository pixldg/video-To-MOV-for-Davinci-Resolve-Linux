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
        self.set_default_size(500, 250)
        self.set_icon_from_file(ICON_PATH)

        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        self.add(grid)

        # --- File chooser ---
        self.file_chooser = Gtk.FileChooserButton(title="Select video file")
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Video files")
        for ext in ["mp4","mkv","m4v","mov","avi","wmv","hevc","3gp"]:
            filter_video.add_pattern(f"*.{ext}")
        self.file_chooser.add_filter(filter_video)
        self.file_chooser.connect("selection-changed", self.on_file_changed)
        grid.attach(Gtk.Label(label="Video File:"), 0,0,1,1)
        grid.attach(self.file_chooser,1,0,2,1)

        # --- FPS options ---
        self.fps_store = Gtk.ListStore(str)
        for fps in ["Original","23.976","24","30","60"]:
            self.fps_store.append([fps])
        self.fps_combo = Gtk.ComboBox.new_with_model(self.fps_store)
        renderer_text = Gtk.CellRendererText()
        self.fps_combo.pack_start(renderer_text, True)
        self.fps_combo.add_attribute(renderer_text, "text", 0)
        self.fps_combo.set_active(0)
        grid.attach(Gtk.Label(label="FPS:"), 0,1,1,1)
        grid.attach(self.fps_combo,1,1,2,1)

        # --- Resolution options ---
        self.res_store = Gtk.ListStore(str)
        for res in ["Original","1920x1080","2048x1080","3840x2160"]:
            self.res_store.append([res])
        self.res_combo = Gtk.ComboBox.new_with_model(self.res_store)
        renderer_text = Gtk.CellRendererText()
        self.res_combo.pack_start(renderer_text, True)
        self.res_combo.add_attribute(renderer_text, "text", 0)
        self.res_combo.set_active(0)
        grid.attach(Gtk.Label(label="Resolution:"),0,2,1,1)
        grid.attach(self.res_combo,1,2,2,1)

        # --- Warning label ---
        self.warning_label = Gtk.Label(label="")
        self.warning_label.set_line_wrap(True)
        self.warning_label.set_justify(Gtk.Justification.LEFT)
        grid.attach(self.warning_label, 0, 3, 3, 1)

        # --- Start button ---
        self.start_button = Gtk.Button(label="Start Conversion")
        self.start_button.connect("clicked", self.on_start)
        grid.attach(self.start_button,1,4,1,1)

        # --- Progress bar ---
        self.progress = Gtk.ProgressBar()
        grid.attach(self.progress,0,5,3,1)

        self.show_all()

    def on_file_changed(self, widget):
        input_file = self.file_chooser.get_filename()
        if not input_file:
            self.warning_label.set_text("")
            return

        resolution_available = True
        fps_available = True

        try:
            width_height = subprocess.check_output([FFPROBE,"-v","error","-select_streams","v:0",
                                                   "-show_entries","stream=width,height","-of","csv=p=0", input_file],
                                                  text=True).strip()
            width_val, height_val = map(int, width_height.split(","))
        except:
            resolution_available = False

        try:
            fps_val = subprocess.check_output([FFPROBE,"-v","error","-select_streams","v:0",
                                              "-show_entries","stream=r_frame_rate","-of","default=noprint_wrappers=1:nokey=1",input_file],
                                             text=True).strip()
            num, den = map(int, fps_val.split("/"))
            fps_actual = num/den if den>0 else num
        except:
            fps_available = False

        # Disable "Original" if not available
        if not fps_available:
            self.fps_combo.set_active(1)
            self.fps_combo.get_child().set_sensitive(False)
        else:
            self.fps_combo.set_sensitive(True)

        if not resolution_available:
            self.res_combo.set_active(1)
            self.res_combo.get_child().set_sensitive(False)
        else:
            self.res_combo.set_sensitive(True)

        # Set warning text if either missing
        warning_msgs = []
        if not resolution_available:
            warning_msgs.append("resolution")
        if not fps_available:
            warning_msgs.append("frame rate")
        if warning_msgs:
            self.warning_label.set_text(
                "⚠ Warning: This video file does not have detected " + " and ".join(warning_msgs) +
                ". Please select a value for the final conversion."
            )
        else:
            self.warning_label.set_text("")

    def on_start(self, widget):
        input_file = self.file_chooser.get_filename()
        if not input_file:
            self.show_message("Please select a video file.")
            return

        fps_iter = self.fps_combo.get_active_iter()
        fps_choice = self.fps_store[fps_iter][0] if fps_iter else "Original"

        res_iter = self.res_combo.get_active_iter()
        res_choice = self.res_store[res_iter][0] if res_iter else "Original"

        output_file = os.path.splitext(input_file)[0] + ".mov"

        ffmpeg_cmd = [FFMPEG, "-i", input_file, "-vcodec", "dnxhd", "-acodec", "pcm_s16le",
                      "-b:v","36M","-pix_fmt","yuv422p","-f","mov"]
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
