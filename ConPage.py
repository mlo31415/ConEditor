from __future__ import annotations
from typing import List


class ConFile:
    def __init__(self):
        self._title: str=""
        self._description: str=""
        self._pathname: str=""


class ConPage:
    # an array of tuples: column header, min col width, col type
    Colheaders=["Title", "Description"]
    ColMinWidths=[50, 100]
    ColDataTypes=["str", "str"]

    def __init__(self):
        self._conFileList: List[ConFile]=[]
        self._name=""

    @property
    def NumRows(self) -> int:
        return len(self._conFileList)

    @property
    def Rows(self):
        return self._conFileList


