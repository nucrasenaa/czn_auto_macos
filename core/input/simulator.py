import logging
import random
from typing import List, Tuple

from .base import InputMethod
from . import create_backend


class InputSimulator:
    """输入模拟门面（facade）。

    自身不实现输入算法，按 ``backend`` 选择 ``core/input`` 下的后端：
    前台型（SendInput）直接注入系统输入，窗口型（SendMessage/PostMessage）
    需绑定目标窗口句柄。对外 API 保持与历史 ``controller.InputSimulator`` 一致，
    向后兼容所有调用方。
    """

    def __init__(self, backend: str = "postmessage", target_hwnd: int = 0):
        self.method = InputMethod.normalize(backend)
        self.backend = create_backend(self.method)
        self._keep_mouse = False
        self._click_jitter_radius = 0

        hwnd = target_hwnd
        if self.backend.needs_window and not hwnd:
            hwnd = self._find_window()
        if hwnd:
            self.backend.set_window(hwnd)

        # 设备型后端（ADB）：从全局选中设备解析 serial 并绑定
        if hasattr(self.backend, "set_device"):
            from core.window import get_selected_device

            serial = get_selected_device()
            if serial:
                self.set_device(serial)
            else:
                logging.warning(f"未选择 ADB 设备，{self.method} 后端将无法点击")

        logging.info(f"输入模拟方式: {self.method} (后端: {self.backend.name})")

    @property
    def keep_mouse(self) -> bool:
        return self._keep_mouse

    @keep_mouse.setter
    def keep_mouse(self, value: bool):
        self._keep_mouse = bool(value)
        self.backend.keep_mouse = bool(value)

    def set_window(self, hwnd: int):
        self.backend.set_window(hwnd)

    def set_device(self, serial: str):
        """绑定 ADB 设备 serial（仅设备型后端支持，其它后端忽略）。"""
        setter = getattr(self.backend, "set_device", None)
        if callable(setter):
            setter(serial)

    def set_click_jitter(self, radius: int = 0, enabled: bool = True):
        """设置点击随机范围。

        ``radius`` 是以点击中心为基准的半边长；例如 ``8`` 表示在
        ``[x-8, x+8] × [y-8, y+8]`` 的正方形内随机点击。每次调用
        ``click_at`` 都会重新取样一次。传入 0 或 disabled 会保留原始坐标。
        """
        try:
            radius = int(radius)
        except (TypeError, ValueError):
            radius = 0
        self._click_jitter_radius = max(0, radius) if enabled else 0

    def _randomized_point(self, x: int, y: int,
                          screen_w: int, screen_h: int) -> Tuple[int, int]:
        """在屏幕边界内，从以 (x, y) 为中心的正方形取一个点。"""
        x = int(x)
        y = int(y)
        radius = self._click_jitter_radius
        if radius <= 0:
            return x, y

        min_x = max(0, x - radius)
        max_x = min(max(0, int(screen_w) - 1), x + radius)
        min_y = max(0, y - radius)
        max_y = min(max(0, int(screen_h) - 1), y + radius)
        if min_x > max_x or min_y > max_y:
            return x, y
        return random.randint(min_x, max_x), random.randint(min_y, max_y)

    def _find_window(self) -> int:
        from core.window import resolve_hwnd

        hwnd = resolve_hwnd()
        if hwnd:
            logging.info(f"已绑定目标窗口 HWND={hwnd}")
        else:
            logging.warning(f"未选择目标窗口，{self.method} 后端将无法点击")
        return hwnd

    # ------------------------------------------------------------------
    # 对外点击 API（坐标均为目标分辨率下的屏幕像素）
    # ------------------------------------------------------------------
    def click_at(self, x: int, y: int, screen_w: int = 1920, screen_h: int = 1080):
        x, y = self._randomized_point(x, y, screen_w, screen_h)
        self.backend.click(x, y, screen_w, screen_h)

    def move_mouse_abs(self, x: int, y: int, screen_w: int = 1920, screen_h: int = 1080):
        """移动真实光标（仅 SendInput 后端支持，其它后端忽略）。"""
        mover = getattr(self.backend, "move_abs", None)
        if callable(mover):
            mover(x, y, screen_w, screen_h)

    def click_config(self, key: str, res: Tuple[int, int], config):
        pts = config.click_points.get(key)
        if not pts:
            return
        x, y = pts
        cx = int(x * res[0] / config.base_res[0])
        cy = int(y * res[1] / config.base_res[1])
        self.click_at(cx, cy, res[0], res[1])

    def click_coord(self, x: int, y: int, res: Tuple[int, int]):
        self.click_at(x, y, res[0], res[1])

    def click_region_center(self, region: List[int], res: Tuple[int, int]):
        x, y, w, h = region
        self.click_at(x + w // 2, y + h // 2, res[0], res[1])

    def close(self):
        try:
            self.backend.close()
        except Exception:
            pass
