import concurrent.futures
from qtpy import QtCore


class FutureWatcher(QtCore.QObject):
    finished = QtCore.Signal(concurrent.futures.Future)  # type: ignore

    @classmethod
    def submit(cls, executor: concurrent.futures.Executor, fn, *args, **kwargs):
        """
        Convenience method to submit a function to an executor and watch the resulting future.

        Example usage:
        ```python
        executor = concurrent.futures.ThreadPoolExecutor()
        watcher = FutureWatcher.submit(executor, some_function, arg1, arg2)
        watcher.finished.connect(lambda f: print(f.result()))
        ```
        """
        future = executor.submit(fn, *args, **kwargs)
        return cls(future)

    def __init__(
        self, future: concurrent.futures.Future, auto_delete=True, parent=None
    ):
        super().__init__(parent)
        self._future = future
        self._auto_delete = auto_delete
        future.add_done_callback(self._on_done)

    def _on_done(self, _):
        # add_done_callback fires synchronously if the future is already done, emitting
        # before the caller can connect slots. Timer defers to the next event loop tick.
        # This ensures that there is an opportunity to connect slots before firing the signal.
        # This is a highly unlikely scenario, but it would be a nightmare to triage so we take the safe route.
        QtCore.QTimer.singleShot(0, self, self._emit)

    @QtCore.Slot()
    def _emit(self):
        self.finished.emit(self._future)
        if self._auto_delete:
            self.deleteLater()
