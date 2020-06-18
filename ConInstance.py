from __future__ import annotations
from typing import List, Union
from DataGrid import GridDataSource
import json

# An individual file to be listed under a convention
class ConFile:
    def __init__(self):
        self._displayTitle: str=""      # The name as shown to the world on the website
        self._notes: str=""             # The free-format description
        self._localfilename: str=""     # The filename of the source file
        self._localpathname: str="."    # The local pathname of the source file (path+filename)
        self._sitefilename: str=""      # The name to be used for this file on the website
        self._size: int=0               # The file's size in bytes

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 5,
           "_displayTitle": self._displayTitle,
           "_notes": self._notes,
           "_localpathname": self._localpathname,
           "_filename": self._localfilename,
           "_sitefilename": self._sitefilename,
           "_size": self._size}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConFile:
        d=json.loads(val)
        self._displayTitle=d["_displayTitle"]
        self._notes=d["_notes"]
        self._localpathname=d["_localpathname"]
        self._localfilename=d["_filename"]
        self._size=d["_size"]
        if d["ver"] > 4:
            self._sitefilename=d["_sitefilename"]
        else:
            self._sitefilename=self._localfilename
        return self

    @property
    def DisplayName(self) -> str:
        return self._displayTitle
    @DisplayName.setter
    def DisplayName(self, val: str):
        self._displayTitle=val

    @property
    def Notes(self) -> str:
        return self._notes
    @Notes.setter
    def Notes(self, val: str):
        self._notes=val

    @property
    def LocalPathname(self) -> str:
        return self._localpathname
    @LocalPathname.setter
    def LocalPathname(self, val: str):
        self._localpathname=val

    @property
    def SiteFilename(self) -> str:
        return self._sitefilename
    @SiteFilename.setter
    def SiteFilename(self, val: str):
        self._sitefilename=val

    @property
    def SourceFilename(self) -> str:
        return self._localfilename
    @SourceFilename.setter
    def SourceFilename(self, val: str):
        self._localfilename=val

    @property
    def Size(self) -> int:
        return self._size
    @Size.setter
    def Size(self, val: int):
        self._size=val


    # Get or set a value by name or column number in the grid
    def GetVal(self, name: Union[str, int]) -> Union[str, int]:
        # (Could use return eval("self."+name))
        if name == "Source File Name" or name == 0:
            return self.SourceFilename
        if name == "Site Name" or name == 1:
            return self.SiteFilename
        if name == "Display Name" or name == 2:
            return self.DisplayName
        if name == "Notes" or name == 3:
            return self.Notes
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == "Source File Name" or nameOrCol == 0:
            self.SourceFilename=val#
            return
        if nameOrCol == "Site Name" or nameOrCol == 1:
            self.SiteFilename=val
            return
        if nameOrCol == "Display Name" or nameOrCol == 2:
            self.DisplayName=val
            return
        if nameOrCol == "Notes" or nameOrCol == 3:
            self.Notes=val
            return
        print("SetVal can't interpret '"+str(nameOrCol)+"'")


#####################################################################################################
#####################################################################################################

class ConInstancePage(GridDataSource):
    # an array of tuples: column header, min col width, col type
    _colheaders=["Source File Name", "Site Name", "Display Name", "Notes"]
    _colminwidths=[100, 75, 75, 150]
    _coldatatypes=["str", "str", "str", "str"]
    _coleditable=["no", "yes", "yes", "yes"]        # Choices are: yes, no, maybe
    _element=ConFile

    def __init__(self):
        self._conFileList: List[ConFile]=[]
        self._name=""
        self._updated=False

    # Serialize and deserialize
    def ToJson(self) -> str:
        dl=[]
        for con in self._conFileList:
            dl.append(con.ToJson())
        d={"ver": 2,
           "_colheaders": self._colheaders,
           "_colminwidths": self._colminwidths,
           "_coldatatypes": self._coldatatypes,
           "_coleditable": self._coleditable,
           "_name": self._name,
           "_conFileList": dl}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConInstancePage:
        d=json.loads(val)
        if d["ver"] >= 1:
            #self._colheaders=d["_colheaders"]
            #self._colminwidths=d["_colminwidths"]
            #self._coldatatypes=d["_coldatatypes"]
            self._name=d["_name"]
            cfld=d["_conFileList"]
            self._conFileList=[]
            for c in cfld:
                self._conFileList.append(ConFile().FromJson(c))

        # self._coleditable=["yes"]*len(self._colheaders)
        # if "_coleditable" in d.keys():
        #     self._coleditable=d["_coleditable"]

        # if len(self._colheaders) == 2:  # Old-style had just two: "File" and "Notes".  We need to rename "File" and insert "Display Name" #TODO: Remove when no longer needed
        #     self._colheaders=["File Name", "Display Name", "Notes"]
        #     self._colminwidths=[50, 50, 200]
        #     self._coldatatypes=["str", "str", "str"]

        #self._colheaders=["Notes" if ch == "Description" else ch for ch in self._colheaders]    # Change Description column to Notes in old files #TODO: Remove when no longer needed
        self._updated=False
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
    def ColEditable(self) -> List[int]:
        return self._coleditable

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

    @property
    def Updated(self) -> bool:
        return self._updated
    @Updated.setter
    def Updated(self, val: bool) -> None:
        self._updated=val


