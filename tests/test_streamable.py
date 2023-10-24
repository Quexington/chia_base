from dataclasses import dataclass

import io

import pytest

from clvm_rs import Program

from chia_base.atoms.ints import int8, int16, uint16, int32, int64, uint64
from chia_base.atoms.sized_bytes import bytes32
from chia_base.bls12_381 import BLSSecretExponent
from chia_base.meta.streamable import (
    Streamable,
    make_parser,
    make_streamer,
    EncodingError,
)


@dataclass
class Foo8(Streamable):
    v1: int8


@dataclass
class Foo16(Streamable):
    v1: int16


@dataclass
class Bytes32(Streamable):
    v1: bytes32


@dataclass
class Compound(Streamable):
    v1: Foo8
    v2: Foo16


@dataclass
class Str(Streamable):
    v: str


@dataclass
class Bytes(Streamable):
    v: bytes


@dataclass
class PWrapper(Streamable):
    p: Program


@dataclass
class Foo1664(Streamable):
    v1: int16
    v2: int64


@dataclass
class Minicoin(Streamable):
    pci: bytes32
    ph: bytes32
    amount: uint64


@dataclass
class TupleTest(Streamable):
    v1: int64
    v2: tuple[int32, int64, Program, str, bytes]


def bytes_for_class_streamable(s) -> bytes:
    f = io.BytesIO()
    s.__class__._class_stream(s, f)
    return f.getvalue()


def test_simple():
    def check_rt(obj, hexpected):
        b = bytes_for_class_streamable(obj)
        assert b.hex() == hexpected
        new_obj = obj.__class__.parse(io.BytesIO(b))
        assert obj == new_obj

    check_rt(Foo8(100), "64")
    check_rt(Foo16(100), "0064")
    check_rt(Foo1664(5000, 10000), "13880000000000002710")
    mc_ex = "30" * 32 + "31" * 32 + "0000000038e9c287"
    check_rt(Minicoin(b"0" * 32, b"1" * 32, 954843783), mc_ex)
    check_rt(Compound(Foo8(100), Foo16(200)), "6400c8")
    check_rt(Str("Hello there"), "0000000b48656c6c6f207468657265")
    check_rt(Bytes(b"Hello there"), "0000000b48656c6c6f207468657265")
    check_rt(Bytes32(b"0" * 32), "30" * 32)
    check_rt(PWrapper(Program.fromhex("80")), "80")
    prog = Program.fromhex("ff826869ff85746865726580")
    hexp = (
        "00000000deadbeef00d5aa96000000000000"
        "faceff826869ff8574686572658000000003666f6f00000003626172"
    )
    check_rt(TupleTest(0xDEADBEEF, (0xD5AA96, 0xFACE, prog, "foo", b"bar")), hexp)


Unstreamable = set


def test_failure():
    with pytest.raises(ValueError):
        make_parser(Unstreamable)
    with pytest.raises(ValueError):
        make_streamer(Unstreamable)
    with pytest.raises(ValueError):

        @dataclass
        class Fail(Streamable):
            v: Unstreamable

    streamer = make_streamer(tuple[uint16, int16])
    f = io.BytesIO()
    with pytest.raises(EncodingError):
        streamer([100], f)


def test_bls_sig():
    # this silly test is to bring coverage to 100% in bls12_381
    sig = BLSSecretExponent.from_int(1).sign(b"foo")
    f = io.BytesIO()
    sig.stream(f)
    assert f.getvalue().hex() == (
        "95b25e3a238209151876ca040b7bf2fac3aaec67af02885118daac0347bbc3beec07958e"
        "6d0ef9822ae2b1544e7884e40eeffcefba6dd43caf618a151644e068755eee5f1096718f"
        "0c0f4c4c0ebe00103e875ac740b0d49910135a51f4e4e9ec"
    )
