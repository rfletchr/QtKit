__all__ = ["ImageColumn"]

import typing
from qtpy import QtCore, QtGui, QtWidgets

from qtkit.DataLoader import LoaderBase, LoadResult
from qtkit.SchemaTable.model import SchemaColumn, Handle

KT = typing.TypeVar("KT")
VT = typing.TypeVar("VT")


class ImageColumn(SchemaColumn):
    def __init__(
        self,
        header: str,
        path_attribute: str,
        loader: LoaderBase,
        cache_size: int = 256,
        placeholder: typing.Optional[QtGui.QPixmap] = None,
        error_placeholder: typing.Optional[QtGui.QPixmap] = None,
        thumbnail_size: QtCore.QSize = QtCore.QSize(64, 64),
        parent=None,
    ):
        super().__init__(parent)
        self._path_attribute = path_attribute
        self._header_name = header
        self._loader = loader
        self._cache: BoundedDict[str, typing.Optional[QtGui.QPixmap]] = BoundedDict(
            max_size=cache_size
        )
        self._placeholder = placeholder
        self._error_placeholder = error_placeholder
        self._thumbnail_size = thumbnail_size

    def header(
        self, role: QtCore.Qt.ItemDataRole, index: QtCore.QModelIndex
    ) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._header_name
        return None

    def extractPath(self, item: typing.Any) -> typing.Optional[str]:
        """Override to derive path from item in a non-standard way."""
        if isinstance(item, dict):
            return item.get(self._path_attribute)
        return getattr(item, self._path_attribute, None)

    def getData(
        self,
        item: typing.Any,
        role: QtCore.Qt.ItemDataRole,
        index: QtCore.QModelIndex,
    ) -> typing.Any:
        if role == QtCore.Qt.ItemDataRole.DecorationRole:
            img_path = self.extractPath(item)
            if img_path is None:
                return self._placeholder

            url = QtCore.QUrl(img_path)
            cache_key = url.toString()

            if cache_key in self._cache:
                return self._cache[cache_key]

            self._cache[cache_key] = self._placeholder

            handle = self.model().handle(index)
            result = self._loader.load(url)
            result.setProperty("handle", handle)
            result.finished.connect(self._on_loaded)
            return self._placeholder

        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            return self._thumbnail_size

    def _on_loaded(self) -> None:
        result = typing.cast(LoadResult, self.sender())
        result.deleteLater()

        handle = result.property("handle")
        img_path = result.url().toString()

        if handle is None or img_path is None:
            return

        if result.isCancelled():
            self._cache.pop(img_path, None)
            return

        if result.error() is not None:
            self._cache[img_path] = self._error_placeholder
            self._emit_data_changed(handle)
            return

        if not self.model().isHandleValid(handle):
            self._cache.pop(img_path, None)
            return

        image = QtGui.QImage.fromData(result.data())

        if image.isNull():
            self._cache[img_path] = self._error_placeholder
            self._emit_data_changed(handle)
            return

        scaled = image.scaled(
            self._thumbnail_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self._cache[img_path] = QtGui.QPixmap.fromImage(scaled)
        self._emit_data_changed(handle)

    def _emit_data_changed(self, handle: Handle) -> None:
        if not self.model().isHandleValid(handle):
            return
        index = self.model().index(handle.row, self.columnIndex())
        self.model().dataChanged.emit(
            index, index, [QtCore.Qt.ItemDataRole.DecorationRole]
        )


class BoundedDict(dict, typing.Generic[KT, VT]):
    def __init__(self, *args, max_size: int = 10, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_size = max_size

    def __setitem__(self, key: KT, value: VT) -> None:
        if len(self) >= self.max_size and key not in self:
            del self[next(iter(self))]
        super().__setitem__(key, value)


if __name__ == "__main__":
    import sys
    import faker
    from qtpy.QtWidgets import QApplication, QTableView
    from qtkit.SchemaTable import SchemaTableModel, DictKeyColumn
    from qtkit.DataLoader import RemoteFileLoader

    app = QApplication(sys.argv)
    profile_factory = faker.Faker()

    # use standard qt icons for placeholder and error states
    placeholder = (
        app.style()
        .standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        .pixmap(128, 128)
    )
    error_placeholder = (
        app.style()
        .standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxCritical)
        .pixmap(128, 128)
    )

    image_column = ImageColumn(
        header="Image",
        path_attribute="image",
        loader=RemoteFileLoader(),
        cache_size=100,
        placeholder=placeholder,
        error_placeholder=error_placeholder,
        thumbnail_size=QtCore.QSize(128, 128),
    )

    rows = []
    for i in range(100):
        profile = profile_factory.profile()
        image = "https://picsum.photos/id/{i}/300/300"
        rows.append({"name": profile["name"], "image": image.format(i=i)})

    columns = [
        DictKeyColumn("Name", "name"),
        image_column,
    ]
    model = SchemaTableModel[dict](columns)
    model.setRows(rows)

    view = QTableView()
    view.verticalHeader().setSectionResizeMode(
        QtWidgets.QHeaderView.ResizeMode.ResizeToContents
    )
    view.setModel(model)
    view.show()
    sys.exit(app.exec())
