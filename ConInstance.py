from __future__ import annotations
from typing import Union, Optional

from HelpersPackage import Int, RemoveAccents

from WxDataGrid import GridDataSource, Color, GridDataElement
import json
import os

# An individual file to be listed under a convention
# This is a single row
class ConFile(GridDataElement):
    def __init__(self):
        self._displayTitle: str=""      # The name as shown to the world on the website
        self._notes: str=""             # The free-format description
        self._localfilename: str=""     # The filename of the source file
        self._localpathname: str="."    # The local pathname of the source file (path+filename)
        self._sitefilename: str=""      # The name to be used for this file on the website
        self._size: int=0               # The file's size in bytes
        self._isText: bool=False        # Is this a piece of text rather than a convention?
        self._isLink: bool=False        # Is this a link?
        self._URL: str=""               # The URL to be used for a link. (This is ignored if _isLink == False.) It will be displayed using displayTitle as the link text.
        self._pages: Optional[int]=None # Page count

    def __str__(self):
        s=""
        if len(self.SourceFilename) > 0:
            s+="Source="+self.SourceFilename+"; "
        if len(self.SiteFilename) > 0:
            s+="Sitename="+self.SiteFilename+"; "
        if len(self.DisplayTitle) > 0:
            s+="Display="+self.DisplayTitle+"; "
        if len(self.Notes) > 0:
            s+="Notes="+self.Notes+"; "
        if len(self.URL) > 0:
            s+="URL="+self.URL+"; "
        if self.Size > 0:
            s+="Size="+str(self.Size)+"; "
        if self.Pages is not None and self.Pages > 0:
            s+="Pages="+str(self.Pages)+"; "
        if self.IsText:
            s+="IsText; "
        if self.IsLink:
            s+="IsLink; "

        return s

    # Make a deep copy of a ConFile
    def Copy(self) -> ConFile:
        cf=ConFile()
        cf._displayTitle=self._displayTitle
        cf._notes=self._notes
        cf._localfilename=self._localfilename
        cf._localpathname=self._localpathname
        cf._sitefilename=self._sitefilename
        cf._size=self._size
        cf._isText=self._isText
        cf._isLink=self._isLink
        cf._URL=self._URL
        cf._pages=self._pages
        return cf

    def Signature(self) -> int:
        tot=hash(self._displayTitle.strip()+self._notes.strip()+self._localfilename.strip()+self._localpathname.strip()+self._sitefilename.strip()+self._URL.strip())
        return tot+self._size+hash(self._isText)+(self._pages if self._pages is not None else 0)

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 9,
           "_displayTitle": self._displayTitle,
           "_notes": self._notes,
           "_localpathname": self._localpathname,
           "_filename": self._localfilename,
           "_sitefilename": self._sitefilename,
           "_isText": self._isText,
           "_isLink": self._isLink,
           "_URL": self._URL,
           "_pages": self._pages,
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
        if d["ver"] <= 4 or self._sitefilename.strip() == "":
            self._sitefilename=self._displayTitle
        if d["ver"] > 5:
            self._isText=d["_isText"]
        if d["ver"] > 6:
            self._pages=d["_pages"]
        if d["ver"] > 7:
            self._isLink=d["_isLink"]
        if d["ver"] > 8:
            self._URL=d["_URL"]
        return self

    @property
    def DisplayTitle(self) -> str:
        return self._displayTitle
    @DisplayTitle.setter
    def DisplayTitle(self, val: str) -> None:
        self._displayTitle=val

    @property
    def Notes(self) -> str:
        return self._notes
    @Notes.setter
    def Notes(self, val: str) -> None:
        self._notes=val

    @property
    def SourcePathname(self) -> str:
        return self._localpathname
    @SourcePathname.setter
    def SourcePathname(self, val: str) -> None:
        self._localpathname=val
        self._localfilename=os.path.basename(val)


    @property
    def SourceFilename(self) -> str:
        return self._localfilename
    @SourceFilename.setter
    def SourceFilename(self, val: str) -> None:
        self._localfilename=val
        self._localpathname="invalidated"

    @property
    def SiteFilename(self) -> str:
        return self._sitefilename
    @SiteFilename.setter
    def SiteFilename(self, val: str) -> None:
        self._sitefilename=RemoveAccents(val)


    @property
    def Size(self) -> int:
        return self._size
    @Size.setter
    def Size(self, val: int) -> None:
        self._size=val

    @property
    def Pages(self) -> Optional[int]:
        return self._pages
    @Pages.setter
    def Pages(self, val: Union[int, str, None]) -> None:
        if type(val) is str:
            val=Int(val)
        self._pages=val

    @property
    def IsText(self) -> bool:
        return self._isText
    @IsText.setter
    def IsText(self, val: bool) -> None:
        self._isText=val


    @property
    def IsLink(self) -> bool:
        return self._isLink
    @IsLink.setter
    def IsLink(self, val: bool) -> None:
        self._isLink=val

    @property
    def URL(self) -> str:
        return self._URL
    @URL.setter
    def URL(self, val: str) -> None:
        self._URL=val

    # Get or set a value by name or column number in the grid
    def GetVal(self, name: Union[str, int]) -> Union[str, int]:
        # (Could use return eval("self."+name))
        if name == 0:
            return self.SourceFilename
        if name == 1:
            return self.SiteFilename
        if name == 2:
            return self.DisplayTitle
        if name == 3:
            return self.Pages
        if name == 4:
            return self.Notes
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == 0:
            self.SourceFilename=val
            return
        if nameOrCol == 1:
            self.SiteFilename=val
            return
        if nameOrCol == 2:
            self.DisplayTitle=val
            return
        if nameOrCol == 3:
            self.Pages=val
            return
        if nameOrCol == 4:
            self.Notes=val
            return
        print("SetVal can't interpret '"+str(nameOrCol)+"'")



#####################################################################################################
#####################################################################################################

class ConInstancePage(GridDataSource):
    # an array of tuples: column header, min col width, col type
    _colheaders=["Source File Name", "Site Name", "Display Name", "Pages", "Notes"]     # "Display Name" is special: change carefully
    _colminwidths=[100, 75, 75, 50, 150]
    _coldatatypes=["str", "str", "str", "int", "str"]
    _coleditable=["maybe", "yes", "yes", "maybe", "yes"]        # Choices are: yes, no, maybe
    _element=ConFile

    def __init__(self):
        GridDataSource.__init__(self)
        self._conFileList: list[ConFile]=[]
        self._name: str=""
        self._specialTextColor: Optional[Color, bool]=True

    # Serialize and deserialize
    def ToJson(self) -> str:
        dl=[]
        for con in self._conFileList:
            dl.append(con.ToJson())
        d={"ver": 3,
           "_name": self._name,
           "_conFileList": dl}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConInstancePage:
        d=json.loads(val)
        if d["ver"] >= 1:
            self._name=d["_name"]
            cfld=d["_conFileList"]
            self._conFileList=[]
            for c in cfld:
                self._conFileList.append(ConFile().FromJson(c))

        return self


    # Inherited from GridDataSource
    @property
    def ColHeaders(self) -> list[str]:
        return self._colheaders

    @property
    def ColDataTypes(self) -> list[str]:
        return self._coldatatypes

    @property
    def ColMinWidths(self) -> list[int]:
        return self._colminwidths

    @property
    def ColEditable(self) -> list[str]:
        return self._coleditable

    @property
    def Rows(self) -> list:
        return self._conFileList

    @Rows.setter
    def Rows(self, rows: list) -> None:
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
        return self.Rows[iRow].GetVal(iCol)

    @property
    def SpecialTextColor(self) -> Optional[Color]:
        return self._specialTextColor
    @SpecialTextColor.setter
    def SpecialTextColor(self, val: Optional[Color]) -> None:
        self._specialTextColor=val

