"""Inspect actual decoded video frames; never infer full-body quality from a filename."""
import math
from pathlib import Path
import cv2
import numpy as np


def inspect_video(path: Path) -> dict:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError('无法解码视频，请上传 H.264 编码的 MP4')
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not math.isfinite(fps) or fps <= 0 or frames < 2 or min(width, height) < 256:
            raise ValueError('视频无有效画面或分辨率过低，宽高至少256像素')
        duration = frames / fps
        if not 3 <= duration <= 30:
            raise ValueError('动作视频长度须为3至30秒')
        samples = []
        for index in np.linspace(0, frames - 1, 12).astype(int):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
            ok, frame = capture.read()
            if not ok:
                raise ValueError('视频包含无法解码的画面')
            # Exclude the head region. Motion here is only a screening signal,
            # not proof of natural gestures or identity consistency.
            gray = cv2.cvtColor(cv2.resize(frame, (160, 240)), cv2.COLOR_BGR2GRAY)
            samples.append(gray[80:, 24:136])
        differences = [float(np.mean(cv2.absdiff(samples[0], frame))) for frame in samples[1:]]
        if max(differences) < 1.0:
            raise ValueError('视频身体区域没有明显变化，静态海报视频不能作为动作素材')
        return {'kind': 'motion_candidate', 'duration': round(duration, 2),
                'width': width, 'height': height, 'fps': round(fps, 2),
                'message': '已检测到画面动作，请预览确认人物全身、动作自然及首尾衔接'}
    finally:
        capture.release()
