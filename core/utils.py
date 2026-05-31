import os
import pygame
from settings import TEXT


# 專案根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 源流明體路徑
FONT_PATH = os.path.join(
    PROJECT_ROOT,
    "font",
    "otf",
    "TW",
    "GenRyuMin2TW-L.otf"
)


def get_font(size):
    """
    優先使用專案內的源流明體。
    若找不到字型檔，則退回系統預設字型，避免遊戲直接報錯。
    """
    if os.path.exists(FONT_PATH):
        return pygame.font.Font(FONT_PATH, size)

    print(f"[警告] 找不到字型檔：{FONT_PATH}")
    return pygame.font.SysFont("Microsoft JhengHei", size)


def draw_text(
    surface,
    text,
    x,
    y,
    font,
    color=TEXT,
    max_width=None,
    line_gap=6
):
    """
    支援中文自動換行的文字繪製。
    """
    if max_width is None:
        img = font.render(text, True, color)
        surface.blit(img, (x, y))
        return y + img.get_height()

    lines = []
    current = ""

    for ch in text:
        test = current + ch

        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch

    if current:
        lines.append(current)

    cy = y

    for line in lines:
        img = font.render(line, True, color)
        surface.blit(img, (x, cy))
        cy += img.get_height() + line_gap

    return cy