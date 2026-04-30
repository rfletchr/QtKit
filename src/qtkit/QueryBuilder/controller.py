from __future__ import annotations
import typing
from qtpy import QtCore
from .api import Field, AndOperator, OrOperator
from .model import QueryModel, NodeRole
from .view import QueryBuilderView
from .widgets import ComparisonWidget, GroupWidget


class QueryBuilderController(QtCore.QObject):
    queryChanged = QtCore.Signal()

    def __init__(
        self,
        fields: list[Field],
        view: typing.Optional[QueryBuilderView] = None,
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent=parent)
        self._fields = list(fields)
        self._model = QueryModel()
        self._view = view or QueryBuilderView()
        self._view.setModel(self._model)

        self._model.rowsInserted.connect(self._onRowsInserted)

        root_index = self._model.index(0, 0)
        self._decorateIndex(root_index)
        self._view.tree_view.expand(root_index)

    def view(self) -> QueryBuilderView:
        return self._view

    def build(self) -> AndOperator | OrOperator | None:
        return self._model.build()

    def load(self, data: dict) -> None:
        from .serialization import deserialize

        node = deserialize(data, self._fields)
        if not isinstance(node, (AndOperator, OrOperator)):
            return
        self._model.loadFromNode(node)
        self._decorateAll()
        self._view.tree_view.expandAll()

    def _decorateAll(self) -> None:
        self._walkAndDecorate(QtCore.QModelIndex())

    def _walkAndDecorate(self, parent: QtCore.QModelIndex) -> None:
        for row in range(self._model.rowCount(parent)):
            index = self._model.index(row, 0, parent)
            self._decorateIndex(index)
            self._walkAndDecorate(index)

    def _onRowsInserted(self, parent: QtCore.QModelIndex, first: int, last: int) -> None:
        self._view.tree_view.expand(parent)
        for row in range(first, last + 1):
            index = self._model.index(row, 0, parent)
            self._decorateIndex(index)
        self.queryChanged.emit()

    def _decorateIndex(self, index: QtCore.QModelIndex) -> None:
        item = self._model.itemFromIndex(index)
        if item is None:
            return
        node_type = item.data(NodeRole.NodeType)
        persistent = QtCore.QPersistentModelIndex(index)

        if node_type == "comparison":
            field: typing.Optional[Field] = item.data(NodeRole.Field)
            operator: str = item.data(NodeRole.Operator) or ""
            value: str = item.data(NodeRole.Value) or ""

            widget = ComparisonWidget(self._fields, self._view.tree_view)
            if field is not None:
                widget.setField(field)
            widget.setOperator(operator)
            widget.setValue(value)

            widget.changed.connect(
                lambda p=persistent, w=widget: self._onComparisonChanged(p, w)
            )
            widget.removeRequested.connect(
                lambda p=persistent: self._onRemoveRequested(p)
            )
            self._view.tree_view.setIndexWidget(index, widget)

        elif node_type == "group":
            op: str = item.data(NodeRole.GroupOp) or "AND"
            is_root = not index.parent().isValid()
            group_widget = GroupWidget(op, is_root=is_root, parent=self._view.tree_view)

            group_widget.operatorChanged.connect(
                lambda new_op, p=persistent: self._onOperatorChanged(p, new_op)
            )
            group_widget.addComparisonRequested.connect(
                lambda p=persistent: self._onAddComparison(p)
            )
            group_widget.addGroupRequested.connect(
                lambda p=persistent: self._onAddGroup(p)
            )
            group_widget.removeRequested.connect(
                lambda p=persistent: self._onRemoveRequested(p)
            )
            self._view.tree_view.setIndexWidget(index, group_widget)

    def _onComparisonChanged(
        self, persistent: QtCore.QPersistentModelIndex, widget: ComparisonWidget
    ) -> None:
        if not persistent.isValid():
            return
        item = self._model.itemFromIndex(QtCore.QModelIndex(persistent))
        if item is None:
            return
        item.setData(widget.currentField(), NodeRole.Field)
        item.setData(widget.currentOperator(), NodeRole.Operator)
        item.setData(widget.currentValue(), NodeRole.Value)
        self.queryChanged.emit()

    def _onOperatorChanged(self, persistent: QtCore.QPersistentModelIndex, op: str) -> None:
        if not persistent.isValid():
            return
        item = self._model.itemFromIndex(QtCore.QModelIndex(persistent))
        if item is None:
            return
        item.setData(op, NodeRole.GroupOp)
        self.queryChanged.emit()

    def _onAddComparison(self, persistent: QtCore.QPersistentModelIndex) -> None:
        if not persistent.isValid() or not self._fields:
            return
        self._model.addComparison(QtCore.QModelIndex(persistent), self._fields[0])

    def _onAddGroup(self, persistent: QtCore.QPersistentModelIndex) -> None:
        if not persistent.isValid():
            return
        self._model.addGroup(QtCore.QModelIndex(persistent))

    def _onRemoveRequested(self, persistent: QtCore.QPersistentModelIndex) -> None:
        if not persistent.isValid():
            return
        index = QtCore.QModelIndex(persistent)
        self._model.removeRow(index.row(), index.parent())
        self.queryChanged.emit()
