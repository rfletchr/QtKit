__all__ = ["SchemaHeaderView"]

import typing
from qtpy import QtCore, QtGui, QtWidgets

from .model import SchemaTableModel


class SchemaHeaderView(QtWidgets.QHeaderView):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(QtCore.Qt.Orientation.Horizontal, parent)
        self.sectionResized.connect(self._repositionWidgets)
        self.sectionMoved.connect(self._repositionWidgets)

    def setModel(self, model: QtCore.QAbstractItemModel | None) -> None:
        old = self.model()
        if old is not None:
            old.columnsInserted.disconnect(self._onColumnsInserted)
            old.columnsAboutToBeRemoved.disconnect(self._onColumnsAboutToBeRemoved)
            old.columnsRemoved.disconnect(self._onColumnsRemoved)
            old.columnsMoved.disconnect(self._onColumnsInserted)
            old.modelAboutToBeReset.disconnect(self._onModelAboutToBeReset)
            old.modelReset.disconnect(self._onModelReset)

        super().setModel(model)

        if model is not None:
            model.columnsInserted.connect(self._onColumnsInserted)
            model.columnsAboutToBeRemoved.connect(self._onColumnsAboutToBeRemoved)
            model.columnsRemoved.connect(self._onColumnsRemoved)
            model.columnsMoved.connect(self._onColumnsInserted)
            model.modelAboutToBeReset.connect(self._onModelAboutToBeReset)
            model.modelReset.connect(self._onModelReset)
            self.updateGeometry()

    def _onColumnsInserted(self) -> None:
        self._repositionWidgets()
        self.updateGeometry()

    def _onColumnsAboutToBeRemoved(self, _, first: int, last: int) -> None:
        model = self.model()
        if not isinstance(model, SchemaTableModel):
            return
        for i in range(first, last + 1):
            col = model.columnAt(i)
            if col is not None:
                w = col.headerWidget(self.viewport())
                if w is not None:
                    w.hide()

    def _onColumnsRemoved(self) -> None:
        self._repositionWidgets()
        self.updateGeometry()

    def _onModelAboutToBeReset(self) -> None:
        model = self.model()
        if not isinstance(model, SchemaTableModel):
            return
        for i in range(model.columnCount()):
            col = model.columnAt(i)
            if col is not None:
                w = col.headerWidget(self.viewport())
                if w is not None:
                    w.hide()

    def _onModelReset(self) -> None:
        self._repositionWidgets()
        self.updateGeometry()

    def _labelHeight(self) -> int:
        return super().sizeHint().height()

    def _maxWidgetHeight(self) -> int:
        model = self.model()
        if not isinstance(model, SchemaTableModel):
            return 0
        vp = self.viewport()
        if vp is None:
            return 0
        max_h = 0
        for i in range(model.columnCount()):
            col = model.columnAt(i)
            if col is not None:
                w = col.headerWidget(vp)
                if w is not None:
                    max_h = max(max_h, w.sizeHint().height())
        return max_h

    def sizeHint(self) -> QtCore.QSize:
        s = super().sizeHint()
        return QtCore.QSize(s.width(), s.height() + self._maxWidgetHeight())

    def _repositionWidgets(self) -> None:
        model = self.model()
        if not isinstance(model, SchemaTableModel):
            return
        vp = self.viewport()
        if vp is None:
            return
        label_h = self._labelHeight()
        for i in range(model.columnCount()):
            col = model.columnAt(i)
            if col is None:
                continue
            w = col.headerWidget(vp)
            if w is None:
                continue
            x = self.sectionViewportPosition(i)
            w.setGeometry(x, label_h, self.sectionSize(i), w.sizeHint().height())
            w.setVisible(not self.isSectionHidden(i))

    def paintSection(
        self, painter: QtGui.QPainter, rect: QtCore.QRect, logical_index: int
    ) -> None:
        label_rect = QtCore.QRect(rect.x(), rect.y(), rect.width(), self._labelHeight())
        super().paintSection(painter, label_rect, logical_index)

    def updateGeometries(self) -> None:
        super().updateGeometries()
        self._repositionWidgets()
