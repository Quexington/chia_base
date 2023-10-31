from dataclasses import fields, is_dataclass
from types import GenericAlias
from typing import (
    Any,
    BinaryIO,
    List,
    Tuple,
    Type,
    TypeVar,
    Callable,
    get_type_hints,
)


from chia_base.atoms import uint32
from clvm_rs import Program  # type: ignore

from chia_base.meta.type_tree import TypeTree, OriginArgsType, ArgsType


_T = TypeVar("_T")

ParseFunction = Callable[[BinaryIO], _T]


def make_parser_for_dataclass(
    cls: Type, type_tree: TypeTree[ParseFunction]
) -> Callable[[BinaryIO], Any]:
    new_types = tuple(f.type for f in fields(cls))
    g: Any = GenericAlias(tuple, new_types)
    tuple_parser = type_tree(g)

    def parser(f: BinaryIO) -> Any:
        args = tuple_parser(f)
        return cls(*args)

    return parser


def parser_for_list(
    origin_type: Type,
    args_type: ArgsType,
    type_tree: TypeTree[ParseFunction],
) -> ParseFunction:
    """
    Deal with a list.
    """
    if args_type is None:
        raise ValueError("list type not completely specified")
    if len(args_type) != 1:
        raise ValueError("list type has too many specifiers")

    subtype = args_type[0]
    inner_parse: ParseFunction = type_tree(subtype)

    def parse_f(f: BinaryIO) -> List[_T]:
        length = uint32.parse(f)
        return [inner_parse(f) for _ in range(length)]

    return parse_f


def parser_for_tuple(
    origin_type: Type,
    args_type: ArgsType,
    type_tree: TypeTree[ParseFunction],
) -> ParseFunction[Tuple[Any, ...]]:
    """
    Deal with a tuple of types.
    """
    if args_type is None:
        raise ValueError("tuple type not completely specified")
    subparsers: list[ParseFunction] = [type_tree(_) for _ in args_type]

    def parse_f(f: BinaryIO) -> Tuple[Any, ...]:
        return tuple(_(f) for _ in subparsers)

    return parse_f


def parse_bytes(f: BinaryIO) -> bytes:
    size = uint32.parse(f)
    return f.read(size)


def parse_str(f: BinaryIO) -> str:
    return parse_bytes(f).decode()


def extra_make_parser(
    origin: Type, args_type: ArgsType, type_tree: TypeTree[ParseFunction]
) -> None | ParseFunction:
    if hasattr(origin, "parse"):
        return origin.parse
    if is_dataclass(origin):
        return make_parser_for_dataclass(origin, type_tree)
    return None


def parser_type_tree() -> TypeTree[ParseFunction]:
    simple_type_lookup: dict[OriginArgsType, ParseFunction] = {
        (Program, None): Program.parse,
        (bytes, None): parse_bytes,
        (str, None): parse_str,
    }
    compound_type_lookup: dict[
        Type, Callable[[Type, ArgsType, TypeTree[ParseFunction]], ParseFunction]
    ] = {
        list: parser_for_list,
        tuple: parser_for_tuple,
    }
    type_tree: TypeTree[ParseFunction] = TypeTree(
        simple_type_lookup, compound_type_lookup, extra_make_parser
    )
    return type_tree


def make_parser(cls: type) -> ParseFunction:
    return parser_type_tree()(cls)
