from __future__ import annotations
from typing import Union, Optional

from HelpersPackage import Int, RemoveAccents

from WxDataGrid import GridDataSource, Color, GridDataRowClass, ColDefinition
import json
import os

# An individual file to be listed under a convention
# This is a single row
class ConFile(GridDataRowClass):
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

    def __str__(self):      # ConFile(GridDataRowClass)
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
    def Copy(self) -> ConFile:      # ConFile(GridDataRowClass)
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

    def Signature(self) -> int:      # ConFile(GridDataRowClass)
        tot=hash(self._displayTitle.strip()+self._notes.strip()+self._localfilename.strip()+self._localpathname.strip()+self._sitefilename.strip()+self._URL.strip())
        return tot+self._size+hash(self._isText)+(self._pages if self._pages is not None else 0)

    # Serialize and deserialize
    def ToJson(self) -> str:      # ConFile(GridDataRowClass)
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

    def FromJson(self, val: str) -> ConFile:      # ConFile(GridDataRowClass)
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
    def DisplayTitle(self) -> str:      # ConFile(GridDataRowClass)
        return self._displayTitle
    @DisplayTitle.setter
    def DisplayTitle(self, val: str) -> None:
        self._displayTitle=val

    @property
    def Notes(self) -> str:      # ConFile(GridDataRowClass)
        return self._notes
    @Notes.setter
    def Notes(self, val: str) -> None:
        self._notes=val

    @property
    def SourcePathname(self) -> str:      # ConFile(GridDataRowClass)
        return self._localpathname
    @SourcePathname.setter
    def SourcePathname(self, val: str) -> None:
        self._localpathname=val
        self._localfilename=os.path.basename(val)


    @property
    def SourceFilename(self) -> str:      # ConFile(GridDataRowClass)
        return self._localfilename
    @SourceFilename.setter
    def SourceFilename(self, val: str) -> None:
        self._localfilename=val
        self._localpathname="invalidated"

    @property
    def SiteFilename(self) -> str:      # ConFile(GridDataRowClass)
        return self._sitefilename
    @SiteFilename.setter
    def SiteFilename(self, val: str) -> None:
        self._sitefilename=RemoveAccents(val)


    @property
    def Size(self) -> int:      # ConFile(GridDataRowClass)
        return self._size
    @Size.setter
    def Size(self, val: int) -> None:
        self._size=val

    @property
    def Pages(self) -> Optional[int]:      # ConFile(GridDataRowClass)
        return self._pages
    @Pages.setter
    def Pages(self, val: Union[int, str, None]) -> None:
        if type(val) is str:
            val=Int(val)
        self._pages=val

    @property
    def IsText(self) -> bool:      # ConFile(GridDataRowClass)
        return self._isText
    @IsText.setter
    def IsText(self, val: bool) -> None:
        self._isText=val


    @property
    def IsLink(self) -> bool:      # ConFile(GridDataRowClass)
        return self._isLink
    @IsLink.setter
    def IsLink(self, val: bool) -> None:
        self._isLink=val

    @property
    def URL(self) -> str:      # ConFile(GridDataRowClass)
        return self._URL
    @URL.setter
    def URL(self, val: str) -> None:
        self._URL=val

    # Get or set a value by name or column number in the grid
    #def GetVal(self, name: Union[str, int]) -> Union[str, int]:
    def __getitem__(self, name: Union[int, slice]) -> Union[str, int]:
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

    #def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
    def __setitem__(self, index: Union[int, slice], value: ColDefinition) -> None:      # ConFile(GridDataRowClass)
        # (Could use return eval("self."+name))
        if index == 0:
            self.SourceFilename=value
            return
        if index == 1:
            self.SiteFilename=value
            return
        if index == 2:
            self.DisplayTitle=value
            return
        if index == 3:
            self.Pages=value
            return
        if index == 4:
            self.Notes=value
            return
        print("SetVal can't interpret '"+str(index)+"'")
        raise KeyError



#####################################################################################################
#####################################################################################################

class ConInstancePage(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: list[ColDefinition]=[
            ColDefinition("Source File Name", Width=100, IsEditable="maybe"),
            ColDefinition("Site Name", Width=75),
            ColDefinition("Display Name", Width=75),
            ColDefinition("Pages", Type="int", IsEditable="maybe"),
            ColDefinition("Notes", Width=150)
        ]
        self._element=ConFile
        self._conFileList: list[ConFile]=[]  # This supplies the Rows property that GridDataSource needs
        self._name: str=""
        self._specialTextColor: Optional[Color, bool]=True

    # Serialize and deserialize
    def ToJson(self) -> str:        # ConInstancePage(GridDataSource)
        dl=[]
        for con in self._conFileList:
            dl.append(con.ToJson())
        d={"ver": 3,
           "_name": self._name,
           "_conFileList": dl}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConInstancePage:        # ConInstancePage(GridDataSource)
        d=json.loads(val)
        if d["ver"] >= 1:
            self._name=d["_name"]
            cfld=d["_conFileList"]
            self._conFileList=[]
            for c in cfld:
                self._conFileList.append(ConFile().FromJson(c))

        return self

    @property        # ConInstancePage(GridDataSource)
    def Rows(self) -> list:
        return self._conFileList
    @Rows.setter
    def Rows(self, rows: list) -> None:
        self._conFileList=rows

    @property        # ConInstancePage(GridDataSource)
    def ColDefs(self) -> list[ColDefinition]:
        return self._colDefs

    @property        # ConInstancePage(GridDataSource)
    def Name(self) -> str:
        return self._name
    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    @property        # ConInstancePage(GridDataSource)
    def NumRows(self) -> int:
        return len(self._conFileList)

    def __getitem__(self, index) -> ConFile:        # ConInstancePage(GridDataSource)
        return self._conFileList[index]

    def __setitem__(self, index, value: ConFile) -> None:        # ConInstancePage(GridDataSource)
        self._conFileList[index]=value

    @property        # ConInstancePage(GridDataSource)
    def SpecialTextColor(self) -> Optional[Color]:
        return self._specialTextColor
    @SpecialTextColor.setter
    def SpecialTextColor(self, val: Optional[Color]) -> None:
        self._specialTextColor=val

