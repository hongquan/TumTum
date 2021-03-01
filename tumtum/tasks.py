from typing import Optional

import numpy as np
import face_recognition
from PIL import Image
from logbook import Logger

from .models import Rectangle, OverlayDrawData


logger = Logger(__name__)


def detect_face(img: Image.Image) -> Optional[OverlayDrawData]:
    nimp = np.asarray(img)
    faces = face_recognition.face_locations(nimp)
    logger.debug('Faces: {}', faces)
    if faces:
        # face_recognition return result as (top, right, bottom, left)
        t, r, b, le = faces[0]
        rect = Rectangle(le, t, r - le, b - t)
        landmarks = face_recognition.face_landmarks(nimp)
        logger.debug('Landmarks: {}', landmarks)
        nose_bridge = landmarks[0]['nose_bridge']
        nose_tip = landmarks[0]['nose_tip']
        draw_data = OverlayDrawData(face_box=rect, nose_bridge=nose_bridge, nose_tip=nose_tip)
        return draw_data
    return None
