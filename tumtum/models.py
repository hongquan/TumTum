from datetime import datetime
from uuid import uuid4, UUID
from dataclasses import field
from typing import Optional, NamedTuple, List, Tuple, Dict, Any

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


class APIRequestMixin:

    def request_for_sst(self) -> Dict[str, Any]:
        return self.dict()

    def request_for_aws(self) -> Dict[str, Any]:
        return self.dict(by_alias=True)


def timestamp_ms_now():
    return round(datetime.utcnow().timestamp() * 1000)


class ChallengeStartRequest(APIRequestMixin, BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    image_width: int
    image_height: int

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

    def request_for_sst(self) -> Dict[str, Any]:
        data = self.dict()
        data['external_person_id'] = data.pop('user_id')
        return data


class ChallengeInfo(BaseModel):
    id: UUID
    # SST API returns external_person_id instead of user_id
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
    token: Optional[str] = None

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class FrameSubmitRequest(APIRequestMixin, BaseModel):
    frame_base64: str
    timestamp: int = Field(default_factory=timestamp_ms_now)
    token: Optional[str] = None

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

    def request_for_sst(self) -> Dict[str, Any]:
        data = self.dict()
        data['content'] = data.pop('frame_base64')
        del data['timestamp']
        del data['token']
        return data


class ChallengeVerifyRequest(APIRequestMixin, BaseModel):
    token: Optional[str] = None


class SSTSetting(BaseModel):
    username: str
    password: str
    base_url: AnyHttpUrl = 'http://localhost:8000'


class AWSSetting(BaseModel):
    domain: str


class AppSettings(BaseModel):
    sst: SSTSetting
    aws_demo: AWSSetting
