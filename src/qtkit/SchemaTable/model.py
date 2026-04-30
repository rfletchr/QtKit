__all__ = [
    "SchemaColumn",
    "ComboBoxHeaderMixin",
    "AttributeColumn",
    "Handle",
    "INVALID_HANDLE",
    "SchemaTableModel",
]
import threading
import typing
from qtpy import QtCore, QtGui, QtWidgets

T = typing.TypeVar("T")

IndexType = QtCore.QModelIndex | QtCore.QPersistentModelIndex
RoleType = int | QtCore.Qt.ItemDataRole


class SchemaColumn(QtCore.QObject, typing.Generic[T]):
    """
    Base class for a column in SchemaTableModel.

    Subclass and implement getData() and header() to define how a column extracts
    and displays data from a row item. Override flags() or setData() to support
    selection behaviour or editing.

    Being a QObject allows columns to emit signals — useful for async patterns
    such as thumbnail loading, where the column emits when data is ready and the
    model can emit dataChanged for affected cells.
    """

    filterChanged = QtCore.Signal(str)

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self.__model: typing.Optional["SchemaTableModel[T]"] = None
        self.__column_index: typing.Optional[int] = None

    def hasCompletionModel(self) -> bool:
        return False

    def completionModel(self) -> QtCore.QAbstractItemModel:
        raise NotImplementedError("This column does not support completion model")

    def attachModel(self, model: "SchemaTableModel[T]") -> None:
        if self.__model is not None:
            raise ValueError("Column is already attached to a model")

        self.__model = model

    def detachModel(self) -> None:
        self.__model = None

    def setColumnIndex(self, index: int) -> None:
        self.__column_index = index

    def columnIndex(self) -> int:
        if self.__column_index is None:
            raise ValueError("Column index is not set")
        return self.__column_index

    def hasModel(self) -> bool:
        return self.__model is not None

    def model(self) -> "SchemaTableModel[T]":
        if self.__model is None:
            raise ValueError("Column is not attached to a model")
        return self.__model

    def flags(self, item: T) -> QtCore.Qt.ItemFlag:
        return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

    def getData(
        self,
        item: T,
        role: RoleType,
        index: IndexType,
    ) -> typing.Any:
        raise NotImplementedError

    def setData(
        self,
        item: T,
        value: typing.Any,
        role: RoleType,
        index: IndexType,
    ) -> bool:
        return False

    def header(
        self,
        role: RoleType,
        index: IndexType,
    ) -> typing.Any:
        raise NotImplementedError

    def headerWidget(
        self, parent: QtWidgets.QWidget
    ) -> typing.Optional[QtWidgets.QWidget]:
        return None


class ComboBoxHeaderMixin(SchemaColumn[T]):
    """
    Mixin for SchemaColumn subclasses that provides a QComboBox header widget
    backed by a QStandardItemModel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._combo_widget: typing.Optional[QtWidgets.QComboBox] = None
        self._combo_model = QtGui.QStandardItemModel()
        self._completer = QtWidgets.QCompleter(self._combo_model)
        self._completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.PopupCompletion
        )

    def hasCompletionModel(self) -> bool:
        return True

    def completionModel(self) -> QtGui.QStandardItemModel:
        return self._combo_model

    def headerWidget(self, parent: QtWidgets.QWidget) -> QtWidgets.QComboBox:
        if self._combo_widget is None:
            self._combo_widget = QtWidgets.QComboBox(parent)
            self._combo_widget.setModel(self._combo_model)
            self._combo_widget.setCompleter(self._completer)
            self._combo_widget.setEditable(True)
            self._combo_widget.currentTextChanged.connect(self.filterChanged)
        return self._combo_widget


class LineEditHeaderMixin(SchemaColumn[T]):
    """
    Mixin for SchemaColumn subclasses that provides a QLineEdit header widget.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._line_edit_widget: typing.Optional[QtWidgets.QLineEdit] = None
        self._model = QtGui.QStandardItemModel()

    def hasCompletionModel(self) -> bool:
        return True

    def completionModel(self) -> QtGui.QStandardItemModel:
        return self._model

    def headerWidget(self, parent: QtWidgets.QWidget) -> QtWidgets.QLineEdit:
        if self._line_edit_widget is None:
            self._line_edit_widget = QtWidgets.QLineEdit(parent)
            completer = QtWidgets.QCompleter(self._model, self._line_edit_widget)
            completer.setCompletionMode(
                QtWidgets.QCompleter.CompletionMode.PopupCompletion
            )
            self._line_edit_widget.setCompleter(completer)
            self._line_edit_widget.textChanged.connect(self.filterChanged)
        return self._line_edit_widget


class AttributeColumn(SchemaColumn[T]):
    def __init__(
        self,
        header_name: str,
        attribute: str,
        mutable: bool = False,
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        self._header_name = header_name
        self._attribute = attribute
        self._mutable = mutable

    def getData(
        self,
        item: T,
        role: RoleType,
        index: IndexType,
    ) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return getattr(item, self._attribute)
        return None

    def setData(
        self,
        item: T,
        value: typing.Any,
        role: RoleType,
        index: IndexType,
    ) -> bool:
        if not self._mutable:
            return False

        if role == QtCore.Qt.ItemDataRole.EditRole:
            setattr(item, self._attribute, value)
            return True
        return False

    def flags(self, item: T) -> QtCore.Qt.ItemFlag:
        base_flags = super().flags(item)
        if self._mutable:
            return base_flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return base_flags

    def header(
        self,
        role: RoleType,
        index: IndexType,
    ) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._header_name
        return None


class DictKeyColumn(SchemaColumn[dict]):
    def __init__(
        self,
        header_name: str,
        key: typing.Any,
        mutable: bool = False,
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        self._header_name = header_name
        self._key = key
        self._mutable = mutable

    def getData(
        self,
        item: dict,
        role: RoleType,
        index: IndexType,
    ) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return item[self._key]
        return None

    def setData(
        self,
        item: dict,
        value: typing.Any,
        role: RoleType,
        index: IndexType,
    ) -> bool:
        if not self._mutable:
            return False

        if role == QtCore.Qt.ItemDataRole.EditRole:
            item[self._key] = value
            return True
        return False

    def flags(self, item: dict) -> QtCore.Qt.ItemFlag:
        base_flags = super().flags(item)
        if self._mutable:
            return base_flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return base_flags

    def header(
        self,
        role: RoleType,
        index: IndexType,
    ) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._header_name
        return None


class Slot(typing.Generic[T]):
    """
    Wraps a row item with a generation counter.

    Generation increments on each successful setData(), allowing delegates or
    async workers to detect whether their result is still current before
    applying it. Not thread-safe on its own — callers must hold the model lock.
    """

    def __init__(self, item: T):
        self.item = item
        self.generation: int = 0


class Handle(typing.NamedTuple):
    row: int
    row_generation: int
    model_generation: int


INVALID_HANDLE = Handle(-1, -1, -1)


class SchemaTableModel(QtCore.QAbstractTableModel, typing.Generic[T]):
    """
    Generic table model driven by a column strategy/schema pattern.

    Columns are fixed at construction; rows are updated via setRows(). All
    display logic — data extraction, headers, flags, editing — is delegated
    to SchemaColumn instances. The model itself contains no column-specific
    branching.

    The model maintains generation counters for rows and the overall model to help detect stale data in async scenarios.
    For Columns which need to gather data asynchronously (e.g. thumbnails), they can take a handle from the model and check its validity before applying results, ensuring that updates are only applied to the intended row and model state.
    """

    def __init__(
        self,
        columns: typing.Sequence[SchemaColumn[T]],
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        self.__columns = list(columns)
        self.__rows: list[Slot] = []
        self.__lock = threading.Lock()
        self.__generation = 0

        for i, column in enumerate(self.__columns):
            column.attachModel(self)
            column.setColumnIndex(i)

    def setRows(self, rows: typing.List[T]) -> None:
        self.beginResetModel()
        with self.__lock:
            self.__rows = [Slot(item) for item in rows]
            self.__generation += 1
        self.endResetModel()

    def rowCount(self, parent: IndexType = QtCore.QModelIndex()) -> int:
        return len(self.__rows)

    def columnCount(self, parent: IndexType = QtCore.QModelIndex()) -> int:
        return len(self.__columns)

    def data(
        self,
        index: IndexType,
        role: RoleType = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        if not index.isValid():
            return None
        if index.row() >= len(self.__rows) or index.row() < 0:
            return None
        if index.column() >= len(self.__columns) or index.column() < 0:
            return None

        item = self.__rows[index.row()].item
        column = self.__columns[index.column()]
        return column.getData(item, role, index)

    def handle(self, index: IndexType) -> Handle:
        if not index.isValid():
            return INVALID_HANDLE
        if index.row() >= len(self.__rows) or index.row() < 0:
            return INVALID_HANDLE
        if index.column() >= len(self.__columns) or index.column() < 0:
            return INVALID_HANDLE

        with self.__lock:
            row_generation = self.__rows[index.row()].generation
            model_generation = self.__generation
        return Handle(index.row(), row_generation, model_generation)

    def isHandleValid(self, handle: Handle) -> bool:
        if handle == INVALID_HANDLE:
            return False
        with self.__lock:
            if handle.model_generation != self.__generation:
                return False
            if handle.row < 0 or handle.row >= len(self.__rows):
                return False
            return self.__rows[handle.row].generation == handle.row_generation

    def setData(
        self,
        index: IndexType,
        value: typing.Any,
        role: RoleType = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        if index.row() >= len(self.__rows) or index.row() < 0:
            return False
        if index.column() >= len(self.__columns) or index.column() < 0:
            return False

        slot = self.__rows[index.row()]

        column = self.__columns[index.column()]
        result = column.setData(slot.item, value, role, index)
        if result:
            with self.__lock:
                slot.generation += 1
            self.dataChanged.emit(index, index, [role])
        return result

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: RoleType = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        if orientation == QtCore.Qt.Orientation.Horizontal:
            if section >= len(self.__columns) or section < 0:
                return None
            column = self.__columns[section]
            return column.header(role, QtCore.QModelIndex())
        else:
            return super().headerData(section, orientation, role)

    def flags(self, index: IndexType) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        if index.row() >= len(self.__rows) or index.row() < 0:
            return QtCore.Qt.ItemFlag.NoItemFlags
        if index.column() >= len(self.__columns) or index.column() < 0:
            return QtCore.Qt.ItemFlag.NoItemFlags

        item = self.__rows[index.row()].item
        column = self.__columns[index.column()]
        return column.flags(item)

    def insertColumns(
        self,
        column: int,
        columns: typing.List[SchemaColumn[T]],
        parent: IndexType = QtCore.QModelIndex(),
    ) -> bool:
        if not columns:
            return False
        self.beginInsertColumns(parent, column, column + len(columns) - 1)
        self.__columns[column:column] = columns

        for i, col in enumerate(columns):
            col.attachModel(self)
            col.setColumnIndex(column + i)

        self.endInsertColumns()
        return True

    def removeColumns(
        self,
        column: int,
        count: int,
        parent: IndexType = QtCore.QModelIndex(),
    ) -> bool:
        if count <= 0:
            return False
        self.beginRemoveColumns(parent, column, column + count - 1)

        for col in self.__columns[column : column + count]:
            col.detachModel()

        del self.__columns[column : column + count]

        for i, col in enumerate(self.__columns):
            col.setColumnIndex(i)

        self.endRemoveColumns()
        return True

    def moveColumns(
        self,
        sourceParent: IndexType,
        sourceColumn: int,
        count: int,
        destinationParent: IndexType,
        destinationChild: int,
    ) -> bool:
        last = sourceColumn + count - 1
        if not self.beginMoveColumns(
            sourceParent, sourceColumn, last, destinationParent, destinationChild
        ):
            return False

        moving = self.__columns[sourceColumn : sourceColumn + count]
        del self.__columns[sourceColumn : sourceColumn + count]
        insert_at = (
            destinationChild
            if destinationChild < sourceColumn
            else destinationChild - count
        )
        self.__columns[insert_at:insert_at] = moving

        for i, col in enumerate(self.__columns):
            col.setColumnIndex(i)

        self.endMoveColumns()
        return True

    def columnAt(self, column: int) -> typing.Optional[SchemaColumn[T]]:
        if column < 0 or column >= len(self.__columns):
            return None
        return self.__columns[column]

    def rowAt(self, row: int) -> typing.Optional[T]:
        if row < 0 or row >= len(self.__rows):
            return None
        return self.__rows[row].item
