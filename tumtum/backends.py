import dataclasses
from abc import ABCMeta, abstractmethod

import yarl
from .models import AWSSetting, SSTSetting


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


@dataclasses.dataclass
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


@dataclasses.dataclass
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
