# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class Severity(Enum):
    """Severity attribute for `ReportItem`. Corresponding values are Emoji-characters."""
    ERROR = "\u274C"
    WARNING = "\u26A0"
    INFO = "\u2139"
    SUMMARY = "SUMMARY"


@dataclass(frozen=True)  # 'frozen' makes it hashable
class ReportItem:
    """A structure for reporting outcomes of complex actions."""
    severity: Severity
    message: str
    id: str = ""
    type: str = ""

    def is_error(self) -> bool:
        """
        Short-hand to test ``severity == ERROR``.
        """
        return self.severity == Severity.ERROR

    def is_warning(self) -> bool:
        """
        Short-hand to test ``severity == WARNING``.
        """
        return self.severity == Severity.WARNING

    def is_info(self) -> bool:
        """
        Short-hand to test ``severity == INFO``.
        """
        return self.severity == Severity.INFO

    def is_summary(self) -> bool:
        """
        Short-hand to test ``severity == SUMMARY``.
        """
        return self.severity == Severity.SUMMARY

    def as_warning(self) -> "ReportItem":
        """
        Convert the ReportItem into a warning.
        """
        return ReportItem(Severity.WARNING, message=self.message, id=self.id, type=self.type)

    def print(self, single_line=False) -> str:
        """
        Format the ReportItem for output.
        """
        msg = self.message
        if single_line:
            msg = ' '.join(s.strip() for s in msg.splitlines())
        return f"{self.severity.name}: {self.type} {self.id}: {msg}"


def removed_duplicates(ris: List[ReportItem]) -> List[ReportItem]:
    """
    Create a shallow copy of a list of ReportItems, and remove duplicate items.
    """
    deja = set()
    res = []
    for ri in ris:
        if ri not in deja:
            deja.add(ri)
            res.append(ri)
    return res
