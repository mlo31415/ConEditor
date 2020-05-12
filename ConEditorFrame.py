from __future__ import annotations
from typing import Optional, List, Union

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup, NavigableString
from urllib.request import urlopen
import json

from GenConEditorFrame import GenConEditorFrame
from Grid import Grid

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import LogOpen

class Convention:
    def __init__(self):
        self._name: str=""

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 1,
           "_name": self._name}
        return json.dumps(d)

    def FromJson(self, val: str) -> Convention:
        d=json.loads(val)
        if d["ver"] <= 1:
            self._name=d["_name"]
        return self

    # Get or set a value by name or column number
    def GetVal(self, name: Union[str, int]) -> Union[str, int, FanzineDateRange]:
        # (Could use return eval("self."+name))
        if name == "Convention" or name == 0:
            return self._name
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int, FanzineDateRange]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == "Convention" or nameOrCol == 0:
            self._name=val
            return
        print("SetVal can't interpret '"+str(nameOrCol)+"'")



class ConList:
    _colheaders: List[str]=["Convention"]
    _coldatatypes: List[str]=["str"]
    _colminwidths: List[int]=[30]
    _element=Convention

    def __init__(self):
        self._conlist: List[Convention]=[]

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 1,
           "_colheaders": self._colheaders,
           "_coldatatypes": self._coldatatypes,
           "_colminwidths": self._colminwidths}
        i=0
        for s in self._conlist:
            d[i]=s.ToJson()
            i+=1
        return json.dumps(d)

    def FromJson(self, val: str) -> ConList:
        d=json.loads(val)
        self._colheaders=d["_colheaders"]
        self._coldatatypes=d["_coldatatypes"]
        self._colminwidths=d["_colminwidths"]
        self._conlist=[]
        i=0
        while str(i) in d.keys():       # Using str(i) is because json merges 1 and "1" as the same. (It appears to be a bug.)
            self._conlist.append(Convention().FromJson(d[str(i)]))
            i+=1
        return self

    @property
    def ColMinWidths(self) -> List[int]:
        return ConList._colminwidths

    @property
    def NumRows(self) -> int:
        return len(self._conlist)

    def GetData(self, iRow: int, iCol: int) -> str:
        if iRow == -1:  # Handle logical coordinate of column headers
            return self._colheaders[iCol]

        r=self.Rows[iRow]
        return r.GetVal(iCol)

    @property
    def Rows(self) -> List:
        return self._conlist

    @Rows.setter
    def Rows(self, rows: List) -> None:
        self._conlist=rows

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str]) -> None:
        self._conlist[irow].SetVal(icol, val)


class ConEditorFrame(GenConEditorFrame):
    def __init__(self, parent):
        GenConEditorFrame.__init__(self, parent)

        self.userSelection=None
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None

        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConList()
        self._grid.SetColHeaders(self._grid._datasource._colheaders)
        self._grid.SetColTypes(ConList._coldatatypes)
        self._grid.RefreshGridFromData()

        self.Show()

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 1,
           #"_textConSeries": self._textConSeriesName,
           "_datasource": self._grid._datasource.ToJson()
           }

        return json.dumps(d)

    def FromJson(self, val: str) -> ConEditorFrame:
        d=json.loads(val)
        #self._textConSeriesName=d["_textConSeries"]
        self._grid._datasource=ConList().FromJson(d["_datasource"])

        return self

    def OnButtonSaveClick(self, event):

        # First read in the template
        file=None
        self._dirname="."
        with open(os.path.join(self._dirname, "Template-ConSeries")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        #link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self._textConSeriesName), self._textConSeriesName)
        #file=SubstituteHTML(file, "title", self._textConSeriesName)
        #file=SubstituteHTML(file, "abc", link)
        #file=SubstituteHTML(file, "xyz", self._textComments)

        # Now construct the table which we'll then substitute.
        newtable='<table class="table">\n'
        newtable+="  <thead>\n"
        newtable+="    <tr>\n"
        newtable+='      <th scope="col">Convention</th>\n'
        newtable+='    </tr>\n'
        newtable+='  </thead>\n'
        newtable+='  <tbody>\n'
        for row in self._grid._datasource.Rows:
            newtable+="    <tr>\n"
            newtable+='      <td>'+row.Name+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "pdq", newtable)
        file=SubstituteHTML(file, "fanac-json", self.ToJson())
        with open("Conventions.html", "w+") as f:
            f.write(file)


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")
app = wx.App(False)
frame = ConEditorFrame(None)
app.MainLoop()
