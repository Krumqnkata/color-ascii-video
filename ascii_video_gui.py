import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

# Символи от най-тъмно към най-светло
ASCII_CHARS = " .:-=+*#%@"


class AsciiVideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Color ASCII Video Converter")
        self.root.geometry("920x700")
        self.root.configure(bg="#18181b")
        self.root.minsize(780, 580)

        self.video_path = None
        self.is_running = False
        self.stop_event = threading.Event()
        self.current_photo = None  # Референция за Tkinter изображението

        self._setup_styles()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#27272a", background="#22c55e", bordercolor="#27272a")

    def _build_ui(self):
        # --- Горен панел с настройки ---
        top_frame = tk.Frame(self.root, bg="#27272a", padx=15, pady=12)
        top_frame.pack(fill=tk.X, padx=12, pady=(12, 6))

        # Ред 1: Избор на файл
        file_row = tk.Frame(top_frame, bg="#27272a")
        file_row.pack(fill=tk.X, pady=(0, 10))

        self.btn_select = tk.Button(
            file_row, text="📁 Избери видео", command=self.select_video,
            bg="#3b82f6", fg="white", activebackground="#2563eb", activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=14, pady=5, cursor="hand2"
        )
        self.btn_select.pack(side=tk.LEFT)

        self.lbl_file = tk.Label(
            file_row, text="Няма избран файл", bg="#27272a", fg="#a1a1aa",
            font=("Segoe UI", 10), anchor="w"
        )
        self.lbl_file.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)

        # Ред 2: Параметри (Секунди, Ширина, Запис)
        controls_row = tk.Frame(top_frame, bg="#27272a")
        controls_row.pack(fill=tk.X)

        # Макс. секунди
        tk.Label(controls_row, text="Макс. секунди:", bg="#27272a", fg="#e4e4e7", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.var_seconds = tk.IntVar(value=15)
        self.spin_seconds = tk.Spinbox(
            controls_row, from_=1, to=300, textvariable=self.var_seconds, width=5,
            bg="#18181b", fg="white", buttonbackground="#3f3f46", relief=tk.FLAT, font=("Segoe UI", 10)
        )
        self.spin_seconds.pack(side=tk.LEFT, padx=(6, 18))

        # Ширина в символи
        tk.Label(controls_row, text="Детайлност (символи):", bg="#27272a", fg="#e4e4e7", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.var_width = tk.IntVar(value=110)
        self.scale_width = tk.Scale(
            controls_row, from_=50, to=200, orient=tk.HORIZONTAL, variable=self.var_width,
            bg="#27272a", fg="white", highlightthickness=0, troughcolor="#18181b",
            activebackground="#3b82f6", length=150, font=("Segoe UI", 8)
        )
        self.scale_width.pack(side=tk.LEFT, padx=(6, 18))

        # Чекбокс за запазване
        self.var_save = tk.BooleanVar(value=True)
        self.chk_save = tk.Checkbutton(
            controls_row, text="Запази като MP4", variable=self.var_save,
            bg="#27272a", fg="#e4e4e7", selectcolor="#18181b", activebackground="#27272a",
            activeforeground="white", font=("Segoe UI", 9), cursor="hand2"
        )
        self.chk_save.pack(side=tk.LEFT, padx=(0, 15))

        # Бутони Старт / Стоп
        self.btn_stop = tk.Button(
            controls_row, text="⏹ Стоп", command=self.stop_processing, state=tk.DISABLED,
            bg="#ef4444", fg="white", activebackground="#dc2626", activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
        )
        self.btn_stop.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_start = tk.Button(
            controls_row, text="▶ Старт", command=self.start_processing, state=tk.DISABLED,
            bg="#22c55e", fg="white", activebackground="#16a34a", activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
        )
        self.btn_start.pack(side=tk.RIGHT)

        # --- Среден панел: Преглед на видеото ---
        preview_container = tk.Frame(self.root, bg="#09090b", bd=1, relief=tk.SOLID)
        preview_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        self.lbl_preview = tk.Label(
            preview_container, text="Избери видео и натисни 'Старт'",
            bg="#09090b", fg="#71717a", font=("Consolas", 12)
        )
        self.lbl_preview.pack(fill=tk.BOTH, expand=True)

        # --- Долен панел: Прогрес и статус ---
        bottom_frame = tk.Frame(self.root, bg="#18181b", padx=12, pady=8)
        bottom_frame.pack(fill=tk.X)

        self.progress = ttk.Progressbar(bottom_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, 5))

        self.lbl_status = tk.Label(
            bottom_frame, text="Готовност", bg="#18181b", fg="#a1a1aa",
            font=("Segoe UI", 9), anchor="w"
        )
        self.lbl_status.pack(fill=tk.X)

    def select_video(self):
        path = filedialog.askopenfilename(
            title="Избери видео файл",
            filetypes=[
                ("Видео файлове", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("Всички файлове", "*.*")
            ]
        )
        if path:
            self.video_path = path
            self.lbl_file.config(text=os.path.basename(path), fg="#ffffff")
            self.btn_start.config(state=tk.NORMAL)
            self.lbl_status.config(text=f"Зареден файл: {path}")

    def _get_font(self, font_size=10):
        for font_name in ("consola.ttf", "DejaVuSansMono.ttf", "cour.ttf"):
            try:
                return ImageFont.truetype(font_name, font_size)
            except IOError:
                continue
        return ImageFont.load_default()

    def _frame_to_ascii_pil(self, frame, cols, font, char_w, char_h):
        h, w, _ = frame.shape
        aspect_ratio = h / w
        rows = max(1, int(cols * aspect_ratio * 0.55))

        small_bgr = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
        small_rgb = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2GRAY)

        out_w = cols * char_w
        out_h = rows * char_h
        canvas = Image.new("RGB", (out_w, out_h), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        num_chars = len(ASCII_CHARS)
        for y in range(rows):
            for x in range(cols):
                brightness = int(gray[y, x])
                char_idx = min(num_chars - 1, int((brightness / 256) * num_chars))
                char = ASCII_CHARS[char_idx]
                if char != " ":
                    r, g, b = small_rgb[y, x]
                    draw.text((x * char_w, y * char_h), char, fill=(int(r), int(g), int(b)), font=font)

        return canvas

    def start_processing(self):
        if not self.video_path or self.is_running:
            return

        self.is_running = True
        self.stop_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.progress["value"] = 0

        thread = threading.Thread(target=self._process_video, daemon=True)
        thread.start()

    def stop_processing(self):
        if self.is_running:
            self.stop_event.set()
            self.lbl_status.config(text="Спиране...")

    def _update_preview(self, pil_img, progress_val, status_text):
        if not self.is_running:
            return

        # Оразмеряваме прегледа така, че да пасва в прозореца без да реже картината
        box_w = max(200, self.lbl_preview.winfo_width() - 10)
        box_h = max(150, self.lbl_preview.winfo_height() - 10)

        img_w, img_h = pil_img.size
        scale = min(box_w / img_w, box_h / img_h)
        new_size = (max(1, int(img_w * scale)), max(1, int(img_h * scale)))

        preview_img = pil_img.resize(new_size, Image.Resampling.BILINEAR)
        photo = ImageTk.PhotoImage(preview_img)

        self.current_photo = photo
        self.lbl_preview.config(image=photo, text="")
        self.progress["value"] = progress_val
        self.lbl_status.config(text=status_text)

    def _process_video(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.root.after(0, lambda: messagebox.showerror("Грешка", "Неуспешно отваряне на видеото."))
            self.root.after(0, self._reset_ui)
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        max_sec = self.var_seconds.get()
        cols = self.var_width.get()
        save_file = self.var_save.get()

        max_frames = int(fps * max_sec)
        if total_video_frames > 0:
            max_frames = min(max_frames, total_video_frames)

        font = self._get_font(font_size=10)
        bbox = font.getbbox("A")
        char_w = bbox[2] - bbox[0]
        char_h = int((bbox[3] - bbox[1]) * 1.15)

        base, _ = os.path.splitext(self.video_path)
        output_path = f"{base}_ascii.mp4"
        writer = None

        frame_idx = 0
        delay = 1.0 / fps

        while cap.isOpened() and frame_idx < max_frames and not self.stop_event.is_set():
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            pil_ascii = self._frame_to_ascii_pil(frame, cols, font, char_w, char_h)

            if save_file:
                if writer is None:
                    w_out, h_out = pil_ascii.size
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(output_path, fourcc, fps, (w_out, h_out))
                bgr_frame = cv2.cvtColor(np.array(pil_ascii), cv2.COLOR_RGB2BGR)
                writer.write(bgr_frame)

            frame_idx += 1
            pct = (frame_idx / max_frames) * 100 if max_frames > 0 else 0
            cur_sec = frame_idx / fps
            status = f"Обработка: {cur_sec:.1f} / {max_frames / fps:.1f} сек. ({frame_idx}/{max_frames} кадъра)"

            self.root.after(0, self._update_preview, pil_ascii, pct, status)

            # Поддържа нормална скорост на възпроизвеждане, ако рендирането е по-бързо от FPS
            elapsed = time.time() - t0
            if elapsed < delay:
                time.sleep(delay - elapsed)

        cap.release()
        if writer:
            writer.release()

        final_msg = "Спряно от потребителя." if self.stop_event.is_set() else "Готово!"
        if save_file and frame_idx > 0:
            final_msg += f" Запазено в: {output_path}"

        self.root.after(0, lambda: self._reset_ui(final_msg))

    def _reset_ui(self, status_msg="Готовност"):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL if self.video_path else tk.DISABLED)
        self.btn_select.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text=status_msg)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AsciiVideoApp(root)
    root.mainloop()