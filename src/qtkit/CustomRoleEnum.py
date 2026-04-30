from __future__ import annotations
import enum

from qtpy import QtCore


class QtCustomRoleEnum(enum.IntEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):  # noqa: ARG004
        return QtCore.Qt.ItemDataRole.UserRole + count + 1
