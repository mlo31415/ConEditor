from __future__ import annotations
from typing import Optional, List, Union

import os
import wx
import wx.grid
import json
from datetime import date

from GenConEditorFrame import GenConEditorFrame
from Grid import Grid, GridDataSource
from ConSeriesFramePage import MainConSeriesFrame
from FTP import FTP
from dlgEnterFancyName import dlgEnterFancyNameWindow

from HelpersPackage import SubstituteHTML, FindBracketedText, FormatLink
from Log import LogOpen, Log

class Convention:
    def __init__(self):
        self._name: str=""      # The name of the convention series
        self._URL: str=""       # The location of the convention series html page relative to the main cons page; empty if no series page exists yet

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 2,
           "_name": self._name,
           "_URL": self._URL}
        return json.dumps(d)

    def FromJson(self, val: str) -> Convention:
        d=json.loads(val)
        self._name=d["_name"]
        if d["ver"] == 2:
            self._URL=d["_URL"]

        return self

    # Get or set a value by name or column number
    def GetVal(self, name: Union[str, int]) -> Union[str, int]:
        # (Could use return eval("self."+name))
        if name == "Convention" or name == 0:
            return self._name
        return "Convention.Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == "Convention" or nameOrCol == 0:
            self._name=val
            return
        print("Convention.SetVal can't interpret '"+str(nameOrCol)+"'")

    @property
    def Name(self) -> str:
        return self._name
    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    @property
    def URL(self) -> str:
        return self._URL
    @URL.setter
    def URL(self, val: str) -> None:
        self._URL=val



class ConList(GridDataSource):
    _colheaders: List[str]=["Convention"]
    _coldatatypes: List[str]=["url"]
    _colminwidths: List[int]=[30]
    _element=Convention

    def __init__(self):
        self._conlist: List[Convention]=[]
        self._updated: bool=False

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
    def ColHeaders(self) -> List[str]:
        return ConList._colheaders

    @property
    def ColDataTypes(self) -> List[str]:
        return ConList._coldatatypes

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

    @property
    def Updated(self) -> bool:
        return self._updated
    @Updated.setter
    def Updated(self, val: bool) -> None:
        self._updated=val


class ConEditorFrame(GenConEditorFrame):
    def __init__(self, parent):
        GenConEditorFrame.__init__(self, parent)

        self.userSelection=None
        self.cntlDown: bool=False
        self.clickedColumn: Optional[int]=None
        self._baseDirFTP: str=""

        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConList()
        self._grid.SetColHeaders(self._grid._datasource._colheaders)
        self._grid.SetColTypes(ConList._coldatatypes)
        self._grid._grid.HideRowLabels()
        self._grid.RefreshGridFromData()

        self.Load()

        self.Show()

    # ------------------
    # Serialize and deserialize
    def ToJson(self) -> str:            # ConEditorFrame
        d={"ver": 1,
           #"_textConSeries": self._textConSeriesName,
           "_datasource": self._grid._datasource.ToJson()
           }

        return json.dumps(d)

    #------------------
    def FromJson(self, val: str) -> ConEditorFrame:            # ConEditorFrame
        d=json.loads(val)
        #self._textConSeriesName=d["_textConSeries"]
        self._grid._datasource=ConList().FromJson(d["_datasource"])

        return self

    #------------------
    def ProgressMessage(self, s: str) -> None:            # ConEditorFrame
        self.m_staticTextMessages.Label=s

    # ------------------
    def Load(self):            # ConEditorFrame

        # Clear out any old information
        self._grid._datasource=ConList()

        self.ProgressMessage("Loading root/index.html")
        file=FTP().GetFileAsString("", "index.html")
        if file is None:
            # Present an empty grid
            self.RefreshWindow()
            return

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is None or j == "":
            wx.MessageBox("Can't load convention information from Conpubs' index.html")
            return

        try:
            self.FromJson(j)
        except (json.decoder.JSONDecodeError):
            wx.MessageBox("JSONDecodeError when loading convention information from Conpubs' index.html")
            return

        # Insert the row data into the grid
        self.RefreshWindow()
        self.ProgressMessage("root/index.html Loaded")
        self._grid._datasource.Updated=False   # Freshly loaded is in a saved state


    #------------------
    def OnButtonSaveClick(self, event):            # ConEditorFrame

        # First read in the template
        file=None
        with open("Template-ConSeries.html") as f:
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
            newtable+='      <td>'+FormatLink(row.URL, row.Name)+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        # Substitute the table into the template
        file=SubstituteHTML(file, "pdq", newtable)
        # Store the json for the page into the template
        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        FTP().PutFileAsString("/", "index.html", file)
        self._grid._datasource.Updated=False
        self.RefreshWindow()


    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self._grid._datasource.Updated:
            s=s+" *"
        self.Title=s


    #------------------
    def OnButtonSortClick(self, event):            # ConEditorFrame
        self._grid._datasource.Rows=sorted(self._grid._datasource.Rows, key=lambda r: r.Name)
        self._grid._datasource.Updated=True
        self.RefreshWindow()


    #------------------
    def OnButtonExitClick(self, event):            # ConEditorFrame
        self.OnClose(event)

    #------------------
    def OnGridCellRightClick(self, event):            # ConEditorFrame
        self._grid.OnGridCellRightClick(event, self.m_menuPopupConEditor)
        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()

        mi=self.m_menuPopupConEditor.FindItemById(self.m_menuPopupConEditor.FindItem("Insert Convention"))
        mi.Enabled=True

        if self._grid._datasource.NumRows > event.GetRow():
            mi=self.m_menuPopupConEditor.FindItemById(self.m_menuPopupConEditor.FindItem("Delete Convention"))
            mi.Enabled=True

        self.PopupMenu(self.m_menuPopupConEditor, pos=self.gRowGrid.Position+event.Position)

    # ------------------
    def OnGridCellDoubleClick(self, event):            # ConEditorFrame
        if event.GetRow() > self._grid._datasource.NumRows:
            return      # For now, we do nothing when you double-click in an empty cell
        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()
        if self.clickedRow >= self._grid._datasource.NumRows:
            self._grid._datasource.Rows.insert(self.clickedRow, Convention())
            self.RefreshWindow()
        conseriesname=self._grid._datasource.GetData(self.clickedRow, 0)
        dlg=MainConSeriesFrame(self._baseDirFTP, conseriesname)
#        dlg.tConInstanceName.Value=name
        dlg.ShowModal()
        self._grid._datasource.Rows[self.clickedRow].URL="./"+conseriesname+"/"+conseriesname+".html"
        self._grid._datasource.Rows[self.clickedRow].Name=conseriesname
        pass

    # ------------------
    def OnGridLabelRightClick(self, event):  # Grid
        self._grid.OnGridLabelRightClick(event)

    #-------------------
    def OnKeyDown(self, event):            # ConEditorFrame
        self._grid.OnKeyDown(event)

    #-------------------
    def OnKeyUp(self, event):            # ConEditorFrame
        self._grid.OnKeyUp(event)

    #------------------
    def OnPopupCopy(self, event):            # ConEditorFrame
        self._grid.OnPopupCopy(event)

    #------------------
    def OnPopupPaste(self, event):            # ConEditorFrame
        self._grid.OnPopupPaste(event)

    #------------------
    def OnGridCellChanged(self, event):            # ConEditorFrame
        self._grid.OnGridCellChanged(event)

    #------------------
    def OnPopupInsertCon(self, event):            # ConEditorFrame
        self._grid._datasource.Rows.insert(self.clickedRow-1, Convention())
        self.RefreshWindow()

    # ------------------
    def OnPopupDeleteCon(self, event):            # ConEditorFrame
        del self._grid._datasource.Rows[self.clickedRow]
        self.RefreshWindow()
        event.Skip()

    # ------------------
    def OnClose(self, event):            # ConEditorFrame
        if self._grid._datasource.Updated:
            resp=wx.MessageBox("The main con list has been updated and not yet saved. Exit anyway?", 'Warning',
                   wx.OK|wx.CANCEL|wx.ICON_WARNING)
            if resp == wx.CANCEL:
                event.Skip()
                return
        self.Destroy()


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")

f=FTP()
f.OpenConnection("FTP Credentials.json")
f.SetRoot(local="")


app = wx.App(False)
frame = ConEditorFrame(None)
app.MainLoop()
