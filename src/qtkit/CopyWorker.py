__all__ = ["CopyItem", "ProgressUpdate", "CopyWorker", "CopyController"]

import typing
import time
import threading
from qtpy import QtCore


class CopyItem(typing.NamedTuple):
    src_path: str
    dst_path: str
    size: int


class ProgressUpdate(typing.NamedTuple):
    progress: int
    total: int
    time_remaining: float


class CopyWorker(QtCore.QObject):
    progressChanged = QtCore.Signal(ProgressUpdate)
    busyChanged = QtCore.Signal(bool)
    error = QtCore.Signal(Exception)

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._stop_event = threading.Event()
        self._last_progress_update = time.time()
        self._report_interval = 0.5

    def stop(self):
        self._stop_event.set()

    def copy_files(
        self,
        copy_plan: list[CopyItem],
        chunk_size: int = 1 << 20,
        continue_on_error: bool = True,
    ):
        total_size = sum(item.size for item in copy_plan)
        copied_size = 0

        start_time = time.time()
        self._last_progress_update = start_time
        self.busyChanged.emit(True)

        try:
            for item in copy_plan:
                if self._stop_event.is_set():
                    break

                try:
                    with (
                        open(item.src_path, "rb") as src_file,
                        open(item.dst_path, "wb") as dst_file,
                    ):
                        while True:
                            if self._stop_event.is_set():
                                break
                            chunk = src_file.read(chunk_size)
                            if not chunk:
                                break

                            dst_file.write(chunk)
                            copied_size += len(chunk)

                            now = time.time()
                            taken = now - self._last_progress_update
                            if taken >= self._report_interval:
                                self.reportProgress(start_time, copied_size, total_size)
                                self._last_progress_update = now

                except Exception as e:
                    self.error.emit(e)
                    if not continue_on_error:
                        break
        finally:
            self.reportProgress(start_time, copied_size, total_size)
            self.busyChanged.emit(False)

    def _start_copy(
        self,
        copy_plan: list,
        chunk_size: int,
        continue_on_error: bool,
    ) -> None:
        self._stop_event.clear()
        self.copy_files(copy_plan, chunk_size, continue_on_error)

    def reportProgress(self, start_time: float, copied_size: int, total_size: int):
        elapsed_time = time.time() - start_time
        time_remaining = (
            (total_size - copied_size) / (copied_size / elapsed_time)
            if copied_size > 0
            else float("inf")
        )
        self.progressChanged.emit(
            ProgressUpdate(
                progress=copied_size,
                total=total_size,
                time_remaining=time_remaining,
            )
        )


class CopyController(QtCore.QObject):
    """Manages a CopyWorker on a dedicated QThread.

    Signals relay directly from the worker across the thread boundary.
    Call shutdown() for a clean stop — cancels any active copy and joins the thread.
    """

    progressChanged = QtCore.Signal(ProgressUpdate)
    busyChanged = QtCore.Signal(bool)
    error = QtCore.Signal(Exception)

    _copy = QtCore.Signal(object, int, bool)

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._worker = CopyWorker()
        self._thread = QtCore.QThread(self)
        self._worker.moveToThread(self._thread)

        self._worker.progressChanged.connect(self.progressChanged)
        self._worker.busyChanged.connect(self.busyChanged)
        self._worker.error.connect(self.error)
        self._copy.connect(self._worker._start_copy)

        self._thread.start()

    def copy(
        self,
        plan: list[CopyItem],
        chunk_size: int = 1 << 20,
        continue_on_error: bool = True,
    ) -> None:
        self._copy.emit(plan, chunk_size, continue_on_error)

    def cancel(self) -> None:
        self._worker.stop()

    def shutdown(self) -> None:
        self._worker.stop()
        self._thread.quit()
        self._thread.wait()
