from dataclasses import dataclass


# TODO: use pydantic instead?
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
