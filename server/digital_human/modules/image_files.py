"""OpenCV image I/O that supports Windows Unicode paths."""
from pathlib import Path
import cv2
import numpy as np


def write_image(path, image):
    target = Path(path)
    encoded_ok, encoded = cv2.imencode(target.suffix or '.png', image)
    if not encoded_ok:
        raise ValueError('图片编码失败')
    encoded.tofile(str(target))


def read_image(path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'无法读取图片：{Path(path).name}')
    return image
