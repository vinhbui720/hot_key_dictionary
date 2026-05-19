#!/usr/bin/env python3
"""
Generate the app icon in all required sizes and install it
into ~/.local/share/icons/hicolor for Ubuntu app launcher.
"""
import sys, os
from pathlib import Path

os.environ.setdefault("DISPLAY", ":0")
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QImage, QLinearGradient, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QRectF

app = QApplication.instance() or QApplication(sys.argv)

def draw_icon(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    m = max(2, size // 16)   # margin scales with size
    w, h = size - 2*m, size - 2*m

    # ── Book cover (gradient blue) ──
    grad = QLinearGradient(m, m, m, m + h)
    grad.setColorAt(0.0, QColor("#7aa2f7"))
    grad.setColorAt(1.0, QColor("#4a72c7"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    radius = max(4, size // 10)
    p.drawRoundedRect(m, m, w, h, radius, radius)

    # ── Spine (darker left strip) ──
    spine_w = max(3, size // 8)
    p.setBrush(QColor("#3a62b7"))
    p.drawRoundedRect(m, m, spine_w, h, radius, radius)
    # Cover spine right edge flush
    p.drawRect(m + spine_w - radius, m, radius, h)

    # ── Page lines (white) ──
    if size >= 24:
        pen = QPen(QColor(255, 255, 255, 200))
        pen.setWidth(max(1, size // 24))
        p.setPen(pen)
        line_x1 = m + spine_w + max(2, size // 12)
        line_x2 = m + w - max(2, size // 12)
        n_lines = 3 if size >= 32 else 2
        for i in range(n_lines):
            y = m + h * (i + 1) // (n_lines + 1)
            p.drawLine(line_x1, y, line_x2, y)

    # ── "D" letter ──
    p.setPen(QColor(255, 255, 255, 240))
    font_size = max(8, int(size * 0.35))
    font = QFont("DejaVu Sans", font_size, QFont.Bold)
    p.setFont(font)
    # Center in the right 3/4 of the cover (excluding spine)
    text_rect = QRect(m + spine_w, m, w - spine_w, h)
    p.drawText(text_rect, Qt.AlignCenter, "D")

    p.end()
    return img

SIZES = [16, 32, 48, 64, 128, 256]
icon_dir = Path.home() / ".local/share/icons/hicolor"
asset_dir = Path(__file__).parent / "assets"
asset_dir.mkdir(exist_ok=True)

for sz in SIZES:
    img = draw_icon(sz)
    dest = icon_dir / f"{sz}x{sz}" / "apps" / "vinh-dictionary.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest))
    print(f"  Saved {sz}x{sz}: {dest}")

# Also save 256px version as main asset
main_icon = asset_dir / "icon.png"
draw_icon(256).save(str(main_icon))
print(f"  Main icon: {main_icon}")

# Update icon cache
os.system("gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true")
print("Done ✓")
