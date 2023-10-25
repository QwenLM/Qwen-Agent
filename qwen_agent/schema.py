from dataclasses import dataclass


# TODO: use pydantic instead?
@dataclass
class RefMaterial:
    url: str
    text: list

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'text': self.text,
        }
