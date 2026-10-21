"""OCR 后端。

通过 ``create_backend(backend, lang)`` 按名称获取具体实现：

- ``windows`` : WinRT 系统 OCR，无需第三方模型，依赖系统语言包
- ``paddle``  : PaddleOCR，精度高但首次加载慢（需 ``pip install paddleocr``）

``OcrReader`` 为对外门面，封装后端选择与语言映射。
"""
import logging
import os

from .base import OcrBackend, TextBox

__all__ = [
    "OcrBackend",
    "TextBox",
    "create_backend",
    "AVAILABLE_BACKENDS",
    "OcrReader",
]

# 供 GUI 下拉框使用：内部值 -> 显示名
AVAILABLE_BACKENDS = {
    "windows": "Windows OCR (系统自带)",
    "paddle": "PaddleOCR (需安装)",
}
if os.name != "nt":
    AVAILABLE_BACKENDS = {
        "macos": "macOS Vision OCR (系统自带)",
        "paddle": "PaddleOCR (需安装)",
    }


def create_backend(backend: str = "windows", lang: str = "zh-cn") -> OcrBackend:
    """根据后端名创建 OCR 后端，按当前平台选择系统 OCR 兜底。

    PaddleOCR 的语言码与系统 OCR 不同（中文用 ``ch``、其余用 ``en``），在此统一映射。
    """
    name = (backend or "windows").strip().lower()

    if os.name != "nt" and name == "windows":
        logging.warning("macOS 不支持 Windows OCR，自动切换为 Vision OCR")
        name = "macos"

    if name == "paddle":
        from .paddle import PaddleOcrBackend
        paddle_lang = "ch" if lang.startswith("zh") else "en"
        return PaddleOcrBackend(lang=paddle_lang)

    if name == "macos":
        from .macos import MacOSVisionOcrBackend
        return MacOSVisionOcrBackend(lang=lang)

    if name != "windows":
        fallback = "macos" if os.name != "nt" else "windows"
        logging.warning(f"未知 OCR 后端 '{backend}'，回退到 {fallback}")
        name = fallback

    if name == "macos":
        from .macos import MacOSVisionOcrBackend
        return MacOSVisionOcrBackend(lang=lang)

    from .windows import WindowsOcrBackend
    return WindowsOcrBackend(lang=lang)


# 末尾导入避免与 create_backend 形成循环导入
from .reader import OcrReader  # noqa: E402
