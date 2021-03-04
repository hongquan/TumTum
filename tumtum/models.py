from uuid import uuid4, UUID
from dataclasses import field
from abc import ABCMeta, abstractmethod
from typing import Optional, NamedTuple, List, Tuple

import yarl
from pydantic import BaseModel, Field, AnyHttpUrl
from pydantic.dataclasses import dataclass
from pydantic_initialized import initialized


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


@initialized
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


@initialized
class AppSettings(BaseModel):
    sst: SSTSetting
    aws_demo: AWSSetting


class Backend(metaclass=ABCMeta):
    _start_url = 'start'
    _submit_frame_url = 'frames'
    _verify_url = 'verify'

    @property
    @abstractmethod
    def start_url(self) -> str:
        pass

    @abstractmethod
    def get_submit_frame_url(self, challenge_id: str) -> str:
        pass

    @abstractmethod
    def get_verify_url(self, challenge_id: str) -> str:
        pass


class MyConvention:
    underscore_attrs_are_private = True


@dataclass(config=MyConvention)
class AWSBackend(Backend):
    domain: str
    _base_url = 'https://69hes0gg2k.execute-api.ap-southeast-1.amazonaws.com/Prod/challenge/'
    _start_url = 'start'
    _submit_frame_url = 'frames'
    _verify_url = 'verify'
    _settings: AWSSetting

    @property
    def start_url(self) -> str:
        yarl.URL(self._base_url).with_host(self.domain).join(self._start_url)

    def get_submit_frame_url(self, challenge_id: str) -> str:
        url = yarl.URL(self._base_url).with_host(self.domain).join(challenge_id).join(self._submit_frame_url)
        return str(url)

    def get_verify_url(self, challenge_id: str):
        return str(yarl.URL(self._base_url).with_host(self.domain).join(challenge_id).join(self._verify_url))

    @classmethod
    def from_settings(cls, settings: AWSSetting):
        obj = cls(domain=settings.domain)
        obj._settings = settings
        return obj


@dataclass(config=MyConvention)
class SSTBackend(Backend):
    _base_url = 'http://localhost:8000'
    _settings: SSTSetting
    username: str
    password: str

    @property
    def start_url(self):
        yarl.URL(self._base_url).join(self._start_url)

    def get_submit_frame_url(self, challenge_id: str) -> str:
        return str(yarl.URL(self._base_url).join(challenge_id).join(self._submit_frame_url))

    def get_verify_url(self, challenge_id: str) -> str:
        return str(yarl.URL(self._base_url).join(challenge_id).join(self._verify_url))

    @classmethod
    def from_settings(cls, settings: SSTSetting):
        obj = cls(settings.username, settings.password)
        obj._base_url = settings.base_url
        obj._settings = settings
        return obj
