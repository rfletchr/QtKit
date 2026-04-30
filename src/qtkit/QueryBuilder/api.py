from __future__ import annotations
import typing
import dataclasses

from qtpy import QtCore, QtGui, QtWidgets


@dataclasses.dataclass
class Field:
    name: str
    type: typing.Type
    operators: list[str]
    value_model: QtCore.QAbstractItemModel | None
    allow_custom_values: bool
    default_operator: str


@dataclasses.dataclass
class Comparison:
    field: Field
    operator: str
    value: str


@dataclasses.dataclass
class AndOperator:
    comparisons: list["Comparison | AndOperator | OrOperator"]


@dataclasses.dataclass
class OrOperator:
    comparisons: list["Comparison | AndOperator | OrOperator"]
