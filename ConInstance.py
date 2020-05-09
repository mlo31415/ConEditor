from __future__ import annotations
from typing import List, Union
from Grid import GridDataSource
import json

# An individual file to be listed under a convention
class ConFile:
    def __init__(self):
        self._displayTitle: str=""      # The name as shown to the world
        self._description: str=""       # The free-format description
        self._localpathname: str="."     # The local pathname of the file

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"version": 1,
           "_displayTitle": self._displayTitle,
           "_description": self._description,
           "_localpathname": self._localpathname}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConFile:
        d=json.loads(val)
        if d["version"] == 1:
            self._displayTitle=d["_displayTitle"]
            self._description=d["_description"]
            self._localpathname=d["_localpathname"]
        return self

    @property
    def DisplayTitle(self) -> str:
        return self._displayTitle
    @DisplayTitle.setter
    def DisplayTitle(self, val: str):
        self._displayTitle=val

    @property
    def Description(self) -> str:
        return self._description
    @Description.setter
    def Description(self, val: str):
        self._description=val

    @property
    def LocalPathname(self) -> str:
        return self._localpathname
    @LocalPathname.setter
    def LocalPathname(self, val: str):
        self._localpathname=val


    # Get or set a value by name or column number in the grid
    def GetVal(self, name: Union[str, int]) -> Union[str, int]:
        # (Could use return eval("self."+name))
        if name == "File" or name == 0:
            return self.DisplayTitle
        if name == "Description" or name == 1:
            return self.Description
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == "File" or nameOrCol == 0:
            self.DisplayTitle=val
            return
        if nameOrCol == "Description" or nameOrCol == 1:
            self.Description=val
            return
        print("SetVal can't interpret '"+str(nameOrCol)+"'")



class ConInstancePage(GridDataSource):
    # an array of tuples: column header, min col width, col type
    _colheaders=["File", "Description"]
    _colminwidths=[50, 200]
    _coldatatypes=["str", "str"]
    _element=ConFile

    def __init__(self):
        self._conFileList: List[ConFile]=[]
        self._name=""

    # Serialize and deserialize
    def ToJson(self) -> str:
        dl=[]
        for con in self._conFileList:
            dl.append(con.ToJson())
        d={"version": 1,
           "_colheaders": self._colheaders,
           "_colminwidths": self._colminwidths,
           "_coldatatypes": self._coldatatypes,
           "_name": self._name,
           "numConFiles": len(self._conFileList),
           "_conFileList": dl}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConInstancePage:
        d=json.loads(val)
        if d["version"] == 1:
            self._colheaders=d["_colheaders"]
            self._colminwidths=d["_colminwidths"]
            self._coldatatypes=d["_coldatatypes"]
            self._name=d["_name"]
            numConFiles=d["numConFiles"]
            cfld=d["_conFileList"]
            self._conFileList=[]
            for c in cfld:
                self._conFileList.append(ConFile().FromJson(c))
        return self


    # Inherited from GridDataSource
    @property
    def ColHeaders(self) -> List[str]:
        return self._colheaders

    @property
    def ColDataTypes(self) -> List[str]:
        return self._coldatatypes

    @property
    def ColMinWidths(self) -> List[int]:
        return self._colminwidths

    @property
    def Rows(self) -> List:
        return self._conFileList

    @Rows.setter
    def Rows(self, rows: List) -> None:
        self._conFileList=rows

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str]) -> None:
        self._conFileList[irow].SetVal(icol, val)

    @property
    def Name(self) -> str:
        return self._name

    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    @property
    def NumRows(self) -> int:
        return len(self._conFileList)

    def GetData(self, iRow: int, iCol: int) -> str:
        r=self.Rows[iRow]
        return r.GetVal(self.ColHeaders[iCol])


