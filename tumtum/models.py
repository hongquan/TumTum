from uuid import uuid4, UUID
from dataclasses import field
from typing import Optional, NamedTuple, List, Tuple

from pydantic import BaseModel, Field, AnyHttpUrl
from pydantic.dataclasses import dataclass


class Rectangle(NamedTuple):
    x: int
    y: int
    width: int
    height: int


@dataclass
class OverlayDrawData:
    face_box: Optional[Rectangle] = None
    nose_bridge: List[Tuple[int, int]] = field(default_factory=list)
    nose_tip: List[Tuple[int, int]] = field(default_factory=list)


def to_camel(string: str) -> str:
    parts = string.split('_')
    parts[1:] = [w.capitalize() for w in parts[1:]]
    return ''.join(parts)


class ChallengeStartRequest(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    image_width: int
    image_height: int

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class ChallengeInfo(BaseModel):
    id: UUID
    user_id: UUID
    image_width: int
    image_height: int
    area_left: int
    area_top: int
    area_width: int
    area_height: int
    min_face_area_percent: int
    nose_left: int
    nose_top: int
    nose_width: int
    nose_height: int
    token: str

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class FrameSubmitRequest(BaseModel):
    frame_base64: str
    timestamp: int
    token: str

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class ChallengeVerifyRequest(BaseModel):
    token: str


class SSTSetting(BaseModel):
    username: str
    password: str
    base_url: AnyHttpUrl = 'http://localhost:8000'


class AWSSetting(BaseModel):
    domain: str


class AppSettings(BaseModel):
    sst: SSTSetting
    aws_demo: AWSSetting
