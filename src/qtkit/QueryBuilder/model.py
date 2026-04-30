from __future__ import annotations
import enum
import typing
from qtpy import QtCore, QtGui
from qtkit.CustomRoleEnum import QtCustomRoleEnum
from .api import Field, Comparison, AndOperator, OrOperator


class NodeRole(QtCustomRoleEnum):
    NodeType = enum.auto()  # "group" | "comparison"
    GroupOp = enum.auto()  # "AND" | "OR"
    Field = enum.auto()  # Field object
    Operator = enum.auto()  # str
    Value = enum.auto()  # str


class QueryModel(QtGui.QStandardItemModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self.invisibleRootItem().appendRow(self._makeGroupItem("AND"))

    def _makeGroupItem(self, op: str) -> QtGui.QStandardItem:
        item = QtGui.QStandardItem(op)
        item.setData("group", NodeRole.NodeType)
        item.setData(op, NodeRole.GroupOp)
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        return item

    def _makeComparisonItem(self, field: Field) -> QtGui.QStandardItem:
        item = QtGui.QStandardItem()
        item.setData("comparison", NodeRole.NodeType)
        item.setData(field, NodeRole.Field)
        item.setData(field.default_operator, NodeRole.Operator)
        item.setData("", NodeRole.Value)
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        return item

    def addComparison(self, parent_index: QtCore.QModelIndex, field: Field) -> None:
        parent_item = self.itemFromIndex(parent_index) or self.item(0, 0)
        if parent_item is None:
            return
        parent_item.appendRow(self._makeComparisonItem(field))

    def addGroup(self, parent_index: QtCore.QModelIndex, op: str = "AND") -> None:
        parent_item = self.itemFromIndex(parent_index) or self.item(0, 0)
        if parent_item is None:
            return
        parent_item.appendRow(self._makeGroupItem(op))

    def nodeFromIndex(
        self, index: QtCore.QModelIndex
    ) -> Comparison | AndOperator | OrOperator | None:
        if not index.isValid():
            return None
        item = self.itemFromIndex(index)
        if item is None:
            return None
        node_type = item.data(NodeRole.NodeType)
        if node_type == "comparison":
            return Comparison(
                field=item.data(NodeRole.Field),
                operator=item.data(NodeRole.Operator),
                value=item.data(NodeRole.Value),
            )
        if node_type == "group":
            op = item.data(NodeRole.GroupOp)
            children: list[Comparison | AndOperator | OrOperator] = []
            for row in range(item.rowCount()):
                child = self.nodeFromIndex(self.index(row, 0, index))
                if child is not None:
                    children.append(child)
            return (
                AndOperator(comparisons=children)
                if op == "AND"
                else OrOperator(comparisons=children)
            )
        return None

    def loadFromNode(self, node: AndOperator | OrOperator) -> None:
        self.beginResetModel()
        super().clear()
        self._buildItem(self.invisibleRootItem(), node)
        self.endResetModel()

    def _buildItem(
        self, parent: QtGui.QStandardItem, node: Comparison | AndOperator | OrOperator
    ) -> None:
        if isinstance(node, (AndOperator, OrOperator)):
            op = "AND" if isinstance(node, AndOperator) else "OR"
            item = self._makeGroupItem(op)
            parent.appendRow(item)
            for child in node.comparisons:
                self._buildItem(item, child)
        elif isinstance(node, Comparison):
            item = self._makeComparisonItem(node.field)
            item.setData(node.operator, NodeRole.Operator)
            item.setData(node.value, NodeRole.Value)
            parent.appendRow(item)

    def build(self) -> AndOperator | OrOperator | None:
        root = self.item(0, 0)
        if root is None:
            return None
        return self.nodeFromIndex(self.indexFromItem(root))
