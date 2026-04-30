from __future__ import annotations
import typing
from qtpy import QtCore, QtGui, QtWidgets


class _RowMarginDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, margin: int = 8, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._margin = margin

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QSize:
        size = super().sizeHint(option, index)
        return QtCore.QSize(size.width(), size.height() + self._margin * 2)


class QueryBuilderView(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setItemDelegate(
            _RowMarginDelegate(margin=4, parent=self.tree_view)
        )

        palette = self.tree_view.palette()
        palette.setColor(
            QtGui.QPalette.ColorRole.Base,
            palette.color(QtGui.QPalette.ColorRole.Base).lighter(125),
        )

        self.tree_view.setPalette(palette)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.tree_view)

    def setModel(self, model: QtGui.QStandardItemModel) -> None:
        self.tree_view.setModel(model)
