from __future__ import annotations
from typing import Optional, List, Union

import os
import sys
import wx
import wx.grid
import json
from datetime import datetime

from GenConEditorFrame import GenConEditorFrame
from DataGrid import DataGrid, GridDataSource
from ConSeriesFrame import ConSeriesFrame
from FTP import FTP
from Settings import Settings


from HelpersPackage import SubstituteHTML, FindBracketedText, FormatLink
from WxHelpers import ModalDialogManager
from Log import LogOpen, Log


class Convention:
    def __init__(self):
        self._name: str=""      # The name of the convention series
        self._URL: str=""       # The location of the convention series html page relative to the main cons page; empty if no series page exists yet


    def Signature(self) -> int:
        return hash(self._name.strip()+self._URL.strip())

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 2,
           "_name": self._name,
           "_URL": self._URL}
        return json.dumps(d)

    def FromJson(self, val: str) -> Convention:
        d=json.loads(val)
        self._name=d["_name"]
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

    # These two properties supplies a default value so that other uses of the grid don't need to implement it.
    @property
    # Is this line a text line. (Used -- so far -- only in a Con Instance.)
    def IsText(self) -> bool:
        return False
    @property
    # Is this line a link line. (Used -- so far -- only in a Con Instance.)
    def IsLink(self) -> bool:
        return False


class ConList(GridDataSource):
    _colheaders: List[str]=["Convention Series"]
    _coldatatypes: List[str]=["url"]
    _colminwidths: List[int]=[30]
    _coleditable: List[str]=["no"]
    _element=Convention

    def __init__(self):
        GridDataSource.__init__(self)
        self._conlist: List[Convention]=[]
        self._toptext: str=""

    #-----------------------------
    def Signature(self) -> int:
        return hash(self._toptext.strip())+GridDataSource().Signature()

    # -----------------------------
    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 2}
        for i, s in enumerate(self._conlist):
            d[i]=s.ToJson()

        return json.dumps(d)

    def FromJson(self, val: str) -> ConList:
        d=json.loads(val)
        self._conlist=[]
        i=0
        while str(i) in d.keys():       # Using str(i) is because json merges 1 and "1" as the same. (It appears to be a bug.)
            self._conlist.append(Convention().FromJson(d[str(i)]))
            i+=1
        return self

    # -----------------------------
    @property
    def ColMinWidths(self) -> List[int]:
        return ConList._colminwidths

    @property
    def ColHeaders(self) -> List[str]:
        return ConList._colheaders

    @property
    def ColEditable(self) -> List[str]:
        return ConList._coleditable

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

    # -----------------------------
    def SetDataVal(self, irow: int, icol: int, val: Union[int, str]) -> None:
        self._conlist[irow].SetVal(icol, val)



###############################################################################
###############################################################################

class ConEditorFrame(GenConEditorFrame):
    def __init__(self, parent):
        GenConEditorFrame.__init__(self, parent)

        # Class instance variables associated with RMB actions, etc.
        self.userSelection=None

        self._baseDirFTP: str=""

        self._signature=0

        self._grid: DataGrid=DataGrid(self.gRowGrid)
        self._grid.Datasource=ConList()
        self._grid.HideRowLabels()

        # Position the window on the screen it was on before
        tlwp=Settings().Get("Top Level Window Position")
        if tlwp is not None and len(tlwp) > 0:
            self.SetPosition(tlwp)

        self.Load()
        self.MarkAsSaved()
        self.Show()


    # ----------------------------------------------
    # Used to determine if anything has been updated
    def Signature(self) -> int:
        return self._grid.Signature()+hash(self.m_textCtrlTopText.GetValue().strip())

    def MarkAsSaved(self):
        Log("ConEditorFrame.MarkAsSaved -- "+str(self.Signature()))
        self._signature=self.Signature()

    def NeedsSaving(self):
        if self._signature != self.Signature():
            Log("ConEditorFrame.NeedsSaving -- "+str(self._signature)+" != "+str(self.Signature()))
        return self._signature != self.Signature()

    # ------------------
    # Serialize and deserialize
    def ToJson(self) -> str:            # ConEditorFrame
        d={"ver": 1,
           "_datasource": self._grid.Datasource.ToJson()
           }

        return json.dumps(d)

    def FromJson(self, val: str) -> ConEditorFrame:            # ConEditorFrame
        d=json.loads(val)
        self._grid.Datasource=ConList().FromJson(d["_datasource"])

        return self


    # ------------------
    def Load(self):            # ConEditorFrame
        # Clear out any old information
        self._grid.Datasource=ConList()

        Log("Loading root/index.html")
        file=FTP().GetFileAsString("", "index.html")
        if file is None:
            # Present an empty grid
            self.RefreshWindow()
            return

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is None or j == "":
            wx.MessageBox("Can't load convention information from conpubs' index.html")
            return

        try:
            self.FromJson(j)
        except (json.decoder.JSONDecodeError):
            wx.MessageBox("JSONDecodeError when loading convention information from conpubs' index.html")
            return

        self._grid.MakeTextLinesEditable()
        self.MarkAsSaved()
        self.RefreshWindow()


    #------------------
    def OnButtonUploadClick(self, event):            # ConEditorFrame
        self.Upload()

    def Upload(self):
        # First read in the template
        file=None
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConMain.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConMain.html'")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name might be tagged with <fanac-instance>, the random text with "fanac-headertext"
        file=SubstituteHTML(file, "fanac-stuff", self.m_textCtrlTopText.GetValue())

        # Now construct the table which we'll then substitute.
        newtable="  <thead>\n"
        newtable+="    <tr>\n"
        newtable+='      <th scope="col">Convention</th>\n'
        newtable+='    </tr>\n'
        newtable+='  </thead>\n'
        newtable+='  <tbody>\n'
        for row in self._grid.Datasource.Rows:
            newtable+="    <tr>\n"
            newtable+='      <td>'+FormatLink(row.URL, row.Name)+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"

        # Substitute the table into the template
        file=SubstituteHTML(file, "fanac-table", newtable)
        # Store the json for the page into the template
        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST")

        Log("Uploading /index.html")
        if not FTP().PutFileAsString("/", "index.html", file):
            Log("Upload of /index.html failed")
            wx.MessageBox("Upload of /index.html failed")

        self.MarkAsSaved()
        self.RefreshWindow()

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self.NeedsSaving():
            s=s+" *"
        self.Title=s


    #------------------
    def OnButtonSortClick(self, event):            # ConEditorFrame
        # Worldcon sorts ahead of everything else; Then "Early Conventions"; Then all other conventions; Finally empty lines after everything else
        def sorter(c: Convention) -> str:
            n=c.Name.upper()        # Convert to all UC so that sort is case-insensitive
            if n == "WORLDCON":
                return " "
            if n == "EARLY CONVENTIONS":
                return " "
            if len(n.strip()) == 0:
                return "ZZZZZZZZZ"      # This should sort last
            return n
        self._grid.Datasource.Rows=sorted(self._grid.Datasource.Rows, key=sorter)
        self.RefreshWindow()

    #------------------
    def OnButtonExitClick(self, event):            # ConEditorFrame
        self.OnClose(event)

    #------------------
    def OnGridCellRightClick(self, event):            # ConEditorFrame
        self._grid.OnGridCellRightClick(event, self.m_menuPopupConEditor)  # Set enabled state of default items; set all others to False

        self.m_popupItemInsert.Enabled=True
        if self._grid.clickedRow < self._grid.Datasource.NumRows:
            self.m_popupItemDelete.Enabled=True
            self.m_popupItemEdit.Enabled=True
            self.m_popupRename.Enabled=True
        self.m_popupItemInsert.Enabled=True
        self.PopupMenu(self.m_menuPopupConEditor, pos=self.gRowGrid.Position+event.Position)

    # ------------------
    def OnGridEditorShown(self, event):
        self._grid.OnGridEditorShown(event)

    # ------------------
    def OnGridCellDoubleClick(self, event):            # ConEditorFrame
        self._grid.OnGridCellDoubleClick(event)
        if event.GetRow() > self._grid.Datasource.NumRows:
            return      # For now, we do nothing when you double-click in an empty cell

        self.EditConSeries()

    # ------------------
    def EditConSeries(self):
        if self._grid.clickedRow >= self._grid.Datasource.NumRows:
            self._grid.Datasource.Rows.insert(self._grid.clickedRow, Convention())
            self.RefreshWindow()
        conseriesname=self._grid.Datasource.GetData(self._grid.clickedRow, 0)
        with ModalDialogManager(ConSeriesFrame, self._baseDirFTP, conseriesname) as dlg:
            if len(dlg.Seriesname.strip()) == 0:  # If the user didn't supply a con series name, we exit and don't show the dialog
                return

            if dlg.ShowModal() == wx.OK:
                conseriesname=dlg.tConSeries.GetValue()
                self._grid.Datasource.Rows[self._grid.clickedRow].URL="./"+conseriesname+"/index.html"
                self._grid.Datasource.Rows[self._grid.clickedRow].Name=conseriesname

        self.RefreshWindow()

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
        self.RefreshWindow()

    #------------------
    def OnPopupInsertCon(self, event):            # ConEditorFrame
        self._grid.Datasource.Rows.insert(self._grid.clickedRow, Convention())
        self.EditConSeries()    # clickedRow is set by the RMB clicked event that must have preceeded this.
        self.RefreshWindow()

    # ------------------
    def OnPopupDeleteCon(self, event):            # ConEditorFrame
        ret=wx.MessageBox("This will delete "+self._grid.Datasource.Rows[self._grid.clickedRow].Name+" from the list of convention series, but will not delete "+
                          "its directory or files from fanac.org. You must use FTP to do that.", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
        if ret == wx.OK:
            self._grid.DeleteRows(self._grid.clickedRow, 1)
            self.RefreshWindow()
        event.Skip()

    # ------------------
    def OnPopupEditCon(self, event):            # ConEditorFrame
        self.EditConSeries()    # clickedRow is set by the RMB clicked event that must have preceeded this.
        event.Skip()

    # ------------------
    def OnPopupRename(self, event):            # ConEditorFrame
        oldname=self._grid.Datasource.GetData(self._grid.clickedRow, 0)
        dlg=wx.TextEntryDialog(None, "Enter the new name of the Convention Series.", "Edit Convention Series name", value=oldname)
        if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
            return
        newname=dlg.GetValue()
        if newname != oldname:
            # Make sure newname isn't already on the list
            for row in self._grid.Datasource.Rows:
                if newname == row.Name:
                    wx.MessageBox("That is a duplicate convention name.", "Duplicate Con Name")
                    return
            self._grid.Datasource.SetDataVal(self._grid.clickedRow, 0, newname)
            self.RefreshWindow()
            FTP().SetDirectory("/")
            FTP().Rename(oldname, newname)
            self.Upload()

    # ------------------
    def OnTopTextUpdated(self, event):
        self._grid.Datasource.toptext=self.m_textCtrlTopText.GetValue()
        self.RefreshWindow()

    # ------------------
    def OnClose(self, event):            # ConEditorFrame
        if self.NeedsSaving():
            if event.CanVeto():
                ret=wx.MessageBox("The main con list has been updated and not yet saved. Exit anyway?", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if ret == wx.CANCEL:
                    event.Veto()
                    return

        # Save the window's position
        pos=self.GetPosition()
        Settings().Put("Top Level Window Position", (pos.x, pos.y))

        self.Destroy()


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")

f=FTP()
if not f.OpenConnection("FTP Credentials.json"):
    Log("Main: OpenConnection('FTP Credentials.json' failed")
    exit(0)

# Load the global settings dictionary
Settings().Load("ConEditor settings.json")

app=wx.App(False)
frame=ConEditorFrame(None)
# frame.ShowModal()
# frame.SetFocus()
# frame.Raise()
#
app.MainLoop()
pass


