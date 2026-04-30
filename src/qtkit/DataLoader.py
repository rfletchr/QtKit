__all__ = ["LoadResult", "LoadQueue", "LocalFileLoader", "RemoteFileLoader"]

import collections
import threading
import typing
from qtpy import QtCore

import requests


class CancelledError(Exception):
    """Raised when a load operation is cancelled."""


class LoadResult(QtCore.QObject):
    finished = QtCore.Signal()

    def __init__(
        self,
        url: QtCore.QUrl,
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        self._url = url
        self._data: typing.Optional[bytes] = None
        self._error: typing.Optional[Exception] = None
        self._cancelled: bool = False

    def url(self) -> QtCore.QUrl:
        return self._url

    def data(self) -> bytes:
        if self._cancelled:
            raise CancelledError("Load was cancelled")
        if self._error is not None:
            raise self._error
        assert self._data is not None
        return self._data

    def error(self) -> typing.Optional[Exception]:
        return self._error

    def isCancelled(self) -> bool:
        return self._cancelled

    def _deliver(
        self,
        data: typing.Optional[bytes],
        error: typing.Optional[Exception],
    ) -> None:
        self._data = data
        self._error = error
        self.finished.emit()

    def _cancel(self) -> None:
        self._cancelled = True
        self.finished.emit()


class LoadQueue:
    """Thread-safe bounded deque. Evicts oldest entry (cancelling its result) when full."""

    def __init__(self, maxlen: typing.Optional[int] = None):
        self._deque: collections.deque = collections.deque(maxlen=maxlen)
        self._cond = threading.Condition()

    def push(self, result: LoadResult) -> None:
        evicted: typing.Optional[LoadResult] = None

        with self._cond:
            if (
                self._deque.maxlen is not None
                and len(self._deque) == self._deque.maxlen
            ):
                evicted = self._deque[0]
            self._deque.append(result)
            self._cond.notify()

        if evicted is not None:
            QtCore.QTimer.singleShot(0, evicted, evicted._cancel)

    def pop(self) -> LoadResult:
        with self._cond:
            while not self._deque:
                self._cond.wait()
            return self._deque.popleft()


class LoaderBase(QtCore.QObject):
    def __init__(
        self,
        num_threads: int = 4,
        max_queue_size: typing.Optional[int] = None,
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        self._queue = LoadQueue(maxlen=max_queue_size)
        self._threads = [
            threading.Thread(target=self._worker, daemon=True)
            for _ in range(num_threads)
        ]
        for t in self._threads:
            t.start()

    def load(self, url: QtCore.QUrl) -> LoadResult:
        result = LoadResult(url, self)
        self._queue.push(result)
        return result

    def _worker(self) -> None:
        while True:
            result = self._queue.pop()
            try:
                data = self._process(result.url())
                QtCore.QTimer.singleShot(
                    0, result, lambda r=result, d=data: r._deliver(d, None)
                )
            except Exception as exc:
                QtCore.QTimer.singleShot(
                    0, result, lambda r=result, e=exc: r._deliver(None, e)
                )

    def _process(self, url: QtCore.QUrl) -> bytes:
        raise NotImplementedError


class LocalFileLoader(LoaderBase):
    def _process(self, url: QtCore.QUrl) -> bytes:
        with open(url.toLocalFile(), "rb") as f:
            return f.read()


class RemoteFileLoader(LoaderBase):
    def __init__(
        self,
        session_factory: typing.Callable[[], requests.Session] | None = None,
        num_threads: int = 4,
        max_queue_size: typing.Optional[int] = None,
        parent: typing.Optional[QtCore.QObject] = None,
    ):
        super().__init__(
            num_threads=num_threads, max_queue_size=max_queue_size, parent=parent
        )
        self._session_factory = session_factory or requests.Session
        self._local = threading.local()

    def _session(self) -> "requests.Session":
        if not hasattr(self._local, "session"):
            self._local.session = self._session_factory()
        return self._local.session

    def _process(self, url: QtCore.QUrl) -> bytes:
        response = self._session().get(url.toString())
        response.raise_for_status()
        return response.content
