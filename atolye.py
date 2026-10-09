# -*- coding: utf-8 -*-
"""
Atölye - Mühendis Kurulum Merkezi (Modern GUI & Kurulum Motoru)
Tamamen standart Python kütüphaneleri (tkinter, threading, subprocess, json) ile çalışır.
Harici paket bağımlılığı gerektirmez, doğrudan çalışır.
"""

import sys
import os
import json
import time
import shutil
import struct
import threading
import subprocess
import urllib.request
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox

# Windows DPI Awareness
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Program veritabanını içe aktar
try:
    from programlar_db import CATEGORIES, PROGRAMS, PRESETS
except ImportError:
    # Aynı dizinde doğrudan çalıştığında
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from programlar_db import CATEGORIES, PROGRAMS, PRESETS

# Konfigürasyon dosya yolu
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secilenler.json")

# Renk Paleti (Apple tarzı açık tema)
THEME = {
    "bg_darkest": "#ffffff",       # üst başlık
    "bg_main": "#f5f5f7",          # ana zemin
    "bg_panel": "#ececf1",         # kenar çubuğu ve alt panel
    "bg_card": "#ffffff",
    "bg_card_hover": "#f2f2f7",
    "bg_card_selected": "#eaf3ff",
    "border": "#e0e0e6",
    "border_light": "#c7c7cc",
    "accent_blue": "#0071e3",
    "accent_blue_dark": "#0062c4",
    "accent_purple": "#8944ab",
    "accent_green": "#248a3d",
    "accent_yellow": "#b25000",
    "accent_red": "#d70015",
    "text_primary": "#1d1d1f",
    "text_secondary": "#6e6e73",
    "text_muted": "#86868b",
    "terminal_bg": "#1c1c1e",
    "terminal_header": "#2c2c2e",
    "terminal_fg": "#30d158",
}

class SuperInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Atölye - Mühendis Kurulum Merkezi")
        win_h = min(900, max(700, self.root.winfo_screenheight() - 90))
        self.root.geometry(f"1200x{win_h}")
        self.root.minsize(1050, 700)
        self.root.configure(bg=THEME["bg_main"])

        # Durum Değişkenleri
        self.selected_vars = {}  # prog_id -> tk.BooleanVar
        self.status_labels = {}  # prog_id -> tk.Label
        self.card_frames = {}    # prog_id -> tk.Frame
        self.program_statuses = {}  # prog_id -> (text, color)
        self.current_process = None
        self.empty_lbl = None
        self.active_category = "all"
        self.search_query = ""
        self.is_installing = False
        self.cancel_requested = False
        self.show_terminal = True
        self.python_cmd = self.detect_python_cmd()

        # Son kayıtlı seçimleri yükle
        self.load_saved_selections()

        # Arayüz Bileşenlerini Kur
        self.setup_styles()
        self.build_ui()
        self.update_stats()
        self.refresh_program_list()

    def detect_python_cmd(self):
        """Python çalıştırma komutunu belirler"""
        if sys.executable and os.path.exists(sys.executable):
            exe = sys.executable
            if exe.lower().endswith("pythonw.exe"):
                alt = exe[:-5] + ".exe"
                if os.path.exists(alt):
                    return alt
            return exe
        elif shutil.which("py"):
            return "py"
        elif shutil.which("python"):
            return "python"
        elif shutil.which("python3"):
            return "python3"
        return "python"

    def load_saved_selections(self):
        """Kayıtlı seçimleri veya varsayılanları hazırlar"""
        saved = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except Exception:
                saved = {}

        for p in PROGRAMS:
            pid = p["id"]
            if pid in saved:
                self.selected_vars[pid] = tk.BooleanVar(value=saved[pid])
            else:
                self.selected_vars[pid] = tk.BooleanVar(value=p.get("default", True))
            # Değişiklik olduğunda kaydet
            self.selected_vars[pid].trace_add("write", lambda *args: self.on_selection_change())

    def save_selections(self):
        """Mevcut seçimleri JSON'a kaydeder"""
        data = {pid: var.get() for pid, var in self.selected_vars.items()}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def on_selection_change(self):
        self.save_selections()
        self.update_stats()
        self.update_category_badges()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Horizontal.TProgressbar",
                        troughcolor=THEME["bg_card"],
                        background=THEME["accent_blue"],
                        darkcolor=THEME["accent_blue"],
                        lightcolor=THEME["accent_blue"],
                        bordercolor=THEME["border"],
                        thickness=14)
        # Koyu kaydırma çubuğu
        style.configure("Dark.Vertical.TScrollbar",
                        troughcolor=THEME["bg_main"],
                        background=THEME["border_light"],
                        bordercolor=THEME["bg_main"],
                        arrowcolor=THEME["text_muted"],
                        lightcolor=THEME["border_light"],
                        darkcolor=THEME["border_light"])
        style.map("Dark.Vertical.TScrollbar",
                  background=[("active", THEME["accent_blue"])])

    @staticmethod
    def add_hover(widget, normal_bg, hover_bg):
        """Fare üzerine gelince renk değiştirir (devre dışı butonları atlar)"""
        def _enter(_e):
            try:
                if str(widget.cget("state")) != "disabled":
                    widget.configure(bg=hover_bg)
            except tk.TclError:
                widget.configure(bg=hover_bg)
        def _leave(_e):
            try:
                if str(widget.cget("state")) != "disabled":
                    widget.configure(bg=normal_bg)
            except tk.TclError:
                widget.configure(bg=normal_bg)
        widget.bind("<Enter>", _enter, add="+")
        widget.bind("<Leave>", _leave, add="+")

    def build_ui(self):
        # 1. ÜST BAŞLIK (HEADER)
        header_frame = tk.Frame(self.root, bg=THEME["bg_darkest"], padx=24, pady=16, relief="flat")
        header_frame.pack(side="top", fill="x")
        # Başlığın altında ince ayırıcı çizgi
        tk.Frame(self.root, height=1, bg=THEME["border"]).pack(side="top", fill="x")

        # Sol Başlık
        title_box = tk.Frame(header_frame, bg=THEME["bg_darkest"])
        title_box.pack(side="left")

        title_lbl = tk.Label(
            title_box,
            text="Atölye",
            font=("Segoe UI Semibold", 22),
            fg=THEME["text_primary"],
            bg=THEME["bg_darkest"]
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            title_box,
            text=f"Mühendis Kurulum Merkezi  ·  {len(PROGRAMS)} araç, tek tıkla kurulum",
            font=("Segoe UI", 10),
            fg=THEME["text_secondary"],
            bg=THEME["bg_darkest"]
        )
        sub_lbl.pack(anchor="w")

        # Sağ Arama ve İstatistik Kutusu
        top_right = tk.Frame(header_frame, bg=THEME["bg_darkest"])
        top_right.pack(side="right", fill="y")

        # Arama Çubuğu
        search_bg = "#e8e8ed"
        search_frame = tk.Frame(top_right, bg=search_bg, padx=12, pady=7)
        search_frame.pack(side="right", padx=(15, 0), pady=4)

        search_icon = tk.Label(search_frame, text="🔍", font=("Segoe UI", 10), fg=THEME["text_muted"], bg=search_bg)
        search_icon.pack(side="left")

        self.search_placeholder = "Program ara (docker, kicad, ai...)"
        self.search_entry = tk.Entry(
            search_frame,
            font=("Segoe UI", 10),
            bg=search_bg,
            fg=THEME["text_muted"],
            insertbackground=THEME["text_primary"],
            relief="flat",
            width=32
        )
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.pack(side="left", padx=6)

        def _focus_in(_e):
            if self.search_entry.get() == self.search_placeholder:
                self.search_entry.delete(0, "end")
                self.search_entry.configure(fg=THEME["text_primary"])

        def _focus_out(_e):
            if not self.search_entry.get():
                self.search_entry.insert(0, self.search_placeholder)
                self.search_entry.configure(fg=THEME["text_muted"])

        self.search_entry.bind("<FocusIn>", _focus_in)
        self.search_entry.bind("<FocusOut>", _focus_out)
        self.search_entry.bind("<KeyRelease>", self.on_search)

        # 2. ANA GÖVDE (SPLIT: SOL KENAR ÇUBUĞU + SAĞ İÇERİK)
        main_body = tk.Frame(self.root, bg=THEME["bg_main"])
        main_body.pack(side="top", fill="both", expand=True)

        # 2.A SOL KENAR ÇUBUĞU (KATEGORİLER & HAZIR PROFİLLER)
        sidebar = tk.Frame(main_body, bg=THEME["bg_panel"], width=290, padx=14, pady=14)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sol Panel Başlığı
        cat_head = tk.Label(sidebar, text="KATEGORİLER", font=("Segoe UI", 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_panel"])
        cat_head.pack(anchor="w", pady=(0, 6))

        # Kategori Butonları
        self.cat_buttons = {}
        for cat in CATEGORIES:
            btn_frame = tk.Frame(sidebar, bg=THEME["bg_panel"], cursor="hand2")
            btn_frame.pack(fill="x", pady=1)

            btn = tk.Label(
                btn_frame,
                text=f"{cat['icon']}  {cat['name']}",
                font=("Segoe UI", 9, "bold" if cat["id"] == "all" else "normal"),
                fg=THEME["accent_blue"] if cat["id"] == "all" else THEME["text_secondary"],
                bg=THEME["bg_card"] if cat["id"] == "all" else THEME["bg_panel"],
                padx=10,
                pady=4,
                anchor="w",
                cursor="hand2"
            )
            btn.pack(side="left", fill="x", expand=True)

            badge = tk.Label(
                btn_frame,
                text="0",
                font=("Segoe UI", 8, "bold"),
                fg=THEME["text_muted"],
                bg=THEME["bg_card"] if cat["id"] == "all" else THEME["bg_panel"],
                padx=6,
                pady=4
            )
            badge.pack(side="right")

            cid = cat["id"]
            btn.bind("<Button-1>", lambda e, c=cid: self.set_category(c))
            badge.bind("<Button-1>", lambda e, c=cid: self.set_category(c))
            btn_frame.bind("<Button-1>", lambda e, c=cid: self.set_category(c))

            self.cat_buttons[cid] = (btn, badge, btn_frame)

        # Ayırıcı
        sep = tk.Frame(sidebar, height=1, bg=THEME["border"])
        sep.pack(fill="x", pady=8)

        # Hazır Şablonlar / Profiller (Presets)
        preset_head = tk.Label(sidebar, text="HAZIR PROFİLLER", font=("Segoe UI", 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_panel"])
        preset_head.pack(anchor="w", pady=(0, 6))

        presets_list = [
            ("all", "🌟 Tümünü Seç"),
            ("none", "🧹 Temizle"),
            ("ai_engineer", "🤖 Yapay Zeka"),
            ("cyber_security", "🛡️ Siber Güvenlik"),
            ("design_media", "🎨 Tasarım & 3D"),
            ("hardware_embedded", "⚡ Donanım"),
            ("software_fullstack", "💻 Yazılım"),
            ("devops_cloud", "☁️ DevOps"),
        ]

        # Profiller 2 sütunlu ızgarada: sol panele sığar
        preset_grid = tk.Frame(sidebar, bg=THEME["bg_panel"])
        preset_grid.pack(fill="x")
        preset_grid.columnconfigure(0, weight=1, uniform="preset")
        preset_grid.columnconfigure(1, weight=1, uniform="preset")

        for i, (p_key, p_title) in enumerate(presets_list):
            p_btn = tk.Button(
                preset_grid,
                text=p_title,
                font=("Segoe UI", 8),
                fg=THEME["text_primary"],
                bg=THEME["bg_card"],
                activebackground=THEME["bg_card_hover"],
                activeforeground=THEME["text_primary"],
                relief="flat",
                anchor="w",
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda k=p_key: self.apply_preset(k)
            )
            p_btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            self.add_hover(p_btn, THEME["bg_card"], THEME["bg_card_hover"])

        # Sol Panel Alt İstatistik Kutusu
        stat_box = tk.Frame(sidebar, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1, padx=10, pady=8)
        # before=cat_head: alt kutu önce yer ayırır, küçük pencerede kesilmez
        stat_box.pack(side="bottom", fill="x", pady=(6, 0), before=cat_head)

        self.stat_label = tk.Label(
            stat_box,
            text="Seçilen: 0 / 0",
            font=("Segoe UI", 9, "bold"),
            fg=THEME["accent_blue"],
            bg=THEME["bg_card"],
            justify="left"
        )
        self.stat_label.pack(anchor="w")

        self.stat_sub = tk.Label(
            stat_box,
            text="Winget: 0 | Pip: 0",
            font=("Segoe UI", 8),
            fg=THEME["text_secondary"],
            bg=THEME["bg_card"],
            justify="left"
        )
        self.stat_sub.pack(anchor="w", pady=(2, 0))

        # 2.B SAĞ İÇERİK ALANI (PROGRAM KARTLARI LİSTESİ)
        content_frame = tk.Frame(main_body, bg=THEME["bg_main"])
        content_frame.pack(side="left", fill="both", expand=True)

        # Üst Araç Çubuğu (Kategori Başlığı + Hızlı Seçim Butonları)
        content_toolbar = tk.Frame(content_frame, bg=THEME["bg_main"], padx=18, pady=10)
        content_toolbar.pack(fill="x")

        self.current_cat_title = tk.Label(
            content_toolbar,
            text="🌟 Tüm Programlar",
            font=("Segoe UI", 13, "bold"),
            fg=THEME["text_primary"],
            bg=THEME["bg_main"]
        )
        self.current_cat_title.pack(side="left")

        # "Bu Kategoriyi Seç / Kaldır" Butonları
        quick_select_box = tk.Frame(content_toolbar, bg=THEME["bg_main"])
        quick_select_box.pack(side="right")

        select_all_btn = tk.Button(
            quick_select_box,
            text="✓ Bu Bölümü Seç",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["accent_blue"],
            bg=THEME["bg_panel"],
            activebackground=THEME["bg_card"],
            activeforeground=THEME["text_primary"],
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.select_current_category
        )
        select_all_btn.pack(side="left", padx=4)
        self.add_hover(select_all_btn, THEME["bg_panel"], THEME["bg_card_hover"])

        deselect_all_btn = tk.Button(
            quick_select_box,
            text="✕ Bu Bölümü Kaldır",
            font=("Segoe UI", 8),
            fg=THEME["text_secondary"],
            bg=THEME["bg_panel"],
            activebackground=THEME["bg_card"],
            activeforeground=THEME["text_primary"],
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.deselect_current_category
        )
        deselect_all_btn.pack(side="left", padx=4)
        self.add_hover(deselect_all_btn, THEME["bg_panel"], THEME["bg_card_hover"])

        # Kaydırılabilir Kart Alanı (Canvas + Scrollbar)
        list_container = tk.Frame(content_frame, bg=THEME["bg_main"], padx=16, pady=4)
        list_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_container, bg=THEME["bg_main"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview,
                                       style="Dark.Vertical.TScrollbar")

        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME["bg_main"])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=None, yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Fare Tekerleği Kaydırma
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 3. ALT KONTROL & TERMİNAL ALANI (FOOTER)
        footer_frame = tk.Frame(self.root, bg=THEME["bg_panel"], padx=18, pady=10, highlightbackground=THEME["border"], highlightthickness=1)
        footer_frame.pack(side="bottom", fill="x")

        # Alt Kontrol Çubuğu (Butonlar + İlerleme)
        control_bar = tk.Frame(footer_frame, bg=THEME["bg_panel"])
        control_bar.pack(fill="x", pady=(0, 6))

        # Sol Bilgi & İlerleme
        progress_info_box = tk.Frame(control_bar, bg=THEME["bg_panel"])
        progress_info_box.pack(side="left", fill="x", expand=True, padx=(0, 15))

        self.status_text_lbl = tk.Label(
            progress_info_box,
            text="Hazır. Kurulacak programları seçin ve 'Kuruluma Başla'ya basın.",
            font=("Segoe UI", 9),
            fg=THEME["text_secondary"],
            bg=THEME["bg_panel"],
            anchor="w"
        )
        self.status_text_lbl.pack(fill="x", pady=(0, 4))

        self.progress_bar = ttk.Progressbar(
            progress_info_box,
            style="Dark.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate"
        )
        self.progress_bar.pack(fill="x")

        # Sağ Butonlar
        btn_action_box = tk.Frame(control_bar, bg=THEME["bg_panel"])
        btn_action_box.pack(side="right")

        self.terminal_toggle_btn = tk.Button(
            btn_action_box,
            text="📋 Konsolu Gizle",
            font=("Segoe UI", 9),
            fg=THEME["text_secondary"],
            bg=THEME["bg_card"],
            activebackground=THEME["bg_card_hover"],
            activeforeground=THEME["text_primary"],
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.toggle_terminal
        )
        self.terminal_toggle_btn.pack(side="left", padx=6)
        self.add_hover(self.terminal_toggle_btn, THEME["bg_card"], THEME["bg_card_hover"])

        self.cancel_btn = tk.Button(
            btn_action_box,
            text="⏹️ İptal Et",
            font=("Segoe UI", 9, "bold"),
            fg=THEME["text_primary"],
            bg=THEME["bg_card"],
            activebackground=THEME["accent_red"],
            relief="flat",
            padx=12,
            pady=6,
            state="disabled",
            command=self.cancel_installation
        )
        self.cancel_btn.pack(side="left", padx=6)

        self.install_btn = tk.Button(
            btn_action_box,
            text="SEÇİLENLERİ KUR (0)",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=THEME["accent_blue"],
            activebackground=THEME["accent_blue_dark"],
            activeforeground="#ffffff",
            disabledforeground=THEME["text_muted"],
            relief="flat",
            padx=20,
            pady=6,
            cursor="hand2",
            command=self.start_installation
        )
        self.install_btn.pack(side="left", padx=6)
        self.add_hover(self.install_btn, THEME["accent_blue"], THEME["accent_blue_dark"])

        # 4. CANLI TERMİNAL ÇIKTI KUTUSU (DRAWER)
        self.terminal_frame = tk.Frame(footer_frame, bg=THEME["terminal_bg"], highlightbackground=THEME["border"], highlightthickness=1)
        self.terminal_frame.pack(fill="x", pady=(6, 0))

        terminal_header = tk.Frame(self.terminal_frame, bg=THEME["terminal_header"], padx=8, pady=3)
        terminal_header.pack(fill="x")

        term_title = tk.Label(terminal_header, text="CANLI KURULUM KONSOLU (Winget & Pip Stream)", font=("Consolas", 8, "bold"), fg="#aeaeb2", bg=THEME["terminal_header"])
        term_title.pack(side="left")

        term_clear_btn = tk.Button(
            terminal_header,
            text="Temizle",
            font=("Segoe UI", 7),
            fg="#aeaeb2",
            bg=THEME["terminal_header"],
            relief="flat",
            cursor="hand2",
            command=self.clear_terminal
        )
        term_clear_btn.pack(side="right")

        self.terminal_text = tk.Text(
            self.terminal_frame,
            font=("Consolas", 9),
            bg=THEME["terminal_bg"],
            fg=THEME["terminal_fg"],
            insertbackground=THEME["terminal_fg"],
            height=4,
            relief="flat",
            wrap="char"
        )
        self.terminal_text.pack(fill="both", expand=True, padx=6, pady=4)
        self.log_to_terminal("Sistem hazır. Python sürümü: " + sys.version.split()[0] + " | Komut: " + self.python_cmd)

        # Kartları bir kere oluştur ve hazırla
        self.create_all_cards()

    def _on_mousewheel(self, event):
        if event.widget == self.terminal_text:
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def toggle_terminal(self):
        self.show_terminal = not self.show_terminal
        if self.show_terminal:
            self.terminal_frame.pack(fill="x", pady=(6, 0))
            self.terminal_toggle_btn.configure(text="📋 Konsolu Gizle")
        else:
            self.terminal_frame.pack_forget()
            self.terminal_toggle_btn.configure(text="📋 Konsolu Göster")

    def log_to_terminal(self, message):
        def _append():
            self.terminal_text.insert(tk.END, message + "\n")
            self.terminal_text.see(tk.END)
        self.root.after(0, _append)

    def clear_terminal(self):
        self.terminal_text.delete("1.0", tk.END)

    def set_category(self, cat_id):
        self.active_category = cat_id
        # Kategori butonlarının stilini güncelle
        for cid, (btn, badge, frame) in self.cat_buttons.items():
            if cid == cat_id:
                btn.configure(fg=THEME["accent_blue"], bg=THEME["bg_card"], font=("Segoe UI", 9, "bold"))
                badge.configure(bg=THEME["bg_card"], fg=THEME["accent_blue"])
                frame.configure(bg=THEME["bg_card"])
            else:
                btn.configure(fg=THEME["text_secondary"], bg=THEME["bg_panel"], font=("Segoe UI", 9, "normal"))
                badge.configure(bg=THEME["bg_panel"], fg=THEME["text_muted"])
                frame.configure(bg=THEME["bg_panel"])

        # Başlığı güncelle
        cat_obj = next((c for c in CATEGORIES if c["id"] == cat_id), None)
        if cat_obj:
            self.current_cat_title.configure(text=f"{cat_obj['icon']} {cat_obj['name']}")

        self.refresh_program_list()

    def on_search(self, event=None):
        text = self.search_entry.get().strip()
        if text == self.search_placeholder:
            text = ""
        self.search_query = text.lower()
        self.refresh_program_list()

    def apply_preset(self, preset_key):
        if preset_key not in PRESETS:
            return
        preset = PRESETS[preset_key]
        target_ids = set(preset["ids"])

        for pid, var in self.selected_vars.items():
            var.set(pid in target_ids)

        self.update_stats()
        self.update_category_badges()
        self.log_to_terminal(f"[ŞABLON SEÇİLDİ] {preset['name']} uygulandı ({len(target_ids)} program).")

    def select_current_category(self):
        items = self.get_visible_programs()
        for p in items:
            self.selected_vars[p["id"]].set(True)
        self.update_stats()
        self.update_category_badges()

    def deselect_current_category(self):
        items = self.get_visible_programs()
        for p in items:
            self.selected_vars[p["id"]].set(False)
        self.update_stats()
        self.update_category_badges()

    def get_visible_programs(self):
        items = []
        for p in PROGRAMS:
            # Kategori kontrolü
            if self.active_category != "all" and p["category"] != self.active_category:
                continue
            # Arama filtresi
            if self.search_query:
                q = self.search_query
                name_match = q in p["name"].lower()
                desc_match = q in p["desc"].lower()
                tag_match = any(q in t.lower() for t in p.get("tags", []))
                pkg_match = q in p.get("package_id", "").lower()
                if not (name_match or desc_match or tag_match or pkg_match):
                    continue
            items.append(p)
        return items

    def create_all_cards(self):
        self.card_frames.clear()
        self.status_labels.clear()

        self.empty_lbl = tk.Label(
            self.scrollable_frame,
            text="Aramanıza veya seçili kategoriye uygun program bulunamadı.",
            font=("Segoe UI", 11),
            fg=THEME["text_muted"],
            bg=THEME["bg_main"],
            pady=40
        )

        for p in PROGRAMS:
            self.create_program_card(p)

    def refresh_program_list(self):
        visible_programs = self.get_visible_programs()
        visible_ids = {p["id"] for p in visible_programs}

        if not visible_programs:
            for pid, card in self.card_frames.items():
                card.pack_forget()
            if self.empty_lbl:
                self.empty_lbl.pack(fill="x")
        else:
            if self.empty_lbl:
                self.empty_lbl.pack_forget()
            for p in PROGRAMS:
                pid = p["id"]
                if pid in self.card_frames:
                    card = self.card_frames[pid]
                    if pid in visible_ids:
                        card.pack(fill="x", pady=4, padx=2)
                    else:
                        card.pack_forget()

        self.update_category_badges()

    def create_program_card(self, p):
        pid = p["id"]
        var = self.selected_vars[pid]

        # Kart Çerçevesi
        card = tk.Frame(
            self.scrollable_frame,
            bg=THEME["bg_card_selected"] if var.get() else THEME["bg_card"],
            highlightbackground=THEME["accent_blue"] if var.get() else THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=12
        )
        self.card_frames[pid] = card

        # Sol: Checkbox ve Bilgiler
        left_box = tk.Frame(card, bg=card.cget("bg"))
        left_box.pack(side="left", fill="both", expand=True)

        # Üst Satır: Checkbox + İsim + Tip Rozeti
        top_line = tk.Frame(left_box, bg=card.cget("bg"))
        top_line.pack(fill="x", anchor="w")

        # Özel Checkbutton
        cb = tk.Checkbutton(
            top_line,
            variable=var,
            text="",
            bg=card.cget("bg"),
            fg=THEME["accent_blue"],
            activebackground=card.cget("bg"),
            activeforeground=THEME["accent_blue"],
            selectcolor="#ffffff",
            relief="flat",
            cursor="hand2"
        )
        cb.pack(side="left", padx=(0, 6))

        # Başlık Etiketi
        title_lbl = tk.Label(
            top_line,
            text=p["name"],
            font=("Segoe UI", 10, "bold"),
            fg=THEME["text_primary"],
            bg=card.cget("bg"),
            cursor="hand2"
        )
        title_lbl.pack(side="left")

        # Tıklanabilir Yapma
        def _toggle(event=None):
            var.set(not var.get())
        title_lbl.bind("<Button-1>", _toggle)

        # Tip Rozeti
        ptype = p.get("type", "winget")
        if ptype == "pip":
            badge_text = "PIP PAKETİ"
            badge_color = THEME["accent_purple"]
        elif ptype == "git_repo":
            badge_text = "GITHUB REPO"
            badge_color = THEME["accent_yellow"]
        elif ptype == "direct_zip":
            badge_text = "PORTATİF ZIP"
            badge_color = "#007aa3"
        elif ptype == "direct_exe":
            badge_text = "DOĞRUDAN İNDİR"
            badge_color = THEME["accent_green"]
        else:
            badge_text = "WINGET SİSTEM"
            badge_color = THEME["accent_blue"]

        type_badge = tk.Label(
            top_line,
            text=badge_text,
            font=("Segoe UI", 7, "bold"),
            fg=badge_color,
            bg=THEME["bg_panel"],
            padx=6,
            pady=2
        )
        type_badge.pack(side="left", padx=(10, 0))

        # Alt Satır: Açıklama ve Paket Kimliği
        desc_lbl = tk.Label(
            left_box,
            text=f"{p['desc']}  •  [ {p['package_id']} ]",
            font=("Segoe UI", 8),
            fg=THEME["text_secondary"],
            bg=card.cget("bg"),
            anchor="w",
            cursor="hand2"
        )
        desc_lbl.pack(fill="x", anchor="w", pady=(3, 0))
        desc_lbl.bind("<Button-1>", _toggle)

        # Sağ: Durum Rozeti (Bekliyor / Kuruluyor / Başarılı)
        cur_text, cur_color = self.program_statuses.get(pid, ("⚪ Bekliyor", THEME["text_muted"]))
        status_lbl = tk.Label(
            card,
            text=cur_text,
            font=("Segoe UI", 9, "bold"),
            fg=cur_color,
            bg=card.cget("bg"),
            padx=10,
            pady=4
        )
        status_lbl.pack(side="right")
        self.status_labels[pid] = status_lbl

        # Kartın her yerine tıklayınca seç / kaldır
        for w in (card, left_box, top_line, type_badge, status_lbl):
            w.bind("<Button-1>", _toggle)
            w.configure(cursor="hand2")

        # Üzerine gelince hafif vurgu (seçili değilse)
        def _card_enter(_e):
            if not var.get():
                card.configure(highlightbackground=THEME["border_light"])
        def _card_leave(_e):
            if not var.get():
                card.configure(highlightbackground=THEME["border"])
        card.bind("<Enter>", _card_enter)
        card.bind("<Leave>", _card_leave)

        # Checkbox değiştiğinde kart rengini dinamik güncelle
        def _on_val_change(*args):
            if not card.winfo_exists():
                return
            is_checked = var.get()
            bg_c = THEME["bg_card_selected"] if is_checked else THEME["bg_card"]
            border_c = THEME["accent_blue"] if is_checked else THEME["border"]
            card.configure(bg=bg_c, highlightbackground=border_c)
            left_box.configure(bg=bg_c)
            top_line.configure(bg=bg_c)
            cb.configure(bg=bg_c, activebackground=bg_c)
            title_lbl.configure(bg=bg_c)
            desc_lbl.configure(bg=bg_c)
            status_lbl.configure(bg=bg_c)

        var.trace_add("write", _on_val_change)

    def update_stats(self):
        selected_count = sum(1 for v in self.selected_vars.values() if v.get())
        total_count = len(PROGRAMS)

        winget_count = sum(1 for p in PROGRAMS if self.selected_vars[p["id"]].get() and p.get("type") == "winget")
        pip_count = sum(1 for p in PROGRAMS if self.selected_vars[p["id"]].get() and p.get("type") == "pip")
        other_count = selected_count - winget_count - pip_count

        self.stat_label.configure(text=f"Seçilen: {selected_count} / {total_count}")
        if other_count > 0:
            self.stat_sub.configure(text=f"Winget: {winget_count} | Pip: {pip_count} | Git/Zip: {other_count}")
        else:
            self.stat_sub.configure(text=f"Winget: {winget_count} | Pip: {pip_count}")
        self.install_btn.configure(text=f"SEÇİLENLERİ KUR ({selected_count})")

    def update_category_badges(self):
        for cat in CATEGORIES:
            cid = cat["id"]
            if cid not in self.cat_buttons:
                continue
            if cid == "all":
                sel = sum(1 for v in self.selected_vars.values() if v.get())
                tot = len(PROGRAMS)
            else:
                cat_progs = [p for p in PROGRAMS if p["category"] == cid]
                sel = sum(1 for p in cat_progs if self.selected_vars[p["id"]].get())
                tot = len(cat_progs)

            _, badge_lbl, _ = self.cat_buttons[cid]
            badge_lbl.configure(text=f"{sel}/{tot}")

    # -------------------------------------------------------------
    # KURULUM MOTORU & ARKA PLAN İŞLEMLERİ
    # -------------------------------------------------------------
    def start_installation(self):
        if self.is_installing:
            return

        selected_programs = [p for p in PROGRAMS if self.selected_vars[p["id"]].get()]
        if not selected_programs:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen kurmak istediğiniz en az bir programı tikleyin.")
            return

        confirm = messagebox.askyesno(
            "Kurulum Onayı",
            f"Seçilen {len(selected_programs)} adet program ve kütüphane kurulacak.\n\nİşlem arka planda sessizce yürütülecek ve canlı konsoldan izlenebilecek.\n\nDevam etmek istiyor musunuz?"
        )
        if not confirm:
            return

        self.is_installing = True
        self.cancel_requested = False
        self.install_btn.configure(state="disabled", bg=THEME["border"], text="Kuruluyor...")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.configure(maximum=len(selected_programs), value=0)

        # Kurulum İş Parçacığını Başlat
        thread = threading.Thread(target=self._run_install_thread, args=(selected_programs,), daemon=True)
        thread.start()

    def cancel_installation(self):
        if self.is_installing:
            self.cancel_requested = True
            self.log_to_terminal("\n[DURDURMA TALEBİ] Kullanıcı iptal butonuna bastı. İşlem durduruluyor...")
            self.status_text_lbl.configure(text="İptal ediliyor... Lütfen bekleyin.")
            if self.current_process and self.current_process.poll() is None:
                try:
                    self.current_process.terminate()
                except Exception:
                    pass

    def set_program_status(self, pid, text, color):
        self.program_statuses[pid] = (text, color)
        def _update():
            if pid in self.status_labels and self.status_labels[pid].winfo_exists():
                self.status_labels[pid].configure(text=text, fg=color)
        self.root.after(0, _update)

    def _run_install_thread(self, target_programs):
        total = len(target_programs)
        success_count = 0
        failed_count = 0
        skipped_count = 0

        self.log_to_terminal("=" * 60)
        self.log_to_terminal(f"ATÖLYE KURULUMU BAŞLADI: Toplam {total} öğe")
        self.log_to_terminal("=" * 60)

        # 32-bit Python'da PyTorch, OpenCV, scikit-image gibi paketler hazır gelmez
        if struct.calcsize("P") * 8 == 32 and any(p.get("type") == "pip" for p in target_programs):
            self.log_to_terminal("⚠ UYARI: 32-bit Python kullanılıyor. Büyük pip paketleri (torch, opencv vb.) "
                                 "kurulamayabilir. 64-bit Python 3.12 önerilir.")

        for idx, p in enumerate(target_programs, start=1):
            if self.cancel_requested:
                self.log_to_terminal("\n[İPTAL EDİLDİ] Kurulum işlemi kullanıcı tarafından durduruldu.")
                self.set_program_status(p["id"], "⏹️ İptal Edildi", THEME["accent_yellow"])
                break

            pid = p["id"]
            pname = p["name"]
            ptype = p.get("type", "winget")
            pkg_id = p["package_id"]

            self.root.after(0, lambda t=f"Kuruluyor ({idx}/{total}): {pname}...": self.status_text_lbl.configure(text=t))
            self.set_program_status(pid, "🔄 Kuruluyor...", THEME["accent_blue"])
            self.log_to_terminal(f"\n▶ [{idx}/{total}] {pname} ({ptype.upper()}: {pkg_id}) kuruluyor...")

            start_t = time.time()

            try:
                tools_dir = os.path.join(os.path.expanduser("~"), "Engineering_Tools")
                os.makedirs(tools_dir, exist_ok=True)

                if ptype == "pip":
                    cmd = [self.python_cmd, "-m", "pip", "install", "--upgrade", "--no-warn-script-location"] + pkg_id.split()
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    )
                    for line in iter(self.current_process.stdout.readline, ""):
                        clean_line = line.strip()
                        if clean_line:
                            self.log_to_terminal(f"   {clean_line}")
                    self.current_process.stdout.close()
                    return_code = self.current_process.wait()
                    self.current_process = None

                elif ptype == "git_repo":
                    target_dir = os.path.join(tools_dir, pid)
                    if os.path.exists(target_dir) and os.path.isdir(os.path.join(target_dir, ".git")):
                        self.log_to_terminal(f"   [GÜNCELLEME] Mevcut repo güncelleniyor: {target_dir}")
                        cmd = ["git", "-c", "core.longpaths=true", "-C", target_dir, "pull"]
                    else:
                        self.log_to_terminal(f"   [GİT KLONLA] {pkg_id} indiriliyor -> {target_dir}")
                        # core.longpaths: Windows'ta 260 karakter yol sınırı hatasını önler
                        cmd = ["git", "-c", "core.longpaths=true", "clone", "--depth", "1", pkg_id, target_dir]

                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    )
                    for line in iter(self.current_process.stdout.readline, ""):
                        clean_line = line.strip()
                        if clean_line:
                            self.log_to_terminal(f"   {clean_line}")
                    self.current_process.stdout.close()
                    return_code = self.current_process.wait()
                    self.current_process = None

                    # Eğer requirements.txt varsa bağımlılıkları yükle
                    req_file = os.path.join(target_dir, "requirements.txt")
                    if return_code == 0 and os.path.exists(req_file) and not self.cancel_requested:
                        self.log_to_terminal("   [PIP BAĞIMLILIKLARI] requirements.txt kuruluyor...")
                        pip_cmd = [self.python_cmd, "-m", "pip", "install", "-r", req_file, "--no-warn-script-location"]
                        self.current_process = subprocess.Popen(
                            pip_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                        )
                        for line in iter(self.current_process.stdout.readline, ""):
                            clean_line = line.strip()
                            if clean_line:
                                self.log_to_terminal(f"   {clean_line}")
                        self.current_process.stdout.close()
                        self.current_process.wait()
                        self.current_process = None

                    # Başlatıcı .bat dosyası oluştur
                    launcher_script = p.get("launcher_cmd")
                    if return_code == 0 and launcher_script:
                        bat_path = os.path.join(target_dir, f"{pid}_baslat.bat")
                        try:
                            with open(bat_path, "w", encoding="utf-8") as bf:
                                bf.write(f"@echo off\ncd /d \"%~dp0\"\n{launcher_script}\npause\n")
                            self.log_to_terminal(f"   [BAŞLATICI OLUŞTURULDU] {bat_path}")
                        except Exception:
                            pass

                elif ptype == "direct_zip":
                    target_dir = os.path.join(tools_dir, pid)
                    os.makedirs(target_dir, exist_ok=True)
                    temp_zip = os.path.join(tools_dir, f"{pid}_temp.zip")
                    self.log_to_terminal(f"   [İNDİRİLİYOR] {pkg_id}")

                    req = urllib.request.Request(pkg_id, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=30) as resp, open(temp_zip, "wb") as out_f:
                        total_sz = resp.getheader("Content-Length")
                        total_bytes = int(total_sz) if total_sz and total_sz.isdigit() else 0
                        dl_bytes = 0
                        while True:
                            if self.cancel_requested:
                                break
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            out_f.write(chunk)
                            dl_bytes += len(chunk)
                            if total_bytes > 0:
                                pct = int(dl_bytes * 100 / total_bytes)
                                if dl_bytes % (65536 * 16) == 0 or dl_bytes == total_bytes:
                                    self.log_to_terminal(f"   İlerleme: %{pct} ({dl_bytes // 1048576} MB / {total_bytes // 1048576} MB)")

                    if not self.cancel_requested:
                        self.log_to_terminal(f"   [ZIP AÇILIYOR] {target_dir} dizinine çıkartılıyor...")
                        with zipfile.ZipFile(temp_zip, "r") as z:
                            # Zip-slip koruması: hedef klasör dışına yazılmasını engelle
                            base = os.path.realpath(target_dir)
                            for member in z.namelist():
                                dest = os.path.realpath(os.path.join(target_dir, member))
                                if dest != base and not dest.startswith(base + os.sep):
                                    raise ValueError(f"Güvensiz zip girdisi: {member}")
                            z.extractall(target_dir)
                        try:
                            os.remove(temp_zip)
                        except Exception:
                            pass
                        self.log_to_terminal(f"   [KONUM] {target_dir}")
                        return_code = 0
                    else:
                        try:
                            if os.path.exists(temp_zip):
                                os.remove(temp_zip)
                        except Exception:
                            pass
                        return_code = -1

                else:
                    cmd = [
                        "winget", "install",
                        "--id", pkg_id,
                        "-e",
                        "--silent",
                        "--accept-source-agreements",
                        "--accept-package-agreements",
                        "--disable-interactivity"
                    ]
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    )
                    for line in iter(self.current_process.stdout.readline, ""):
                        clean_line = line.strip()
                        if clean_line:
                            self.log_to_terminal(f"   {clean_line}")
                    self.current_process.stdout.close()
                    return_code = self.current_process.wait()
                    self.current_process = None

                elapsed = int(time.time() - start_t)

                if self.cancel_requested:
                    self.set_program_status(pid, "⏹️ İptal Edildi", THEME["accent_yellow"])
                    self.log_to_terminal(f"⏹ [{pname}] Kurulum durduruldu.")
                    break

                already_installed_codes = [
                    2316632107, -1978335189,
                    2316632084, -1978335212,
                    2316632109, -1978335187,
                    2316632329, -1978334967
                ]

                if return_code == 0:
                    self.set_program_status(pid, "✅ Kuruldu", THEME["accent_green"])
                    self.log_to_terminal(f"✔ [{pname}] Başarıyla kuruldu! ({elapsed} sn)")
                    success_count += 1
                elif return_code == 3010:
                    self.set_program_status(pid, "✅ Kuruldu (Yeniden Başlatma)", THEME["accent_green"])
                    self.log_to_terminal(f"✔ [{pname}] Başarıyla kuruldu (Yeniden başlatma gerekebilir). ({elapsed} sn)")
                    success_count += 1
                elif return_code in already_installed_codes:
                    self.set_program_status(pid, "⭐ Zaten Kurulu", THEME["accent_yellow"])
                    self.log_to_terminal(f"⭐ [{pname}] Zaten sisteminizde mevcut.")
                    skipped_count += 1
                else:
                    self.set_program_status(pid, f"❌ Hata ({return_code})", THEME["accent_red"])
                    self.log_to_terminal(f"✖ [{pname}] Kurulum başarısız oldu (Çıkış Kodu: {return_code})")
                    failed_count += 1

            except Exception as e:
                self.current_process = None
                if self.cancel_requested:
                    self.set_program_status(pid, "⏹️ İptal Edildi", THEME["accent_yellow"])
                    break
                self.set_program_status(pid, "❌ Hata", THEME["accent_red"])
                self.log_to_terminal(f"✖ [{pname}] Çalıştırma Hatası: {str(e)}")
                failed_count += 1

            # İlerleme Çubuğunu Güncelle
            self.root.after(0, lambda v=idx: self.progress_bar.configure(value=v))

        # Kurulum Sonu Raporu
        self.is_installing = False
        def _finish():
            self.current_process = None
            selected_count = sum(1 for v in self.selected_vars.values() if v.get())
            self.install_btn.configure(state="normal", bg=THEME["accent_blue"], text=f"SEÇİLENLERİ KUR ({selected_count})")
            self.cancel_btn.configure(state="disabled")

            if self.cancel_requested:
                self.status_text_lbl.configure(text=f"Kurulum durduruldu. Başarılı: {success_count} | Zaten Kurulu: {skipped_count} | Hatalı: {failed_count}")
                self.log_to_terminal("\n" + "=" * 60)
                self.log_to_terminal("⏹️ KURULUM İŞLEMİ İPTAL EDİLDİ!")
                self.log_to_terminal(f"Tamamlanan: {success_count} | Atlanan/Kurulu: {skipped_count} | Hata: {failed_count}")
                self.log_to_terminal("=" * 60)
                messagebox.showwarning("Kurulum Durduruldu", "Kurulum işlemi kullanıcı isteğiyle durduruldu.")
            else:
                self.status_text_lbl.configure(text=f"Kurulum bitti! Başarılı: {success_count} | Zaten Kurulu: {skipped_count} | Hatalı: {failed_count}")
                self.log_to_terminal("\n" + "=" * 60)
                self.log_to_terminal("🎉 KURULUM İŞLEMİ TAMAMLANDI!")
                self.log_to_terminal(f"Toplam: {total} | Başarılı: {success_count} | Atlanan/Kurulu: {skipped_count} | Hata: {failed_count}")
                self.log_to_terminal("=" * 60)

                msg = (
                    f"Kurulum işlemi tamamlandı!\n\n"
                    f"✅ Başarıyla Kurulan: {success_count}\n"
                    f"⭐ Zaten Kurulu Olan: {skipped_count}\n"
                    f"❌ Hata Oluşan: {failed_count}\n\n"
                    f"Detaylı logları canlı konsoldan inceleyebilirsiniz."
                )
                messagebox.showinfo("Kurulum Tamamlandı", msg)

        self.root.after(0, _finish)


def main():
    root = tk.Tk()
    app = SuperInstallerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
