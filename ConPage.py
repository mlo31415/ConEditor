from __future__ import annotations
from typing import List, Union
from Grid import GridDataSource

# An individual file to be listed under a convention
class ConFile:
    def __init__(self):
        self._displayTitle: str=""      # The name as shown to the world
        self._description: str=""       # The free-format description
        self._localpathname: str=""          # The local pathname of the file

    @property
    def DisplayTitle(self) -> str:
        return self._displayTitle

    @property
    def Description(self) -> str:
        return self._description

    @property
    def LocalPathname(self) -> str:
        return self._localpathname

    # Get or set a value by name or column number in the grid
    def GetVal(self, name: Union[str, int]) -> Union[str, int]:
        # (Could use return eval("self."+name))
        if name == "File" or name == 0:
            return self._displayTitle
        if name == "Description" or name == 1:
            return self._description
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == "File" or nameOrCol == 0:
            self._displayTitle=val
            return
        if nameOrCol == "Description" or nameOrCol == 1:
            self._description=val
            return
        print("SetVal can't interpret '"+str(nameOrCol)+"'")



class ConPage(GridDataSource):
    # an array of tuples: column header, min col width, col type
    _colheaders=["File", "Description"]
    _colminwidths=[50, 200]
    _coldatatypes=["str", "str"]
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

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str, FanzineDateRange]) -> None:
        self._conFileList[irow].SetVal(icol, val)

    @property
    def ColDataTypes(self) -> List[str]:
        return self._coldatatypes

    @property
    def ColMinWidths(self) -> List[int]:
        return self._colminwidths

    @property
    def NumRows(self) -> int:
        return len(self._conFileList)

    def GetData(self, iRow: int, iCol: int) -> str:
        r=self.Rows[iRow]
        return r.GetVal(self.ColHeaders[iCol])

