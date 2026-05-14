import os
import io
import zipfile
import shutil
import tempfile
from tkinter import filedialog
from threading import Thread

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw

from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
AUDIO_EXTENSIONS = {".mp3", ".flac"}

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def load_icon(name, size):
    path = os.path.join(ICONS_DIR, f"{name}.png")
    return ctk.CTkImage(Image.open(path), size=(size, size))


# --- Core functions ---

def find_files_in_dir(directory):
    image = None
    audios = []
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext in IMAGE_EXTENSIONS and image is None:
            image = fpath
        elif ext in AUDIO_EXTENSIONS:
            audios.append(fpath)
    return image, audios


def analyze_zip(zip_path):
    zip_name = os.path.splitext(os.path.basename(zip_path))[0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        image, audios = find_files_in_dir(tmp_dir)
        if not audios:
            for sub in os.listdir(tmp_dir):
                sub_path = os.path.join(tmp_dir, sub)
                if os.path.isdir(sub_path):
                    img, auds = find_files_in_dir(sub_path)
                    if auds:
                        image = image or img
                        audios.extend(auds)

        image_data = None
        if image:
            with open(image, "rb") as f:
                image_data = f.read()

        track_names = [os.path.splitext(os.path.basename(a))[0] for a in audios]

        return {
            "zip_path": zip_path,
            "zip_name": zip_name,
            "image_data": image_data,
            "track_names": track_names,
            "has_cover": image_data is not None,
            "track_count": len(audios),
        }


def embed_cover_flac(audio_path, image_data, mime_type):
    audio = FLAC(audio_path)
    audio.clear_pictures()
    pic = Picture()
    pic.type = 3
    pic.mime = mime_type
    pic.desc = "Cover"
    pic.data = image_data
    audio.add_picture(pic)
    audio.save()


def embed_cover_mp3(audio_path, image_data, mime_type):
    audio = MP3(audio_path, ID3=ID3)
    try:
        audio.add_tags()
    except Exception:
        pass
    tags = audio.tags
    assert tags is not None
    tags.delall("APIC")
    tags.add(APIC(
        encoding=3,
        mime=mime_type,
        type=3,
        desc="Cover",
        data=image_data,
    ))
    audio.save()


def process_zip(zip_path, output_dir, log_callback=None):
    zip_name = os.path.splitext(os.path.basename(zip_path))[0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        image, audios = find_files_in_dir(tmp_dir)
        if not audios:
            for sub in os.listdir(tmp_dir):
                sub_path = os.path.join(tmp_dir, sub)
                if os.path.isdir(sub_path):
                    img, auds = find_files_in_dir(sub_path)
                    if auds:
                        image = image or img
                        audios.extend(auds)

        if not image or not audios:
            if log_callback:
                log_callback(f"  SKIP  {zip_name}")
            return False

        image_ext = os.path.splitext(image)[1].lower()
        mime_type = MIME_TYPES.get(image_ext, "image/jpeg")
        with open(image, "rb") as f:
            image_data = f.read()

        for audio_path in audios:
            ext = os.path.splitext(audio_path)[1].lower()
            if ext == ".flac":
                embed_cover_flac(audio_path, image_data, mime_type)
            elif ext == ".mp3":
                embed_cover_mp3(audio_path, image_data, mime_type)

            dest = os.path.join(output_dir, os.path.basename(audio_path))
            shutil.copy2(audio_path, dest)

        count = len(audios)
        if log_callback:
            log_callback(f"  OK    {zip_name} — {count} track{'s' if count > 1 else ''}")
        return True


def make_rounded_thumb(image_data, size=50, radius=12):
    img = Image.open(io.BytesIO(image_data)).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=255)
    img.putalpha(mask)
    return ImageTk.PhotoImage(img)


# --- UI ---

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#0d0d0d"
SURFACE = "#1a1a2e"
SURFACE_2 = "#25253e"
SURFACE_3 = "#30304a"
TEXT = "#f0f0f5"
TEXT_SEC = "#9d9db5"
TEXT_TER = "#5a5a78"
PURPLE = "#a855f7"
PURPLE_HOVER = "#c084fc"
PURPLE_DIM = "#7c3aed"
PINK = "#ec4899"
GREEN = "#34d399"
RED = "#f43f5e"
THUMB_SIZE = 50

SPINNER_FRAMES = ["\u25DC", "\u25DD", "\u25DE", "\u25DF"]


class FolderSelector(ctk.CTkFrame):
    def __init__(self, master, icon_img, label, dialog_title):
        super().__init__(master, fg_color=SURFACE, corner_radius=14,
                         border_width=1, border_color=SURFACE_2)
        self.dialog_title = dialog_title
        self.path = ""

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=18, pady=14)

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        top_row = ctk.CTkFrame(left, fg_color="transparent")
        top_row.pack(anchor="w")

        ctk.CTkLabel(
            top_row, text="", image=icon_img,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            top_row, text=label,
            font=("SF Pro Display", 14, "bold"), text_color=TEXT,
        ).pack(side="left")

        self.path_label = ctk.CTkLabel(
            left, text="Tap browse to pick a folder",
            font=("SF Mono", 11), text_color=TEXT_TER, anchor="w",
        )
        self.path_label.pack(anchor="w", padx=(28, 0), pady=(4, 0))

        self.btn = ctk.CTkButton(
            content, text="Browse", width=80, height=30,
            font=("SF Pro Text", 12, "bold"),
            fg_color=PURPLE_DIM, hover_color=PURPLE,
            text_color="#ffffff", corner_radius=8,
            command=self.browse,
        )
        self.btn.pack(side="right")

    def browse(self):
        path = filedialog.askdirectory(title=self.dialog_title)
        if path:
            self.path = path
            display = path if len(path) < 50 else "..." + path[-47:]
            self.path_label.configure(text=display, text_color=TEXT_SEC)


class TrackRow(ctk.CTkFrame):
    def __init__(self, master, track_name, subtitle, cover_image=None, hp_icon=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=12, height=64,
                         border_width=1, border_color=SURFACE_2)
        self.pack_propagate(False)

        self._photo = None

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=7)

        if cover_image:
            self._photo = make_rounded_thumb(cover_image, THUMB_SIZE, 12)
            ctk.CTkLabel(row, image=self._photo, text="").pack(side="left", padx=(0, 14))
        else:
            ph = ctk.CTkFrame(row, width=THUMB_SIZE, height=THUMB_SIZE, fg_color=SURFACE_3, corner_radius=12)
            ph.pack(side="left", padx=(0, 14))
            ph.pack_propagate(False)
            if hp_icon:
                ctk.CTkLabel(ph, text="", image=load_icon("music-dim", 24)).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info, text=track_name,
            font=("SF Pro Text", 13, "bold"), text_color=TEXT, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            info, text=subtitle,
            font=("SF Pro Text", 11), text_color=TEXT_TER, anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        if hp_icon:
            ctk.CTkLabel(row, text="", image=hp_icon).pack(side="right", padx=(8, 4))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("Cover Drop")
        self.geometry("800x720")
        self.minsize(580, 500)

        self.analyzed_data = []
        self._spinner_running = False
        self._spinner_index = 0
        self._spinner_text = ""
        self._spinner_after_id = None

        # Load icons
        self._icon_disc = load_icon("disc-3-purple", 28)
        self._icon_folder = load_icon("folder-purple", 18)
        self._icon_sparkle = load_icon("sparkles-pink", 18)
        self._icon_search = load_icon("search-white", 16)
        self._icon_rocket = load_icon("rocket-white", 16)
        self._icon_hp = load_icon("headphones-purple", 16)
        self._icon_hp_sec = load_icon("headphones-sec", 14)
        self._icon_heart = load_icon("heart-purple", 12)

        # --- Header ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=36, pady=(36, 0))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row, text="", image=self._icon_disc,
        ).pack(side="left", padx=(0, 14))

        titles = ctk.CTkFrame(title_row, fg_color="transparent")
        titles.pack(side="left")

        ctk.CTkLabel(
            titles, text="Cover Drop",
            font=("SF Pro Display", 28, "bold"), text_color=TEXT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            titles, text="Drop your ZIPs, get your covers embedded. Easy.",
            font=("SF Pro Text", 13), text_color=TEXT_TER,
        ).pack(anchor="w", pady=(2, 0))

        # --- Folder selectors ---
        selectors = ctk.CTkFrame(self, fg_color="transparent")
        selectors.pack(fill="x", padx=36, pady=(24, 0))

        self.input_sel = FolderSelector(selectors, self._icon_folder, "ZIP Folder", "Select folder with ZIPs")
        self.input_sel.pack(fill="x", pady=(0, 8))

        self.output_sel = FolderSelector(selectors, self._icon_sparkle, "Output Folder", "Select output folder")
        self.output_sel.pack(fill="x")

        # --- Action bar ---
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=36, pady=(20, 0))

        btn_container = ctk.CTkFrame(action_bar, fg_color="transparent")
        btn_container.pack(side="left")

        self.btn_analyze = ctk.CTkButton(
            btn_container, text="  Analyze", height=40, width=140,
            image=self._icon_search,
            font=("SF Pro Text", 13, "bold"),
            fg_color=PURPLE, hover_color=PURPLE_HOVER, text_color="#ffffff",
            corner_radius=12, command=self.start_analyze,
            compound="left",
        )
        self.btn_analyze.pack(side="left", padx=(0, 8))

        self.btn_process = ctk.CTkButton(
            btn_container, text="  Process", height=40, width=140,
            image=self._icon_rocket,
            font=("SF Pro Text", 13, "bold"),
            fg_color=SURFACE_2, hover_color=SURFACE_3,
            text_color=TEXT_TER, corner_radius=12,
            command=self.start_processing, state="disabled",
            compound="left",
        )
        self.btn_process.pack(side="left")

        # Status
        self.status = ctk.CTkLabel(
            action_bar, text="",
            font=("SF Pro Text", 12), text_color=TEXT_TER,
        )
        self.status.pack(side="right")

        # --- Progress bar ---
        self.progress = ctk.CTkProgressBar(
            self, height=4, fg_color=SURFACE_2, progress_color=PURPLE,
            corner_radius=2,
        )
        self.progress.pack(fill="x", padx=36, pady=(16, 0))
        self.progress.set(0)

        # --- Track list header ---
        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=36, pady=(16, 0))

        th_left = ctk.CTkFrame(list_header, fg_color="transparent")
        th_left.pack(side="left")

        ctk.CTkLabel(
            th_left, text="", image=self._icon_hp_sec,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            th_left, text="Track Preview",
            font=("SF Pro Text", 12, "bold"), text_color=TEXT_SEC,
        ).pack(side="left")

        self.track_count_label = ctk.CTkLabel(
            list_header, text="",
            font=("SF Pro Text", 12), text_color=TEXT_TER,
        )
        self.track_count_label.pack(side="right")

        # --- Scrollable track list ---
        self.preview_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
        )
        self.preview_frame.pack(fill="both", expand=True, padx=36, pady=(8, 12))

        # Empty state
        empty = ctk.CTkFrame(self.preview_frame, fg_color=SURFACE, corner_radius=16, height=140)
        empty.pack(fill="x", pady=8)
        empty.pack_propagate(False)

        ctk.CTkLabel(
            empty, text="", image=load_icon("music-sec", 28),
        ).place(relx=0.5, rely=0.35, anchor="center")

        ctk.CTkLabel(
            empty, text="No tracks yet — hit Analyze to get started!",
            font=("SF Pro Text", 13), text_color=TEXT_TER,
        ).place(relx=0.5, rely=0.65, anchor="center")

        # --- Footer ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(pady=(0, 16))


    # --- Spinner ---
    def start_spinner(self, text):
        self._spinner_running = True
        self._spinner_index = 0
        self._spinner_text = text
        self._tick_spinner()

    def _tick_spinner(self):
        if not self._spinner_running:
            return
        frame = SPINNER_FRAMES[self._spinner_index % len(SPINNER_FRAMES)]
        self.status.configure(text=f"{frame}  {self._spinner_text}", text_color=PURPLE)
        self._spinner_index += 1
        self._spinner_after_id = self.after(120, self._tick_spinner)

    def stop_spinner(self, done_text, is_error=False):
        self._spinner_running = False
        if self._spinner_after_id:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None
        if is_error:
            self.status.configure(text=f"x  {done_text}", text_color=RED)
        else:
            self.status.configure(text=f"ok  {done_text}", text_color=GREEN)

    # --- Preview ---
    def clear_preview(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

    def start_analyze(self):
        input_dir = self.input_sel.path
        if not input_dir:
            self.status.configure(text="Pick a ZIP folder first!", text_color=RED)
            return

        self.btn_analyze.configure(state="disabled")
        self.btn_process.configure(state="disabled", fg_color=SURFACE_2, text_color=TEXT_TER)
        self.progress.set(0)
        self.clear_preview()
        self.analyzed_data = []
        self.track_count_label.configure(text="")
        self.start_spinner("Scanning ZIPs...")

        Thread(target=self.run_analyze, args=(input_dir,), daemon=True).start()

    def run_analyze(self, input_dir):
        zips = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(".zip")])

        if not zips:
            self.after(0, lambda: self.stop_spinner("No ZIP files found", is_error=True))
            self.after(0, lambda: self.btn_analyze.configure(state="normal"))
            return

        total = len(zips)
        results = []

        for i, zip_name in enumerate(zips, 1):
            zip_path = os.path.join(input_dir, zip_name)
            try:
                info = analyze_zip(zip_path)
                results.append(info)
            except Exception as e:
                results.append({
                    "zip_path": zip_path,
                    "zip_name": os.path.splitext(zip_name)[0],
                    "image_data": None,
                    "track_names": [],
                    "has_cover": False,
                    "track_count": 0,
                    "error": str(e),
                })
            self.after(0, lambda v=i / total: self.progress.set(v))

        self.analyzed_data = results
        self.after(0, lambda: self.show_preview(results))

    def show_preview(self, results):
        self.clear_preview()

        total_tracks = 0
        for info in results:
            cover = info["image_data"]
            if not info["track_names"]:
                TrackRow(self.preview_frame, info["zip_name"], "No tracks found", cover, self._icon_hp).pack(fill="x", pady=(0, 6))
                continue
            for name in info["track_names"]:
                TrackRow(self.preview_frame, name, info["zip_name"], cover, self._icon_hp).pack(fill="x", pady=(0, 6))
                total_tracks += 1

        self.track_count_label.configure(text=f"{total_tracks} track{'s' if total_tracks != 1 else ''}")
        self.stop_spinner(f"{total_tracks} tracks ready!")
        self.btn_analyze.configure(state="normal")
        self.btn_process.configure(state="normal", fg_color=PINK, hover_color="#f472b6", text_color="#ffffff")

    def start_processing(self):
        output_dir = self.output_sel.path
        if not output_dir:
            self.status.configure(text="Pick an output folder!", text_color=RED)
            return
        if not self.analyzed_data:
            self.status.configure(text="Analyze first!", text_color=RED)
            return

        self.btn_analyze.configure(state="disabled")
        self.btn_process.configure(state="disabled")
        self.progress.set(0)
        self.start_spinner("Embedding covers...")

        Thread(target=self.run_process, args=(output_dir,), daemon=True).start()

    def run_process(self, output_dir):
        total = len(self.analyzed_data)
        ok_count = 0

        for i, info in enumerate(self.analyzed_data, 1):
            zip_path = info["zip_path"]
            try:
                success = process_zip(zip_path, output_dir)
                if success:
                    ok_count += 1
            except Exception:
                pass

            self.after(0, lambda v=i / total: self.progress.set(v))

        self.after(0, lambda: self.stop_spinner(f"Done! {ok_count}/{total} ZIPs processed"))
        self.after(0, lambda: self.btn_analyze.configure(state="normal"))
        self.after(0, lambda: self.btn_process.configure(state="normal"))


if __name__ == "__main__":
    app = App()
    app.mainloop()
