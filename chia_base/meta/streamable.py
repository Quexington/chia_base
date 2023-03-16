from typing import Type, BinaryIO, TypeVar

import io

from .make_parser import make_parser
from .make_streamer import make_streamer


_T = TypeVar("T")
_U = TypeVar("U")


class Streamable:
    def __init_subclass__(subclass):
        super().__init_subclass__()
        Streamable.__build_stream_and_parse(subclass)

    @classmethod
    def __build_stream_and_parse(cls: Type[_T], subclass: Type[_U]):
        """
        Augment the subclass with two dynamically generated methods:
        _class_stream: Callable[[Type[_T], BinaryIO], None]
        _parse: Callable[Type[_T], BinaryIO], _T]
        """
        subclass._class_stream = make_streamer(subclass)
        subclass._parse = make_parser(subclass)

    @classmethod
    def from_bytes(cls: Type[_T], blob: bytes) -> _T:
        return cls.parse(io.BytesIO(blob))

    @classmethod
    def parse(cls: Type[_T], f: BinaryIO) -> _T:
        return cls._parse(cls, f)

    def stream(self, f: BinaryIO) -> None:
        return self._class_stream(f)

    def __bytes__(self):
        f = io.BytesIO()
        self.stream(f)
        return f.getvalue()