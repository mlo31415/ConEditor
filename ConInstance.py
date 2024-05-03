from __future__ import annotations

import os

from HelpersPackage import Int0, Float0, RemoveAccents
from WxDataGrid import GridDataSource, Color, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable


# An individual file to be listed under a convention
# This is a single row
class ConFile(GridDataRowClass):
    def __init__(self):
        self._displayTitle: str=""      # The name as shown to the world on the website
        self._notes: str=""             # The free-format description
        self._localfilename: str=""     # The filename of the source file
        self._localpathname: str="."    # The local pathname of the source file (path+filename)
        self._sitefilename: str=""      # The name to be used for this file on the website (It will be (part of) the URL and holds the URL for link rows.)
        self._size: int=0               # The file's size in bytes
        self._isText: bool=False        # Is this a piece of text rather than a convention?
        self._isLink: bool=False        # Is this a link?
        self._pages: int=0              # Page count


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
        if Float0(self.Size) > 0:
            s+="Size="+str(self.Size)+"; "
        if Int0(self.Pages) > 0:
            s+="Pages="+str(self.Pages)+"; "
        if self.IsTextRow:
            s+="IsTextRow; "
        if self.IsLinkRow:
            s+="IsLinkRow; "

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
        cf._pages=self._pages
        return cf

    def Signature(self) -> int:      
        tot=hash(self._displayTitle.strip()+self._notes.strip()+self._localfilename.strip()+self._localpathname.strip()+self._sitefilename.strip())
        return tot+hash(self._size)+hash(self._isText)+Int0(self.Pages)


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

    # When a line is a text line, it stores the text in DisplayTitle.  This is just an alias to make the code a bit more comprehensible.
    @property
    def TextLineText(self) -> str:
        return self.DisplayTitle
    @TextLineText.setter
    def TextLineText(self, val: str) -> None:
        self.DisplayTitle=val


    @property
    def SiteFilename(self) -> str:      
        return self._sitefilename
    @SiteFilename.setter
    def SiteFilename(self, val: str) -> None:      
        self._sitefilename=RemoveAccents(val)


    @property
    def Size(self) -> float:
        return self._size
    @Size.setter
    def Size(self, val: int|float|str) -> None:
        if isinstance(val, str):
            val=Float0(val)
        if val > 500:  # We're looking for a value in MB, but if we get a value in bytess, convert it
            val=val/(1024**2)
        self._size=val

    @property
    def Pages(self) -> int:      
        if self._pages is None:
            return 0
        return self._pages
    @Pages.setter
    def Pages(self, val: int|str) -> None:      
        if type(val) is str:
            val=Int0(val)
        self._pages=val

    @property
    def IsTextRow(self) -> bool:      
        return self._isText
    @IsTextRow.setter
    def IsTextRow(self, val: bool) -> None:
        self._isText=val

    @property
    def IsLinkRow(self) -> bool:      
        return self._isLink
    @IsLinkRow.setter
    def IsLinkRow(self, val: bool) -> None:
        self._isLink=val


    # Get or set a value by name or column number in the grid
    def __getitem__(self, index: int|slice) -> str|int|float:
        # (Could use return eval("self."+name))
        if index == 0:
            return self.DisplayTitle
        if index == 1:
            return self.SourceFilename
        if index == 2:
            return self.SiteFilename
        if index == 3:
            if self.Pages == 0:
                return ""
            return self.Pages
        if index == 4:
            return self.Size
        if index == 5:
            return self.Notes
        return "Val can't interpret '"+str(index)+"'"

    def __setitem__(self, index: int|slice, value: str) -> None:      
        # (Could use return eval("self."+name))
        if index == 0:
            self.DisplayTitle=value
            return
        if index == 1:
            self.SourceFilename=value
            return
        if index == 2:
            self.SiteFilename=value
            return
        if index == 3:
            if isinstance(value, int):
                self.Pages=value
            else:
                self.Pages=Int0(value.strip())
            return
        if index == 4:
            self.Size=Float0(value)
            return
        if index == 5:
            self.Notes=value
            return
        print("SetVal can't interpret '"+str(index)+"'")
        raise KeyError


    @property
    def IsEmptyRow(self) -> bool:      
        return self.SourceFilename == "" and self.SiteFilename == "" and self.DisplayTitle == "" and Int0(self.Pages) == 0 and self.Notes != ""


#####################################################################################################
#####################################################################################################

class ConInstancePage(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList=ColDefinitionsList([
            ColDefinition("Display Name", Width=75),
            ColDefinition("Source File Name", Width=100, IsEditable=IsEditable.Maybe),
            ColDefinition("Site Name", Width=75),
            ColDefinition("Pages", Type="int", IsEditable=IsEditable.Maybe),
            ColDefinition("Size (MB)", Type="float", IsEditable=IsEditable.Maybe),
            ColDefinition("Notes", Width=150)
        ])
        self._element=ConFile
        self._conFileList: list[ConFile]=[]  # This supplies the Rows property that GridDataSource needs
        self._name: str=""
        self._specialTextColor: Color|bool|None =True



    def Signature(self) -> int:        
        s=self._colDefs.Signature()+hash(self._name.strip())+hash(self._specialTextColor)
        return s+sum([x.Signature()*(i+1) for i, x in enumerate(self._conFileList)])


    @property        
    def Rows(self) -> list:
        return self._conFileList
    @Rows.setter
    def Rows(self, rows: list) -> None:        
        self._conFileList=rows

    @property        
    def ColDefs(self) -> ColDefinitionsList:
        return self._colDefs

    @property
    def TextAndHrefCols(self) -> (int, int):
        return self.ColHeaderIndex("Display Name"), self.ColHeaderIndex("Site Name")    # These are the cols to be used for link text and href

    @property        
    def Name(self) -> str:
        return self._name
    @Name.setter
    def Name(self, val: str) -> None:        
        self._name=val

    @property        
    def NumRows(self) -> int:
        return len(self._conFileList)

    def __getitem__(self, index) -> ConFile:        
        return self._conFileList[index]

    def __setitem__(self, index, value: ConFile) -> None:        
        self._conFileList[index]=value

    @property        
    def SpecialTextColor(self) -> Color|None:
        return self._specialTextColor
    @SpecialTextColor.setter
    def SpecialTextColor(self, val: Color|None) -> None:        
        self._specialTextColor=val

    def InsertEmptyRows(self, index: int, num: int=1) -> None:        
        if num <= 0:
            return
        if index > len(self.Rows):
            index=len(self.Rows)
        self.Rows=self.Rows[:index]+[ConFile() for i in range(num)]+self.Rows[index:]


