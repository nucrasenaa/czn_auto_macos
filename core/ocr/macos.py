#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""macOS Vision OCR 后端。

通过 PyObjC 调用 Vision.framework，在本地处理 ADB 截取的 numpy 图像；不需要
屏幕录制权限，也不需要把模拟器窗口置于前台。
"""
import logging
from typing import List, Optional

import cv2
import numpy as np

from .base import OcrBackend, TextBox

logger = logging.getLogger(__name__)


class MacOSVisionOcrBackend(OcrBackend):
    name = "macos"

    def __init__(self, lang: str = "zh-cn"):
        try:
            from Foundation import NSData
            import Quartz
            import Vision
        except ImportError as exc:
            raise ImportError(
                "macOS Vision OCR 需要 PyObjC，请执行: "
                "pip install -r requirements-macos.txt"
            ) from exc

        self._NSData = NSData
        self._Quartz = Quartz
        self._Vision = Vision
        self._lang = lang

    def _cgimage(self, frame: np.ndarray):
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            raise ValueError("无法把 OCR 图像编码为 PNG")
        data = self._NSData.alloc().initWithBytes_length_(
            encoded.tobytes(), encoded.nbytes
        )
        source = self._Quartz.CGImageSourceCreateWithData(data, None)
        if source is None:
            raise ValueError("无法创建 ImageIO image source")
        image = self._Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
        if image is None:
            raise ValueError("无法创建 CGImage")
        return image

    def _languages(self):
        if self._lang.startswith("zh"):
            return ["zh-Hans", "zh-Hant", "en-US"]
        return ["en-US"]

    @staticmethod
    def _rect_values(rect):
        try:
            return rect.origin.x, rect.origin.y, rect.size.width, rect.size.height
        except AttributeError:
            return rect[0], rect[1], rect[2], rect[3]

    def scan(self, frame: np.ndarray, region: Optional[list] = None) -> List[TextBox]:
        if frame is None or frame.size == 0:
            return []
        if region:
            ox, oy, w, h = region
            crop = frame[oy:oy + h, ox:ox + w]
        else:
            ox, oy = 0, 0
            crop = frame

        try:
            image = self._cgimage(crop)
            request = self._Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(None)
            request.setRecognitionLevel_(
                self._Vision.VNRequestTextRecognitionLevelAccurate
            )
            request.setRecognitionLanguages_(self._languages())
            handler = self._Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
                image, None
            )
            handler.performRequests_error_([request], None)

            height, width = crop.shape[:2]
            texts: List[TextBox] = []
            for observation in request.results() or []:
                candidates = observation.topCandidates_(1)
                if not candidates:
                    continue
                text = str(candidates[0].string()).strip()
                if not text:
                    continue
                bx, by, bw, bh = self._rect_values(observation.boundingBox())
                x = int(bx * width) + ox
                y = int((1.0 - by - bh) * height) + oy
                texts.append((text, x, y, int(bw * width), int(bh * height)))
            return texts
        except Exception as exc:
            logger.error(f"macOS Vision OCR 识别失败: {exc}")
            return []

    def set_lang(self, lang: str):
        self._lang = lang
