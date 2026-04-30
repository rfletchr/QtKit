import sys
import dataclasses
from qtpy import QtWidgets, QtGui, QtCore
from qtkit.SchemaTable import (
    SchemaTableModel,
    AttributeColumn,
    ComboBoxHeaderMixin,
    SchemaHeaderView,
    SchemaColumn,
)


@dataclasses.dataclass
class Person:
    name: str
    department: str
    salary: float
    active: bool


PEOPLE = [
    Person("Alice", "Engineering", 95000, True),
    Person("Bob", "Design", 82000, True),
    Person("Carol", "Engineering", 105000, False),
    Person("Dave", "HR", 74000, True),
    Person("Eve", "Design", 88000, False),
    Person("Frank", "Engineering", 112000, True),
    Person("Grace", "HR", 71000, True),
    Person("Heidi", "Design", 79000, False),
]


class DepartmentColumn(ComboBoxHeaderMixin, AttributeColumn):
    def __init__(self):
        super().__init__("Department", "department")
        for dept in ("", "Engineering", "Design", "HR"):
            self.completionModel().appendRow(QtGui.QStandardItem(dept))


class ActiveColumn(AttributeColumn):
    def __init__(self):
        super().__init__("Active", "active")

    def getData(self, item, role, index):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return "Yes" if item.active else "No"
        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            return QtGui.QColor("green") if item.active else QtGui.QColor("red")
        return None


class PersonFilter(QtCore.QSortFilterProxyModel):
    def __init__(self, source: SchemaTableModel[Person], parent=None):
        super().__init__(parent=parent)
        self._filters: dict[int, str] = {}
        self.setSourceModel(source)

    def setFilter(self, column: int, value: str) -> None:
        if value:
            self._filters[column] = value
        else:
            self._filters.pop(column, None)
        self.invalidateFilter()

    def filterAcceptsRow(
        self,
        source_row: int,
        _source_parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> bool:
        source = self.sourceModel()
        assert isinstance(source, SchemaTableModel)
        person = source.rowAt(source_row)
        if person is None:
            return False
        for col_idx, filter_value in self._filters.items():
            col = source.columnAt(col_idx)
            if col is None:
                continue
            display = col.getData(
                person,
                QtCore.Qt.ItemDataRole.DisplayRole,
                source.index(source_row, col_idx),
            )
            if filter_value.lower() not in str(display).lower():
                return False
        return True


class PersonTableView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.header = SchemaHeaderView()
        self.table_view = QtWidgets.QTableView()
        self.table_view.setHorizontalHeader(self.header)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setAlternatingRowColors(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table_view)

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        self.table_view.setModel(model)


class PersonTableController(QtCore.QObject):
    def __init__(
        self,
        columns: list[SchemaColumn],
        view: PersonTableView | None = None,
        parent: QtCore.QObject | None = None,
    ):
        super().__init__(parent=parent)
        self._model = SchemaTableModel(columns)
        self._proxy = PersonFilter(self._model)
        self._view = view or PersonTableView()
        self._view.setModel(self._proxy)

        for col in columns:
            col.filterChanged.connect(self.onFilterChanged)

    def onFilterChanged(self, value: str):
        sender = self.sender()
        if not isinstance(sender, SchemaColumn):
            return
        column_index = sender.columnIndex()
        self._proxy.setFilter(column_index, value)

    def view(self) -> PersonTableView:
        return self._view

    def setRows(self, rows: list[Person]) -> None:
        self._model.setRows(rows)


def main():
    app = QtWidgets.QApplication(sys.argv)

    columns = [
        AttributeColumn("Name", "name"),
        DepartmentColumn(),
        AttributeColumn("Salary", "salary"),
        ActiveColumn(),
    ]

    ctrl = PersonTableController(columns)
    ctrl.setRows(PEOPLE)

    window = QtWidgets.QWidget()
    window.setWindowTitle("SchemaTable Test")
    window.resize(700, 400)

    layout = QtWidgets.QVBoxLayout(window)
    layout.addWidget(ctrl.view())

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
