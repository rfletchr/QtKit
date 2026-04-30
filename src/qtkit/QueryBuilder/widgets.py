from __future__ import annotations
import datetime
import typing
from qtpy import QtCore, QtWidgets, QtGui
from .api import Field


class CustomLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        palette = self.palette()
        palette.setColor(
            QtGui.QPalette.ColorRole.Base,
            palette.color(QtGui.QPalette.ColorRole.Base).lighter(125),
        )
        self.setPalette(palette)
        self.setPlaceholderText("...")


def make_value_editor(field: Field, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    if field.value_model is not None:
        combo = QtWidgets.QComboBox(parent)
        combo.setModel(field.value_model)
        combo.setEditable(field.allow_custom_values)

        return combo
    if field.type is bool:
        combo = QtWidgets.QComboBox(parent)
        combo.addItems(["True", "False"])
        return combo
    if field.type is datetime.datetime:
        return QtWidgets.QDateTimeEdit(parent)
    if field.type is datetime.date:
        return QtWidgets.QDateEdit(parent)
    if field.type is int:
        return QtWidgets.QSpinBox(parent)
    if field.type is float:
        return QtWidgets.QDoubleSpinBox(parent)
    if field.type is str:
        return CustomLineEdit(parent)
    return CustomLineEdit(parent)


def _connect_value_changed(editor: QtWidgets.QWidget, slot: typing.Callable) -> None:
    if isinstance(editor, QtWidgets.QLineEdit):
        editor.textChanged.connect(slot)
    elif isinstance(editor, QtWidgets.QComboBox):
        editor.currentIndexChanged.connect(slot)
    elif isinstance(editor, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
        editor.valueChanged.connect(slot)
    elif isinstance(editor, (QtWidgets.QDateTimeEdit, QtWidgets.QDateEdit)):
        editor.dateTimeChanged.connect(slot)


def _read_value(editor: QtWidgets.QWidget) -> str:
    if isinstance(editor, QtWidgets.QLineEdit):
        return editor.text()
    if isinstance(editor, QtWidgets.QComboBox):
        return editor.currentText()
    if isinstance(editor, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
        return str(editor.value())
    if isinstance(editor, QtWidgets.QDateTimeEdit):
        return editor.dateTime().toString(QtCore.Qt.DateFormat.ISODate)
    if isinstance(editor, QtWidgets.QDateEdit):
        return editor.date().toString(QtCore.Qt.DateFormat.ISODate)
    return ""


def _write_value(editor: QtWidgets.QWidget, value: str) -> None:
    if isinstance(editor, QtWidgets.QLineEdit):
        editor.setText(value)
    elif isinstance(editor, QtWidgets.QComboBox):
        idx = editor.findText(value)
        if idx >= 0:
            editor.setCurrentIndex(idx)
        elif editor.isEditable():
            editor.setEditText(value)
    elif isinstance(editor, QtWidgets.QSpinBox):
        try:
            editor.setValue(int(value))
        except (ValueError, TypeError):
            pass
    elif isinstance(editor, QtWidgets.QDoubleSpinBox):
        try:
            editor.setValue(float(value))
        except (ValueError, TypeError):
            pass
    elif isinstance(editor, QtWidgets.QDateTimeEdit):
        dt = QtCore.QDateTime.fromString(value, QtCore.Qt.DateFormat.ISODate)
        if dt.isValid():
            editor.setDateTime(dt)
    elif isinstance(editor, QtWidgets.QDateEdit):
        date = QtCore.QDate.fromString(value, QtCore.Qt.DateFormat.ISODate)
        if date.isValid():
            editor.setDate(date)


class ComparisonWidget(QtWidgets.QWidget):
    changed = QtCore.Signal()
    removeRequested = QtCore.Signal()

    def __init__(
        self,
        fields: list[Field],
        parent: typing.Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent=parent)

        self._value_editor: typing.Optional[QtWidgets.QWidget] = None

        self.field_combo = QtWidgets.QComboBox()
        for field in fields:
            self.field_combo.addItem(field.name, userData=field)

        self.operator_combo = QtWidgets.QComboBox()

        self._value_container = QtWidgets.QWidget()
        self._value_layout = QtWidgets.QHBoxLayout(self._value_container)
        self._value_layout.setContentsMargins(0, 0, 0, 0)

        self.remove_button = QtWidgets.QPushButton("✕")
        self.remove_button.setFixedWidth(24)

        row_layout = QtWidgets.QHBoxLayout(self)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self.field_combo)
        row_layout.addWidget(self.operator_combo)
        row_layout.addWidget(self._value_container, 1)
        row_layout.addWidget(self.remove_button)

        self.field_combo.currentIndexChanged.connect(self._onFieldChanged)
        self.operator_combo.currentIndexChanged.connect(self.changed)
        self.remove_button.clicked.connect(self.removeRequested)

        self._onFieldChanged(0)

    def _onFieldChanged(self, index: int) -> None:
        field: typing.Optional[Field] = self.field_combo.itemData(index)
        if field is None:
            return

        self.operator_combo.blockSignals(True)
        self.operator_combo.clear()
        self.operator_combo.addItems(field.operators)
        if field.default_operator in field.operators:
            self.operator_combo.setCurrentIndex(
                field.operators.index(field.default_operator)
            )
        self.operator_combo.blockSignals(False)

        if self._value_editor is not None:
            self._value_layout.removeWidget(self._value_editor)
            self._value_editor.deleteLater()

        editor = make_value_editor(field, self._value_container)
        _connect_value_changed(editor, self.changed)
        self._value_layout.addWidget(editor)
        self._value_editor = editor

        self.changed.emit()

    def currentField(self) -> typing.Optional[Field]:
        return self.field_combo.currentData()

    def currentOperator(self) -> str:
        return self.operator_combo.currentText()

    def currentValue(self) -> str:
        return _read_value(self._value_editor) if self._value_editor is not None else ""

    def setField(self, field: Field) -> None:
        for i in range(self.field_combo.count()):
            if self.field_combo.itemData(i) is field:
                self.field_combo.setCurrentIndex(i)
                return

    def setOperator(self, operator: str) -> None:
        idx = self.operator_combo.findText(operator)
        if idx >= 0:
            self.operator_combo.setCurrentIndex(idx)

    def setValue(self, value: str) -> None:
        if self._value_editor is not None:
            _write_value(self._value_editor, value)


class GroupWidget(QtWidgets.QWidget):
    operatorChanged = QtCore.Signal(str)
    addComparisonRequested = QtCore.Signal()
    addGroupRequested = QtCore.Signal()
    removeRequested = QtCore.Signal()

    def __init__(
        self,
        op: str = "AND",
        is_root: bool = False,
        parent: typing.Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent=parent)

        self.op_button = QtWidgets.QPushButton(op)
        self.op_button.setFixedWidth(48)
        self.add_condition_button = QtWidgets.QPushButton("+ Condition")
        self.add_group_button = QtWidgets.QPushButton("+ Group")
        self.remove_button = QtWidgets.QPushButton("✕")
        self.remove_button.setFixedWidth(24)
        self.remove_button.setEnabled(not is_root)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.op_button)
        layout.addStretch()
        layout.addWidget(self.add_condition_button)
        layout.addWidget(self.add_group_button)
        layout.addWidget(self.remove_button)

        self.op_button.clicked.connect(self._onToggleOp)
        self.add_condition_button.clicked.connect(self.addComparisonRequested)
        self.add_group_button.clicked.connect(self.addGroupRequested)
        self.remove_button.clicked.connect(self.removeRequested)

    def _onToggleOp(self) -> None:
        new_op = "OR" if self.op_button.text() == "AND" else "AND"
        self.op_button.setText(new_op)
        self.operatorChanged.emit(new_op)

    def setOperator(self, op: str) -> None:
        self.op_button.setText(op)
