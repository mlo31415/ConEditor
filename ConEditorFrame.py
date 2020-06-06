from __future__ import annotations
from typing import Optional, List, Union

import os
import sys
import wx
import wx.grid
import json
from datetime import date

from GenConEditorFrame import GenConEditorFrame
from Grid import Grid, GridDataSource
from ConSeriesFramePage import MainConSeriesFrame
from FTP import FTP
from Settings import Settings
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
    _colheaders: List[str]=["Convention Series"]
    _coldatatypes: List[str]=["url"]
    _colminwidths: List[int]=[30]
    _element=Convention

    def __init__(self):
        self._conlist: List[Convention]=[]
        self._updated: bool=False
        self._toptext: str=""

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
        self._updated=False

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

    @property
    def Updated(self) -> bool:
        return self._updated or (self._grid._datasource.Updated is not None and self._grid._datasource.Updated)
    @Updated.setter
    def Updated(self, val: bool) -> None:
        self._updated=val
        if val == False:    # If we're setting the updated flag to False, set the grid's flag, too.
            self._grid._datasource.Updated=False

    #------------------
    def ProgressMessage(self, s: str) -> None:            # ConEditorFrame
        self.m_statusBar.SetStatusText(s)

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
        self.Updated=False   # Freshly loaded is in a saved state


    #------------------
    def OnButtonUploadClick(self, event):            # ConEditorFrame

        # First read in the template
        file=None
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConMain.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConMain.html'")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name might be tagged with <fanac-instance>, the random text with "fanac-headertext"
        file=SubstituteHTML(file, "fanac-stuff", self.m_textCtrlTopText.Value)

        # Now construct the table which we'll then substitute.
        newtable="  <thead>\n"
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

        # Substitute the table into the template
        file=SubstituteHTML(file, "fanac-table", newtable)
        # Store the json for the page into the template
        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        self.ProgressMessage("Uploading /index.html")
        Log("Uploading /index.html")
        if not FTP().PutFileAsString("/", "index.html", file):
            Log("Upload of /index.html failed")
            wx.MessageBox("Upload of /index.html failed")
            self.ProgressMessage("Upload of /index.html failed")
        else:
            self.ProgressMessage("Upload of /index.html succeeded")

        self.Updated=False
        self.RefreshWindow()

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self.Updated:
            s=s+" *"
        self.Title=s


    #------------------
    def OnButtonSortClick(self, event):            # ConEditorFrame
        self._grid._datasource.Rows=sorted(self._grid._datasource.Rows, key=lambda r: r.Name if r.Name != "Worldcon" else " ")  # Worldcon sorts ahead of everything else
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

        self.m_menuItemInsert.Enabled=True
        if self._grid._datasource.NumRows > event.GetRow():
            self.m_menuItemDelete.Enabled=True
        if event.GetRow() < self._grid._datasource.NumRows:
            self.m_menuItemEdit.Enabled=True

        self.PopupMenu(self.m_menuPopupConEditor, pos=self.gRowGrid.Position+event.Position)

    # ------------------
    def OnGridCellDoubleClick(self, event):            # ConEditorFrame
        if event.GetRow() > self._grid._datasource.NumRows:
            return      # For now, we do nothing when you double-click in an empty cell
        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()
        self.EditConSeries()

    # ------------------
    def EditConSeries(self):
        if self.clickedRow >= self._grid._datasource.NumRows:
            self._grid._datasource.Rows.insert(self.clickedRow, Convention())
            self.RefreshWindow()
        conseriesname=self._grid._datasource.GetData(self.clickedRow, 0)
        dlg=MainConSeriesFrame(self._baseDirFTP, conseriesname)
        #        dlg.tConInstanceName.Value=name
        ret=dlg.ShowModal()
        if ret == wx.OK:
            conseriesname=dlg.tConSeries.Value
            self._grid._datasource.Rows[self.clickedRow].URL="./"+conseriesname+"/index.html"
            self._grid._datasource.Rows[self.clickedRow].Name=conseriesname

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
        self._grid._datasource.Rows.insert(self.clickedRow, Convention())
        self.EditConSeries()    # clickedRow is set by the RMB clicked event that must have preceeded this.
        name=self._grid._datasource.Rows[self.clickedRow].Name
        self.RefreshWindow()

    # ------------------
    def OnPopupDeleteCon(self, event):            # ConEditorFrame
        del self._grid._datasource.Rows[self.clickedRow]
        self.RefreshWindow()
        event.Skip()

    # ------------------
    def OnPopupEditCon(self, event):            # ConEditorFrame
        self.EditConSeries()    # clickedRow is set by the RMB clicked event that must have preceeded this.
        event.Skip()

    # ------------------
    def OnTopTextUpdated(self, event):
        self._grid._datasource.toptext=self.m_textCtrlTopText.Value
        self.Updated=True
        self.RefreshWindow()

    # ------------------
    def OnClose(self, event):            # ConEditorFrame
        if self.Updated:
            if event.CanVeto():
                resp=wx.MessageBox("The main con list has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return
        self.Destroy()


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")

f=FTP()
if not f.OpenConnection("FTP Credentials.json"):
    Log("Main: OpenConnection('FTP Credentials.json' failed")
    wx.MessageBox("OpenConnection('FTP Credentials.json' failed")
    exit(0)

# Load the global settings dictionary
Settings().Load("ConEditor settings.json")


app = wx.App(False)
frame = ConEditorFrame(None)
app.MainLoop()
