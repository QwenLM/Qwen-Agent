
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # system / user / assistant
    content: str

    def to_str(self) -> str:
        return f'{self.role}: {self.content}'

    def to_dict(self) -> dict:
        return {
            'role': self.role,
            'content': self.content
        }


@dataclass
class Record:
    url: str
    time: str
    type: str
    raw: list
    extract: str
    topic: str
    checked: bool
    session: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'time': self.time,
            'type': self.type,
            'raw': self.raw,
            'extract': self.extract,
            'topic': self.topic,
            'checked': self.checked,
            'session': self.session
        }


@dataclass
class RefMaterial:
    url: str
    text: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'text': self.text,
        }
