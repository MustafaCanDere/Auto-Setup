# -*- coding: utf-8 -*-
"""
Atölye - Mühendis Kurulum Merkezi (Modern GUI & Kurulum Motoru)
Tamamen standart Python kütüphaneleri (tkinter, threading, subprocess, json) ile çalışır.
Harici paket bağımlılığı gerektirmez, doğrudan çalışır.
"""

import sys
import os
import json
import re
import time
import shutil
import struct
import threading
import subprocess
import urllib.request
import zipfile
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

# Windows DPI Awareness
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Atolye.exe olarak paketlendiyse (PyInstaller) dosyalar exe'nin yanında tutulur
IS_FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable if IS_FROZEN else os.path.abspath(__file__))

# Program veritabanını içe aktar
try:
    from programlar_db import CATEGORIES, PROGRAMS, PRESETS
except ImportError:
    # Aynı dizinde doğrudan çalıştığında
    sys.path.append(APP_DIR)
    from programlar_db import CATEGORIES, PROGRAMS, PRESETS

# Konfigürasyon dosya yolu
CONFIG_FILE = os.path.join(APP_DIR, "secilenler.json")

# Renk Paleti (Apple tarzı açık tema)
THEME = {
    "bg_darkest": "#f5f5f7",       # üst başlık (ana zeminle aynı, yumuşak geçiş)
    "bg_main": "#f5f5f7",          # ana zemin
    "bg_panel": "#ededf2",         # kenar çubuğu ve alt panel
    "bg_card": "#ffffff",
    "bg_card_hover": "#f4f4f8",
    "bg_card_selected": "#eef5ff",
    "border": "#ececf1",           # neredeyse görünmez kart kenarı
    "border_light": "#d9d9e0",
    "border_selected": "#a9cdf7",  # seçili kartın yumuşak mavi kenarı
    "accent_blue": "#0071e3",
    "accent_blue_dark": "#0062c4",
    "accent_purple": "#8944ab",
    "accent_green": "#248a3d",
    "accent_yellow": "#b25000",
    "accent_red": "#d70015",
    "accent_indigo": "#5856d6",
    "text_primary": "#1d1d1f",
    "text_secondary": "#6e6e73",
    "text_muted": "#86868b",
    "terminal_bg": "#1c1c1e",
    "terminal_header": "#2c2c2e",
    "terminal_fg": "#30d158",
}

# -------------------------------------------------------------
# İNDİRME İLERLEMESİ: winget / pip / git çıktısından ilerleme okuma
# -------------------------------------------------------------
_UNITS = {
    "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3,
    "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3,
}
_NUM = r"(\d+(?:[.,]\d+)?)"
_UNIT = r"(B|KB|MB|GB|KiB|MiB|GiB)"
_RE_PIP_RAW = re.compile(r"^Progress (\d+) of (\d+)\s*$")
_RE_PIP_START = re.compile(r"Downloading\s+(\S+)\s+\(" + _NUM + r"\s*" + _UNIT + r"\)", re.I)
_RE_GIT = re.compile(r"Receiving objects:\s+(\d{1,3})%.*?(?:,\s*" + _NUM + r"\s*" + _UNIT + r")?(?:\s*\||\s*$)", re.I)
_RE_SIZE_PAIR = re.compile(_NUM + r"\s*" + _UNIT + r"\s*/\s*" + _NUM + r"\s*" + _UNIT, re.I)
_RE_BARE_PCT = re.compile(r"^\W*(\d{1,3}(?:[.,]\d+)?)\s*%\W*$")


def _to_bytes(num, unit):
    return int(float(num.replace(",", ".")) * _UNITS[unit.upper()])


def parse_download_progress(line):
    """Tek bir çıktı satırından indirme ilerlemesini çıkarır.

    Dönüş: {"done": bayt|None, "total": bayt|None, "pct": 0-100|None, "name": str|None,
            "start": bool} ya da ilerleme satırı değilse None.
    """
    s = line.strip()
    if not s:
        return None

    m = _RE_PIP_RAW.match(s)  # pip >= 24.1 --progress-bar raw
    if m:
        done, total = int(m.group(1)), int(m.group(2))
        return {"done": done, "total": total or None,
                "pct": (done * 100.0 / total) if total else None, "name": None, "start": False}

    m = _RE_PIP_START.search(s)  # "Downloading torch-2.5.whl (2.3 GB)"
    if m:
        return {"done": 0, "total": _to_bytes(m.group(2), m.group(3)), "pct": 0.0,
                "name": m.group(1).rsplit("/", 1)[-1], "start": True}

    m = _RE_GIT.search(s)  # "Receiving objects:  45% (123/456), 12.34 MiB | 2.10 MiB/s"
    if m:
        done = _to_bytes(m.group(2), m.group(3)) if m.group(2) else None
        return {"done": done, "total": None, "pct": float(m.group(1)), "name": None, "start": False}

    m = _RE_SIZE_PAIR.search(s)  # winget: "████▒▒▒  120 MB / 286 MB"
    if m:
        done, total = _to_bytes(m.group(1), m.group(2)), _to_bytes(m.group(3), m.group(4))
        if total > 0 and done <= total:
            return {"done": done, "total": total, "pct": done * 100.0 / total,
                    "name": None, "start": False}

    m = _RE_BARE_PCT.match(s)  # winget boyut bilinmiyorsa: "████▒▒▒  45%"
    if m:
        pct = float(m.group(1).replace(",", "."))
        if 0 <= pct <= 100:
            return {"done": None, "total": None, "pct": pct, "name": None, "start": False}
    return None


def format_size(n):
    if n is None:
        return "?"
    for unit, div in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= div:
            return f"{n / div:.1f} {unit}"
    return f"{int(n)} B"


def format_eta(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec} sn"
    if sec < 3600:
        return f"{sec // 60} dk {sec % 60:02d} sn"
    return f"{sec // 3600} sa {(sec % 3600) // 60:02d} dk"


class DownloadMeter:
    """İndirme ilerlemesini izler; hız ve kalan süreyi hesaplar, ekranı yormamak için yenilemeyi seyreltir."""

    REFRESH = 0.15  # saniye

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self.reset()

    def reset(self):
        self.done = None
        self.total = None
        self.pct = None
        self.name = None
        self.speed = None
        self.active = False
        self._last_t = None
        self._last_done = None
        self._last_emit = 0.0
        self._milestone = -1

    def feed(self, prog, force=False):
        """Yeni ilerleme bilgisini işler. Ekran yenilenmeli ise (oran|None, metin) döner, yoksa None."""
        now = self._clock()
        # Yuvarlanmış boyut ("15.9 MB") ile tam bayt sayısı ayrı dosya sanılmasın diye %5 tolerans
        total_changed = bool(prog.get("total") and self.total
                             and abs(prog["total"] - self.total) > self.total * 0.05)
        new_file = prog.get("start") or total_changed or (
            prog.get("done") is not None and self.done is not None and prog["done"] < self.done)
        if new_file:
            name = prog.get("name") if (prog.get("start") or total_changed) else self.name
            self.reset()
            self.name = name
        if prog.get("name"):
            self.name = prog["name"]

        done, total = prog.get("done"), prog.get("total")
        if done is not None:
            if self._last_t is not None and self._last_done is not None and now > self._last_t:
                dt = now - self._last_t
                if dt >= 0.3:
                    inst = max(0, done - self._last_done) / dt
                    self.speed = inst if self.speed is None else self.speed * 0.6 + inst * 0.4
                    self._last_t, self._last_done = now, done
            else:
                self._last_t, self._last_done = now, done
            self.done = done
        if total:
            self.total = total
        if prog.get("pct") is not None:
            self.pct = max(0.0, min(100.0, prog["pct"]))
        elif self.done is not None and self.total:
            self.pct = min(100.0, self.done * 100.0 / self.total)
        self.active = True

        if not force and now - self._last_emit < self.REFRESH and (self.pct or 0) < 100:
            return None
        self._last_emit = now
        return self.fraction(), self.text()

    def fraction(self):
        return None if self.pct is None else self.pct / 100.0

    def milestone(self):
        """Konsola yazmak için %25'lik eşik geçildiyse eşiği döndürür."""
        if self.pct is None:
            return None
        step = int(self.pct // 25) * 25
        if step > self._milestone:
            self._milestone = step
            return step
        return None

    def text(self):
        parts = []
        name = self.name
        if name and len(name) > 34:
            name = name[:31] + "…"
        head = "⬇ " + (f"{name}  " if name else "İndiriliyor  ")
        if self.pct is not None:
            head += f"%{int(self.pct)}"
        parts.append(head.rstrip())
        if self.done is not None and self.total:
            parts.append(f"{format_size(self.done)} / {format_size(self.total)}")
        elif self.done is not None:
            parts.append(format_size(self.done))
        if self.speed:
            parts.append(f"{format_size(self.speed)}/s")
            if self.total and self.done is not None and self.speed > 0 and self.done < self.total:
                parts.append(f"~{format_eta((self.total - self.done) / self.speed)} kaldı")
        return "  ·  ".join(parts)

    def finish_text(self):
        size = self.total or self.done
        return "✔ İndirme bitti" + (f" ({format_size(size)})" if size else "") + " — kuruluyor..."


def _round_rect(cv, x1, y1, x2, y2, r, fill="", outline=None, width=1, tag="rr"):
    """Canvas üzerinde tam yuvarlak köşeli dikdörtgen çizer (4 daire + 2 dikdörtgen).

    Kenarlık için önce dış renkte, sonra `width` kadar içeride dolgu renginde ikinci bir katman çizilir.
    Tüm parçalar `tag` etiketini taşır, böylece tek seferde silinebilir.
    """
    def layer(a, b, c, d, rad, color, sub):
        rad = max(0, min(rad, (c - a) / 2, (d - b) / 2))
        tags = (tag, sub)
        if rad <= 0:
            cv.create_rectangle(a, b, c, d, fill=color, outline="", tags=tags)
            return
        k = 2 * rad
        for ox, oy in ((a, b), (c - k, b), (a, d - k), (c - k, d - k)):
            cv.create_oval(ox, oy, ox + k, oy + k, fill=color, outline="", tags=tags)
        cv.create_rectangle(a + rad, b, c - rad, d, fill=color, outline="", tags=tags)
        cv.create_rectangle(a, b + rad, c, d - rad, fill=color, outline="", tags=tags)

    if outline and outline != fill and width:
        layer(x1, y1, x2, y2, r, outline, tag + "_o")
        layer(x1 + width, y1 + width, x2 - width, y2 - width, r - width, fill, tag + "_i")
    else:
        layer(x1, y1, x2, y2, r, fill, tag + "_i")


class RoundedFrame(tk.Canvas):
    """Yuvarlak köşeli çerçeve. İçerik `.body` çerçevesine eklenir."""

    def __init__(self, parent, fill, outline=None, radius=14, pad=(16, 12), width=200):
        # Başlangıç yüksekliği iç dolgudan büyük olmalı, yoksa içerik görünür alan dışında kalır ve hiç çizilmez
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0,
                         width=width, height=2 * pad[1] + 20)
        self.radius = radius
        self._fill = fill
        self._outline = outline or fill
        self._pad = pad
        self._shape = None
        self.body = tk.Frame(self, bg=fill)
        self._win = self.create_window(pad[0], pad[1], window=self.body, anchor="nw")
        self.bind("<Configure>", self._on_resize)
        self.body.bind("<Configure>", self._on_body)
        self.after_idle(self._on_body)

    def _on_body(self, _e=None):
        if not self.winfo_exists():
            return
        want = self.body.winfo_reqheight() + 2 * self._pad[1]
        if int(float(self.cget("height"))) != want:
            self.configure(height=want)

    def _on_resize(self, e):
        self.itemconfigure(self._win, width=max(1, e.width - 2 * self._pad[0]))
        self._redraw(e.width, e.height)

    def _redraw(self, w, h):
        self.delete("rr")
        _round_rect(self, 0, 0, w - 1, h - 1, self.radius, fill=self._fill, outline=self._outline, width=1)
        self.tag_lower("rr")

    def set_colors(self, fill, outline=None):
        self._fill = fill
        self._outline = outline or fill
        self.body.configure(bg=fill)
        w, h = self.winfo_width(), self.winfo_height()
        if w > 2 and h > 2:
            self._redraw(w, h)


class RoundedButton(tk.Canvas):
    """Yuvarlak köşeli, tk.Button gibi davranan düğme (text, bg, fg, state, command)."""

    def __init__(self, parent, text, command=None, bg="#0071e3", fg="#ffffff",
                 font=("Segoe UI", 9), radius=10, padx=16, pady=7,
                 disabled_fg="#86868b", parent_bg=None):
        self._font = tkfont.Font(font=font)
        self._padx = padx
        self._text, self._command = text, command
        self._bg, self._fg, self._disabled_fg = bg, fg, disabled_fg
        self._state, self._radius = "normal", radius
        w = self._font.measure(text) + 2 * padx
        h = self._font.metrics("linespace") + 2 * pady
        super().__init__(parent, width=w, height=h, bg=parent_bg or parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._click)

    def _draw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return
        self.delete("all")
        fg = self._fg if self._state == "normal" else self._disabled_fg
        _round_rect(self, 0, 0, w - 1, h - 1, self._radius, fill=self._bg, outline=self._bg)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    def _click(self, _e):
        if self._state == "normal" and self._command:
            self._command()

    def cget(self, key):
        if key == "state":
            return self._state
        return super().cget(key)

    def configure(self, cnf=None, **kw):
        changed = False
        if "text" in kw:
            self._text = kw.pop("text")
            need = self._font.measure(self._text) + 2 * self._padx
            if need > int(float(super().cget("width"))):
                super().configure(width=need)
            changed = True
        if "bg" in kw:
            self._bg = kw.pop("bg")
            changed = True
        if "fg" in kw:
            self._fg = kw.pop("fg")
            changed = True
        if "command" in kw:
            self._command = kw.pop("command")
        if "state" in kw:
            self._state = kw.pop("state")
            super().configure(cursor="hand2" if self._state == "normal" else "arrow")
            changed = True
        if kw or cnf:
            super().configure(cnf, **kw)
        if changed:
            self._draw()

    config = configure


class RoundCheck(tk.Canvas):
    """Yuvarlak köşeli onay kutusu: seçilince mavi dolar ve beyaz tik çizer."""

    def __init__(self, parent, variable, bg, size=22, radius=7):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self._var = variable
        self._size = size
        self._radius = radius
        self.bind("<Button-1>", lambda _e: self._var.set(not self._var.get()))
        self.bind("<Enter>", lambda _e: self._draw(hover=True))
        self.bind("<Leave>", lambda _e: self._draw())
        self._var.trace_add("write", lambda *_a: self._draw())
        self._draw()

    def _draw(self, hover=False):
        if not self.winfo_exists():
            return
        self.delete("all")
        s = self._size
        if self._var.get():
            _round_rect(self, 1, 1, s - 1, s - 1, self._radius,
                        fill=THEME["accent_blue"], outline=THEME["accent_blue"])
            self.create_line(s * 0.28, s * 0.53, s * 0.44, s * 0.69, s * 0.75, s * 0.33,
                             fill="#ffffff", width=2.5, capstyle="round", joinstyle="round")
        else:
            outline = THEME["accent_blue"] if hover else "#b4b4bc"
            _round_rect(self, 1.5, 1.5, s - 1.5, s - 1.5, self._radius,
                        fill="#ffffff", outline=outline, width=1.5)

    def set_bg(self, bg):
        self.configure(bg=bg)


class InstallOverlay(tk.Frame):
    """Kurulum sırasında pencerenin üstünü kaplayan yükleme ekranı."""

    BAR_W = 480

    def __init__(self, parent, on_cancel):
        super().__init__(parent, bg=THEME["bg_main"])
        self._on_cancel = on_cancel
        self._target = 0.0
        self._shown = 0.0
        self._angle = 0
        self._running = False
        self._loop_id = None
        self._total = 0
        self._done = 0
        bg = THEME["bg_card"]

        self.card = RoundedFrame(self, fill=bg, outline=THEME["border"], radius=26, pad=(44, 36), width=620)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        body = self.card.body

        self.icon = tk.Canvas(body, width=72, height=72, bg=bg, highlightthickness=0)
        self.icon.pack(pady=(0, 14))

        self.title = tk.Label(body, text="Kurulum sürüyor", font=("Segoe UI Semibold", 20),
                              fg=THEME["text_primary"], bg=bg)
        self.title.pack()
        self.subtitle = tk.Label(body, text="Hazırlanıyor...", font=("Segoe UI", 11),
                                 fg=THEME["text_secondary"], bg=bg)
        self.subtitle.pack(pady=(4, 18))

        self.bar = tk.Canvas(body, width=self.BAR_W, height=12, bg=bg, highlightthickness=0)
        self.bar.pack()
        self.percent = tk.Label(body, text="%0", font=("Segoe UI", 10, "bold"),
                                fg=THEME["accent_blue"], bg=bg)
        self.percent.pack(pady=(8, 2))
        self.dl_lbl = tk.Label(body, text="", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=bg)
        self.dl_lbl.pack(pady=(0, 12))

        stats = tk.Frame(body, bg=bg)
        stats.pack(fill="x")
        self._count_labels = {}
        for col, (key, label, color) in enumerate((
                ("ok", "Kuruldu", THEME["accent_green"]),
                ("skip", "Zaten kurulu", THEME["accent_yellow"]),
                ("fail", "Hata", THEME["accent_red"]))):
            stats.columnconfigure(col, weight=1, uniform="stat")
            box = RoundedFrame(stats, fill=THEME["bg_main"], radius=14, pad=(12, 10), width=150)
            box.grid(row=0, column=col, padx=5, sticky="ew")
            num = tk.Label(box.body, text="0", font=("Segoe UI Semibold", 20), fg=color, bg=THEME["bg_main"])
            num.pack()
            tk.Label(box.body, text=label, font=("Segoe UI", 9), fg=THEME["text_secondary"],
                     bg=THEME["bg_main"]).pack()
            self._count_labels[key] = num

        self.log_lbl = tk.Label(body, text="", font=("Consolas", 8), fg=THEME["text_muted"], bg=bg, anchor="w")
        self.log_lbl.pack(fill="x", pady=(16, 0))

        self.btn = RoundedButton(body, text="İptal Et", command=self._cancel_clicked,
                                 bg=THEME["bg_main"], fg=THEME["accent_red"],
                                 font=("Segoe UI", 10, "bold"), radius=18, padx=34, pady=9, parent_bg=bg)
        self.btn.pack(pady=(18, 0))
        self._draw_bar()
        self._draw_spinner()

    # --- dış arayüz ---------------------------------------------------
    def begin(self, total):
        self._target = self._shown = 0.0
        self._total = total
        self._done = 0
        self._running = True
        self.dl_lbl.configure(text="")
        self.title.configure(text="Kurulum sürüyor")
        self.subtitle.configure(text=f"{total} öğe sırayla kuruluyor...")
        for lbl in self._count_labels.values():
            lbl.configure(text="0")
        self.log_lbl.configure(text="")
        self.btn.configure(text="İptal Et", bg=THEME["bg_main"], fg=THEME["accent_red"],
                           command=self._cancel_clicked, state="normal")
        self._loop()

    def set_current(self, idx, total, name):
        self.subtitle.configure(text=f"{name}  ·  {idx} / {total}")
        self.dl_lbl.configure(text="")

    def set_download(self, frac, text):
        """Mevcut öğenin indirme durumunu gösterir; ana çubuk da indirmeyle birlikte ilerler."""
        self.dl_lbl.configure(text=text)
        if frac is not None and self._total:
            self._target = max(self._target, (self._done + min(frac, 1.0)) / self._total)

    def update_progress(self, done, total, ok, skip, fail):
        self._done = done
        self._target = done / total if total else 0.0
        self.dl_lbl.configure(text="")
        self._count_labels["ok"].configure(text=str(ok))
        self._count_labels["skip"].configure(text=str(skip))
        self._count_labels["fail"].configure(text=str(fail))

    def set_log(self, text):
        text = text.strip().splitlines()[-1] if text.strip() else ""
        self.log_lbl.configure(text=text[:80] + ("…" if len(text) > 80 else ""))

    def set_cancelling(self):
        self.subtitle.configure(text="İptal ediliyor... Lütfen bekleyin.")
        self.btn.configure(state="disabled")

    def finish(self, ok, skip, fail, total, cancelled):
        self._running = False
        if self._loop_id:
            self.after_cancel(self._loop_id)
            self._loop_id = None
        if not cancelled:
            self._target = self._shown = 1.0
        self._draw_bar()
        self.percent.configure(text=f"%{int(self._shown * 100)}")
        self._draw_done(cancelled, fail)
        self.dl_lbl.configure(text="")
        if cancelled:
            self.title.configure(text="Kurulum durduruldu")
        elif fail:
            self.title.configure(text="Kurulum tamamlandı")
        else:
            self.title.configure(text="Hepsi hazır")
        self.subtitle.configure(text=f"{ok} kuruldu  ·  {skip} zaten kuruluydu  ·  {fail} hata")
        self.log_lbl.configure(text="Ayrıntılar alttaki konsolda.")
        self.btn.configure(text="Kapat", bg=THEME["accent_blue"], fg="#ffffff",
                           command=self.hide, state="normal")

    def hide(self):
        self.place_forget()

    # --- iç işler -----------------------------------------------------
    def _cancel_clicked(self):
        self._on_cancel()

    def _loop(self):
        if not self._running:
            return
        self._angle = (self._angle - 14) % 360
        self._draw_spinner()
        diff = self._target - self._shown
        if abs(diff) > 0.001:
            self._shown += diff * 0.18
            self._draw_bar()
        self.percent.configure(text=f"%{int(self._shown * 100)}")
        self._loop_id = self.after(33, self._loop)

    def _draw_spinner(self):
        c = self.icon
        c.delete("all")
        c.create_oval(8, 8, 64, 64, outline=THEME["bg_panel"], width=6)
        c.create_arc(8, 8, 64, 64, start=self._angle, extent=100, style="arc",
                     outline=THEME["accent_blue"], width=6)

    def _draw_done(self, cancelled, fail):
        c = self.icon
        c.delete("all")
        color = THEME["accent_yellow"] if (cancelled or fail) else THEME["accent_green"]
        c.create_oval(4, 4, 68, 68, fill=color, outline=color)
        if cancelled:
            c.create_line(28, 24, 28, 48, fill="#ffffff", width=5, capstyle="round")
            c.create_line(44, 24, 44, 48, fill="#ffffff", width=5, capstyle="round")
        else:
            c.create_line(22, 37, 32, 47, 50, 26, fill="#ffffff", width=5, capstyle="round", joinstyle="round")

    def _draw_bar(self):
        c = self.bar
        c.delete("all")
        _round_rect(c, 0, 0, self.BAR_W, 12, 6, fill=THEME["bg_panel"], outline=THEME["bg_panel"])
        if self._shown > 0.001:
            w = max(12, self.BAR_W * min(self._shown, 1.0))
            _round_rect(c, 0, 0, w, 12, 6, fill=THEME["accent_blue"], outline=THEME["accent_blue"])


class ProgramCard(tk.Canvas):
    """Tek Canvas üzerine çizilen hızlı program kartı: onay kutusu, ad, tür rozeti, açıklama, durum."""

    HEIGHT = 78
    _fonts = {}
    _BADGES = {
        "pip": ("PIP PAKETİ", "accent_purple"),
        "git_repo": ("GITHUB REPO", "accent_yellow"),
        "direct_zip": ("PORTATİF ZIP", None),
        "direct_exe": ("DOĞRUDAN İNDİR", "accent_green"),
        "winget": ("WINGET SİSTEM", "accent_blue"),
        "web": ("RESMÎ SİTE", "accent_indigo"),
    }

    def __init__(self, parent, program, variable, status):
        super().__init__(parent, height=self.HEIGHT, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        if not ProgramCard._fonts:
            ProgramCard._fonts = {
                "name": tkfont.Font(font=("Segoe UI", 10, "bold")),
                "badge": tkfont.Font(font=("Segoe UI", 7, "bold")),
                "desc": tkfont.Font(font=("Segoe UI", 8)),
                "status": tkfont.Font(font=("Segoe UI", 9, "bold")),
            }
        self.program = program
        self.var = variable
        self._is_web = program.get("type") == "web"
        if self._is_web:
            # Ticari yazılım: kurulum yok, karta tıklayınca resmî sayfa açılır
            status = ("Resmî sayfa ↗", THEME["accent_indigo"])
        self.status_text, self.status_color = status
        self._hover = False
        self._last_w = 0
        self.bind("<Configure>", self._on_configure)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.var.trace_add("write", lambda *_a: self._draw())

    def _on_click(self, _e):
        if self._is_web:
            webbrowser.open(self.program["package_id"])
        else:
            self.var.set(not self.var.get())

    def set_status(self, text, color):
        if self._is_web:
            return
        self.status_text, self.status_color = text, color
        self._draw()

    def _set_hover(self, value):
        if self._hover != value:
            self._hover = value
            self._draw()

    def _on_configure(self, e):
        if e.width != self._last_w:
            self._last_w = e.width
            self._draw()

    @staticmethod
    def _fit(text, font, avail):
        if font.measure(text) <= avail:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= avail:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"

    def _draw(self):
        if not self.winfo_exists():
            return
        w, h = self.winfo_width(), self.HEIGHT
        if w < 60:
            return
        f = self._fonts
        p = self.program
        selected = self.var.get()
        self.delete("all")

        fill = THEME["bg_card_selected"] if selected else THEME["bg_card"]
        outline = THEME["border_selected"] if selected else (
            THEME["border_light"] if self._hover else THEME["border"])
        _round_rect(self, 0, 0, w - 1, h - 1, 16, fill=fill, outline=outline, width=1)

        # Onay kutusu (web türünde bunun yerine bağlantı simgesi)
        cx, cy, s = 18, (h - 22) // 2, 22
        if self._is_web:
            link_color = THEME["accent_indigo"]
            _round_rect(self, cx, cy, cx + s, cy + s, 7, fill="#ffffff", outline=link_color, width=1, tag="cb")
            self.create_text(cx + s / 2, cy + s / 2 - 1, text="↗", font=f["status"], fill=link_color)
        elif selected:
            _round_rect(self, cx, cy, cx + s, cy + s, 7, fill=THEME["accent_blue"], outline=THEME["accent_blue"], tag="cb")
            self.create_line(cx + s * 0.28, cy + s * 0.53, cx + s * 0.44, cy + s * 0.69, cx + s * 0.75, cy + s * 0.33,
                             fill="#ffffff", width=2.5, capstyle="round", joinstyle="round")
        else:
            box_outline = THEME["accent_blue"] if self._hover else "#b4b4bc"
            _round_rect(self, cx, cy, cx + s, cy + s, 7, fill="#ffffff", outline=box_outline, width=1, tag="cb")

        # Ad ve tür rozeti
        tx = 54
        self.create_text(tx, 28, text=p["name"], anchor="w", font=f["name"], fill=THEME["text_primary"])
        name_w = f["name"].measure(p["name"])
        label, color_key = self._BADGES.get(p.get("type", "winget"), self._BADGES["winget"])
        badge_color = THEME[color_key] if color_key else "#007aa3"
        bw = f["badge"].measure(label) + 14
        bx = tx + name_w + 12
        if bx + bw < w - 120:
            _round_rect(self, bx, 19, bx + bw, 37, 9, fill=THEME["bg_panel"], outline=THEME["bg_panel"], tag="bd")
            self.create_text(bx + bw / 2, 28, text=label, font=f["badge"], fill=badge_color)

        # Durum (sağda)
        status_w = f["status"].measure(self.status_text)
        self.create_text(w - 20, h / 2, text=self.status_text, anchor="e", font=f["status"], fill=self.status_color)

        # Açıklama (sığmazsa "…" ile kısalt)
        avail = w - tx - status_w - 44
        desc = f"{p['desc']}  •  [ {p['package_id']} ]"
        self.create_text(tx, 54, text=self._fit(desc, f["desc"], avail), anchor="w",
                         font=f["desc"], fill=THEME["text_secondary"])


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
        self.card_frames = {}    # prog_id -> ProgramCard
        self._packed_ids = []    # ekranda şu an gösterilen kartların sırası
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
        # Exe içinde sys.executable Atolye.exe'dir: pip için sistemdeki Python aranır
        if not IS_FROZEN and sys.executable and os.path.exists(sys.executable):
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
        if getattr(self, "_bulk", False):
            return
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
                        thickness=8)
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
            text=(f"Mühendis Kurulum Merkezi  ·  {sum(1 for p in PROGRAMS if p['type'] != 'web')} araç, tek tıkla kurulum"
                  f"  ·  {sum(1 for p in PROGRAMS if p['type'] == 'web')} ticari yazılım için resmî sayfa"),
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
        search_pill = RoundedFrame(top_right, fill=search_bg, radius=16, pad=(14, 7), width=340)
        search_pill.pack(side="right", padx=(15, 0), pady=4)
        search_frame = search_pill.body

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
            width=30
        )
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.pack(side="left", padx=6, fill="x", expand=True)

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
        # Dış çerçeve sabit genişlikte; içerik kaydırılabilir, istatistik kutusu altta sabit kalır
        self.sidebar_outer = tk.Frame(main_body, bg=THEME["bg_panel"], width=300)
        self.sidebar_outer.pack(side="left", fill="y")
        self.sidebar_outer.pack_propagate(False)

        self.sidebar_canvas = tk.Canvas(self.sidebar_outer, bg=THEME["bg_panel"], highlightthickness=0, width=300)
        sidebar = tk.Frame(self.sidebar_canvas, bg=THEME["bg_panel"], padx=14, pady=14)
        sidebar_win = self.sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")
        sidebar.bind("<Configure>", lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.bind("<Configure>", lambda e: self.sidebar_canvas.itemconfigure(sidebar_win, width=e.width))
        sidebar_scroll = ttk.Scrollbar(self.sidebar_outer, orient="vertical", command=self.sidebar_canvas.yview,
                                       style="Dark.Vertical.TScrollbar")
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar_scroll.pack(side="right", fill="y")
        self.sidebar_canvas.pack(side="left", fill="both", expand=True)

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
            ("workplace", "🏢 İş Yeri"),
            ("ai_engineer", "🤖 Yapay Zeka"),
            ("cyber_security", "🛡️ Siber Güvenlik"),
            ("design_media", "🎨 Tasarım & 3D"),
            ("hardware_embedded", "⚡ Donanım"),
            ("software_fullstack", "💻 Yazılım"),
            ("devops_cloud", "☁️ DevOps"),
            ("mech_eng", "🔧 Makine"),
            ("elec_eng", "🔌 Elektrik-Elektronik"),
            ("civil_eng", "🏗️ İnşaat & Harita"),
            ("chem_bio", "🧪 Kimya & Biyo"),
            ("aero_ind", "🛰️ Uzay & Endüstri"),
            ("science_math", "📐 Matematik & Bilim"),
        ]

        # Profiller 2 sütunlu ızgarada: sol panele sığar
        preset_grid = tk.Frame(sidebar, bg=THEME["bg_panel"])
        preset_grid.pack(fill="x")
        preset_grid.columnconfigure(0, weight=1, uniform="preset")
        preset_grid.columnconfigure(1, weight=1, uniform="preset")

        for i, (p_key, p_title) in enumerate(presets_list):
            p_btn = RoundedButton(
                preset_grid,
                text=p_title,
                command=lambda k=p_key: self.apply_preset(k),
                bg=THEME["bg_card"],
                fg=THEME["text_primary"],
                font=("Segoe UI", 9),
                radius=12,
                padx=8,
                pady=7,
                parent_bg=THEME["bg_panel"]
            )
            p_btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
            self.add_hover(p_btn, THEME["bg_card"], THEME["bg_card_hover"])

        # Sol Panel Alt İstatistik Kutusu
        stat_card = RoundedFrame(self.sidebar_outer, fill=THEME["bg_card"], radius=14, pad=(14, 10), width=240)
        # before=: alt kutu önce yer ayırır, küçük pencerede kesilmez
        stat_card.pack(side="bottom", fill="x", padx=14, pady=(6, 14), before=sidebar_scroll)
        stat_box = stat_card.body

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

        select_all_btn = RoundedButton(
            quick_select_box,
            text="✓ Bu Bölümü Seç",
            command=self.select_current_category,
            bg=THEME["bg_card"],
            fg=THEME["accent_blue"],
            font=("Segoe UI", 9, "bold"),
            radius=14,
            padx=14,
            pady=6,
            parent_bg=THEME["bg_main"]
        )
        select_all_btn.pack(side="left", padx=4)
        self.add_hover(select_all_btn, THEME["bg_card"], THEME["bg_card_hover"])

        deselect_all_btn = RoundedButton(
            quick_select_box,
            text="✕ Bu Bölümü Kaldır",
            command=self.deselect_current_category,
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=("Segoe UI", 9),
            radius=14,
            padx=14,
            pady=6,
            parent_bg=THEME["bg_main"]
        )
        deselect_all_btn.pack(side="left", padx=4)
        self.add_hover(deselect_all_btn, THEME["bg_card"], THEME["bg_card_hover"])

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
        footer_frame = tk.Frame(self.root, bg=THEME["bg_panel"], padx=22, pady=12)
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

        self.terminal_toggle_btn = RoundedButton(
            btn_action_box,
            text="📋 Konsolu Gizle",
            command=self.toggle_terminal,
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=("Segoe UI", 9),
            radius=16,
            padx=16,
            pady=8,
            parent_bg=THEME["bg_panel"]
        )
        self.terminal_toggle_btn.pack(side="left", padx=6)
        self.add_hover(self.terminal_toggle_btn, THEME["bg_card"], THEME["bg_card_hover"])

        self.cancel_btn = RoundedButton(
            btn_action_box,
            text="İptal Et",
            command=self.cancel_installation,
            bg=THEME["bg_card"],
            fg=THEME["accent_red"],
            font=("Segoe UI", 9, "bold"),
            radius=16,
            padx=16,
            pady=8,
            parent_bg=THEME["bg_panel"]
        )
        self.cancel_btn.configure(state="disabled")
        self.cancel_btn.pack(side="left", padx=6)

        self.install_btn = RoundedButton(
            btn_action_box,
            text="SEÇİLENLERİ KUR (222)",
            command=self.start_installation,
            bg=THEME["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            radius=18,
            padx=24,
            pady=9,
            parent_bg=THEME["bg_panel"]
        )
        self.install_btn.configure(text="SEÇİLENLERİ KUR (0)")
        self.install_btn.pack(side="left", padx=6)
        self.add_hover(self.install_btn, THEME["accent_blue"], THEME["accent_blue_dark"])

        # 4. CANLI TERMİNAL ÇIKTI KUTUSU (DRAWER)
        self.terminal_frame = tk.Frame(footer_frame, bg=THEME["terminal_bg"])
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
        # İşaretçi sol paneldeyse onu, değilse program listesini kaydır
        outer = str(self.sidebar_outer)
        path = str(event.widget)
        in_sidebar = path == outer or path.startswith(outer + ".")
        target = self.sidebar_canvas if in_sidebar else self.canvas
        if target.yview() == (0.0, 1.0):
            return
        target.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
            if getattr(self, "overlay", None) is not None and self.is_installing:
                self.overlay.set_log(message)
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

        self._bulk = True
        try:
            for pid, var in self.selected_vars.items():
                var.set(pid in target_ids)
        finally:
            self._bulk = False
        self.save_selections()
        self.update_stats()
        self.update_category_badges()
        self.log_to_terminal(f"[ŞABLON SEÇİLDİ] {preset['name']} uygulandı ({len(target_ids)} program).")

    def select_current_category(self):
        items = [p for p in self.get_visible_programs() if p.get("type") != "web"]
        self._bulk = True
        try:
            for p in items:
                self.selected_vars[p["id"]].set(True)
        finally:
            self._bulk = False
        self.save_selections()
        self.update_stats()
        self.update_category_badges()

    def deselect_current_category(self):
        items = self.get_visible_programs()
        self._bulk = True
        try:
            for p in items:
                self.selected_vars[p["id"]].set(False)
        finally:
            self._bulk = False
        self.save_selections()
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
        visible_ids = [p["id"] for p in visible_programs]

        if visible_ids != self._packed_ids:
            for pid in self._packed_ids:
                self.card_frames[pid].pack_forget()
            if self.empty_lbl:
                self.empty_lbl.pack_forget()
            if not visible_ids:
                if self.empty_lbl:
                    self.empty_lbl.pack(fill="x")
            else:
                for pid in visible_ids:
                    self.card_frames[pid].pack(fill="x", pady=4, padx=2)
            self._packed_ids = visible_ids
            self.canvas.yview_moveto(0)

        self.update_category_badges()

    def create_program_card(self, p):
        pid = p["id"]
        status = self.program_statuses.get(pid, ("⚪ Bekliyor", THEME["text_muted"]))
        self.card_frames[pid] = ProgramCard(self.scrollable_frame, p, self.selected_vars[pid], status)

    def update_stats(self):
        selected_count = sum(1 for v in self.selected_vars.values() if v.get())
        total_count = sum(1 for p in PROGRAMS if p.get("type") != "web")

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
                tot = sum(1 for p in PROGRAMS if p.get("type") != "web")
            else:
                cat_progs = [p for p in PROGRAMS if p["category"] == cid and p.get("type") != "web"]
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

        # Yükleme ekranını göster
        if getattr(self, "overlay", None) is None:
            self.overlay = InstallOverlay(self.root, self.cancel_installation)
        self.overlay.begin(len(selected_programs))
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.overlay.lift()

        # Kurulum İş Parçacığını Başlat
        thread = threading.Thread(target=self._run_install_thread, args=(selected_programs,), daemon=True)
        thread.start()

    def cancel_installation(self):
        if self.is_installing:
            self.cancel_requested = True
            self.log_to_terminal("\n[DURDURMA TALEBİ] Kullanıcı iptal butonuna bastı. İşlem durduruluyor...")
            self.status_text_lbl.configure(text="İptal ediliyor... Lütfen bekleyin.")
            if getattr(self, "overlay", None) is not None:
                self.overlay.set_cancelling()
            if self.current_process and self.current_process.poll() is None:
                try:
                    self.current_process.terminate()
                except Exception:
                    pass

    def set_program_status(self, pid, text, color):
        self.program_statuses[pid] = (text, color)
        def _update():
            card = self.card_frames.get(pid)
            if card is not None and card.winfo_exists():
                card.set_status(text, color)
        self.root.after(0, _update)

    def _pip_progress_args(self):
        """pip 24.1+ ise, ilerlemeyi okunabilir satırlar halinde yazdıran '--progress-bar raw' ekler."""
        if getattr(self, "_pip_raw_ok", None) is None:
            self._pip_raw_ok = False
            try:
                out = subprocess.run(
                    [self.python_cmd, "-m", "pip", "--version"], capture_output=True, text=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).stdout
                m = re.search(r"pip (\d+)\.(\d+)", out or "")
                if m and (int(m.group(1)), int(m.group(2))) >= (24, 1):
                    self._pip_raw_ok = True
            except Exception:
                pass
        return ["--progress-bar", "raw"] if self._pip_raw_ok else []

    def _show_download(self, frac, text, idx, total, pname):
        """İndirme durumunu yükleme ekranına ve alt çubuğa yansıtır (arka plan iş parçacığından çağrılabilir)."""
        def _apply():
            if getattr(self, "overlay", None) is not None:
                self.overlay.set_download(frac, text)
            self.status_text_lbl.configure(text=f"Kuruluyor ({idx}/{total}): {pname}  —  {text}")
            if frac is not None:
                self.progress_bar.configure(value=(idx - 1) + min(frac, 1.0))
        self.root.after(0, _apply)

    def _feed_meter(self, meter, prog, idx, total, pname):
        upd = meter.feed(prog)
        if upd is not None:
            self._show_download(upd[0], upd[1], idx, total, pname)
        step = meter.milestone()
        if step is not None:
            self.log_to_terminal(f"   {meter.text()}")

    def _run_streamed(self, cmd, idx, total, pname):
        """Komutu çalıştırır, çıktısını konsola akıtır; ilerleme satırlarını ayrıştırıp ekranda gösterir."""
        meter = DownloadMeter()
        # text=True evrensel satır sonu kullanır: winget/git'in \r ile güncellediği çubuklar da ayrı satır gelir
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
            if not clean_line:
                continue
            prog = parse_download_progress(clean_line)
            if prog is not None:
                if prog.get("start"):
                    self.log_to_terminal(f"   {clean_line}")
                self._feed_meter(meter, prog, idx, total, pname)
                continue
            if meter.active:
                # İlerleme bitti, kurulum/kurulum sonrası çıktılar başladı
                self._show_download(None, meter.finish_text(), idx, total, pname)
                meter.reset()
            self.log_to_terminal(f"   {clean_line}")
        self.current_process.stdout.close()
        return_code = self.current_process.wait()
        self.current_process = None
        return return_code

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
            self.root.after(0, lambda i=idx, n=pname: self.overlay.set_current(i, total, n))
            self.set_program_status(pid, "🔄 Kuruluyor...", THEME["accent_blue"])
            self.log_to_terminal(f"\n▶ [{idx}/{total}] {pname} ({ptype.upper()}: {pkg_id}) kuruluyor...")

            start_t = time.time()

            try:
                tools_dir = os.path.join(os.path.expanduser("~"), "Engineering_Tools")
                os.makedirs(tools_dir, exist_ok=True)

                if ptype == "pip":
                    cmd = [self.python_cmd, "-m", "pip", "install", "--upgrade", "--no-warn-script-location"] \
                        + self._pip_progress_args() + pkg_id.split()
                    return_code = self._run_streamed(cmd, idx, total, pname)

                elif ptype == "git_repo":
                    target_dir = os.path.join(tools_dir, pid)
                    if os.path.exists(target_dir) and os.path.isdir(os.path.join(target_dir, ".git")):
                        self.log_to_terminal(f"   [GÜNCELLEME] Mevcut repo güncelleniyor: {target_dir}")
                        cmd = ["git", "-c", "core.longpaths=true", "-C", target_dir, "pull", "--progress"]
                    else:
                        self.log_to_terminal(f"   [GİT KLONLA] {pkg_id} indiriliyor -> {target_dir}")
                        # core.longpaths: Windows'ta 260 karakter yol sınırı hatasını önler
                        cmd = ["git", "-c", "core.longpaths=true", "clone", "--progress", "--depth", "1", pkg_id, target_dir]

                    return_code = self._run_streamed(cmd, idx, total, pname)

                    # Eğer requirements.txt varsa bağımlılıkları yükle
                    req_file = os.path.join(target_dir, "requirements.txt")
                    if return_code == 0 and os.path.exists(req_file) and not self.cancel_requested:
                        self.log_to_terminal("   [PIP BAĞIMLILIKLARI] requirements.txt kuruluyor...")
                        pip_cmd = [self.python_cmd, "-m", "pip", "install", "-r", req_file,
                                   "--no-warn-script-location"] + self._pip_progress_args()
                        self._run_streamed(pip_cmd, idx, total, pname)

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
                        meter = DownloadMeter()
                        while True:
                            if self.cancel_requested:
                                break
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            out_f.write(chunk)
                            dl_bytes += len(chunk)
                            self._feed_meter(meter, {"done": dl_bytes, "total": total_bytes or None,
                                                     "pct": None, "name": None, "start": False},
                                             idx, total, pname)
                        if meter.active and not self.cancel_requested:
                            self._show_download(None, meter.finish_text(), idx, total, pname)

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
                    return_code = self._run_streamed(cmd, idx, total, pname)

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
            self.root.after(0, lambda v=idx, s=success_count, k=skipped_count, f=failed_count: (
                self.progress_bar.configure(value=v),
                self.overlay.update_progress(v, total, s, k, f)))

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
                self.overlay.finish(success_count, skipped_count, failed_count, total, cancelled=True)
            else:
                self.status_text_lbl.configure(text=f"Kurulum bitti! Başarılı: {success_count} | Zaten Kurulu: {skipped_count} | Hatalı: {failed_count}")
                self.log_to_terminal("\n" + "=" * 60)
                self.log_to_terminal("🎉 KURULUM İŞLEMİ TAMAMLANDI!")
                self.log_to_terminal(f"Toplam: {total} | Başarılı: {success_count} | Atlanan/Kurulu: {skipped_count} | Hata: {failed_count}")
                self.log_to_terminal("=" * 60)

                self.overlay.finish(success_count, skipped_count, failed_count, total, cancelled=False)

        self.root.after(0, _finish)


def main():
    root = tk.Tk()
    app = SuperInstallerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
