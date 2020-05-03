from __future__ import annotations
from typing import List
from Grid import GridDataSource


class ConFile:
    def __init__(self):
        self._title: str=""
        self._description: str=""
        self._pathname: str=""


class ConPage(GridDataSource):
    # an array of tuples: column header, min col width, col type
    _colheaders=["Title", "Description"]
    _colminwidths=[50, 100]
    _coltypes=["str", "str"]
    _element=ConFile

    def __init__(self):
        self._conFileList: List[ConFile]=[]
        self._name=""


    # Inherited from GridDataSource
    @property
    def ColHeaders(self) -> List[str]:
        return self._colheaders

    @property
    def Rows(self) -> List:
        return self._conFileList

    @Rows.setter
    def Rows(self, rows: List) -> None:
        self._conFileList=rows

    @property
    def ColDataTypes(self) -> List[str]:
        return self._coltypes

    @property
    def ColMinWidths(self) -> List[int]:
        return self._colminwidths

    @property
    def NumRows(self) -> int:
        return len(self._conFileList)

    def Data(self, iRow: int, iCol: int) -> str:
        return "Data"




