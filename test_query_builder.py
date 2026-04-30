import sys
import datetime
from qtpy import QtWidgets, QtCore, QtGui
from qtkit.QueryBuilder import Field, QueryBuilderController


def make_fields() -> list[Field]:
    status_model = QtGui.QStandardItemModel()
    for value in ("active", "inactive", "pending"):
        status_model.appendRow(QtGui.QStandardItem(value))

    return [
        Field(
            name="name",
            type=str,
            operators=["contains", "equals", "starts with", "ends with"],
            value_model=None,
            allow_custom_values=False,
            default_operator="contains",
        ),
        Field(
            name="age",
            type=int,
            operators=["=", "!=", ">", "<", ">=", "<="],
            value_model=None,
            allow_custom_values=False,
            default_operator="=",
        ),
        Field(
            name="status",
            type=str,
            operators=["=", "!="],
            value_model=status_model,
            allow_custom_values=False,
            default_operator="=",
        ),
        Field(
            name="score",
            type=float,
            operators=["=", ">", "<", ">=", "<="],
            value_model=None,
            allow_custom_values=False,
            default_operator=">=",
        ),
        Field(
            name="created",
            type=datetime.date,
            operators=["=", ">", "<", ">=", "<="],
            value_model=None,
            allow_custom_values=False,
            default_operator=">=",
        ),
    ]


def main():
    app = QtWidgets.QApplication(sys.argv)

    fields = make_fields()
    ctrl = QueryBuilderController(fields)

    output = QtWidgets.QTextEdit()
    output.setReadOnly(True)
    output.setMaximumHeight(120)

    def on_query_changed():
        result = ctrl.build()
        output.setPlainText(repr(result))

    ctrl.queryChanged.connect(on_query_changed)

    window = QtWidgets.QWidget()
    window.setWindowTitle("QueryBuilder Test")
    window.resize(700, 500)

    layout = QtWidgets.QVBoxLayout(window)
    layout.addWidget(ctrl.view(), 1)
    layout.addWidget(QtWidgets.QLabel("AST output:"))
    layout.addWidget(output)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
