from __future__ import annotations

from typing import Union

import os
import sys
import wx
import wx.grid
import json
from datetime import datetime

from GenConEditorFrame import GenConEditorFrame
from WxDataGrid import DataGrid, GridDataSource, GridDataRowClass, ColDefinition, ColDefinitionsList
from ConSeriesFrame import ConSeriesFrame
from ConInstanceDeltaTracker import UpdateLog
from FTP import FTP
from Settings import Settings


from HelpersPackage import SubstituteHTML, FindBracketedText, FormatLink, Int, MessageBox, PyiResourcePath
from WxHelpers import ModalDialogManager, OnCloseHandling
from Log import LogOpen, Log, LogFlush


class Convention(GridDataRowClass):
    def __init__(self):
        self._name: str=""      # The name of the convention series
        self._URL: str=""       # The location of the convention series html page relative to the main cons page; empty if no series page exists yet


    def Signature(self) -> int:     # Convention(GridDataRowClass)
        s=hash(self._name.strip()+self._URL.strip())
        Log(f"Convention(GridDataRowClass).Signature {s=}")
        return s

    # Serialize and deserialize
    def ToJson(self) -> str:     # Convention(GridDataRowClass)
        d={"ver": 2,
           "_name": self._name,
           "_URL": self._URL}
        return json.dumps(d)

    def FromJson(self, val: str) -> Convention:     # Convention(GridDataRowClass)
        d=json.loads(val)
        self._name=d["_name"]
        self._URL=d["_URL"]

        return self

    # Get or set a value by name or column number
    #def GetVal(self, name: Union[str, int]) -> Union[str, int]:
    def __getitem__(self, index: Union[str, int, slice]) -> Union[str, int]:     # Convention(GridDataRowClass)
        # (Could use return eval("self."+name))
        if index == "Convention" or index == 0:
            return self._name
        return "Convention.Val can't interpret '"+str(index)+"'"

    #def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int]) -> None:
    def __setitem__(self, nameOrCol: Union[str, int, slice], value: ColDefinition) -> None:     # Convention(GridDataRowClass)
        # (Could use return eval("self."+name))
        if nameOrCol == "Convention" or nameOrCol == 0:
            self._name=value
            return
        print("Convention.SetVal can't interpret '"+str(nameOrCol)+"'")
        raise KeyError

    @property
    def Name(self) -> str:     # Convention(GridDataRowClass)
        return self._name
    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    @property
    def URL(self) -> str:     # Convention(GridDataRowClass)
        return self._URL
    @URL.setter
    def URL(self, val: str) -> None:
        self._URL=val


class ConList(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList =ColDefinitionsList([
            ColDefinition("Convention Series", Type="url", IsEditable="no")
            ])    # There's only one column!
        self._gridDataRowClass: Convention=Convention()
        self._conlist: list[Convention]=[]  # This supplies the Rows property that GridDataSource needs

    # -----------------------------
    # Serialize and deserialize
    def ToJson(self) -> str:         # ConList(GridDataSource)
        d={"ver": 2}
        for i, s in enumerate(self._conlist):
            d[i]=s.ToJson()

        return json.dumps(d)

    def FromJson(self, val: str) -> ConList:         # ConList(GridDataSource)
        d=json.loads(val)
        self._conlist=[]
        i=0
        while str(i) in d.keys():       # Using str(i) is because json merges 1 and "1" as the same. (It appears to be a bug.)
            self._conlist.append(Convention().FromJson(d[str(i)]))
            i+=1
        return self


    def Signature(self) -> int:         # ConList(GridDataSource)
        s=sum([hash(x)*(i+1) for i, x in enumerate(self._conlist)])
        return s

    @property
    def ColDefs(self) -> ColDefinitionsList:         # ConList(GridDataSource)
        return self._colDefs

    @property
    def NumRows(self) -> int:         # ConList(GridDataSource)
        return len(self._conlist)

    def __getitem__(self, index: int) -> Convention:         # ConList(GridDataSource)
        assert index != -1
        return self.Rows[index]

    def __setitem__(self, index: int, val: Convention) -> None:         # ConList(GridDataSource)
        assert index != -1
        self.Rows[index]=val

    @property
    def Rows(self) -> list:         # ConList(GridDataSource)
        return self._conlist
    @Rows.setter
    def Rows(self, rows: list) -> None:
        self._conlist=rows


    def InsertEmptyRows(self, index: int, num: int=1) -> None:         # ConList(GridDataSource)
        if num <= 0:
            return
        if index > len(self.Rows):
            index=len(self.Rows)
        self.Rows=self.Rows[:index]+[Convention() for i in range(num)]+self.Rows[index:]


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
        self.Datasource=ConList()

        self._grid.HideRowLabels()

        # Position the window on the screen it was on before
        tlwp=Settings().Get("Top Level Window Position")
        if tlwp:
            self.SetPosition(tlwp)

        self.Load()
        self.MarkAsSaved()
        self.Show()


    @property
    def Datasource(self) -> ConList:        # ConEditorFrame(GenConEditorFrame)
        return self._Datasource
    @Datasource.setter
    def Datasource(self, val: ConList):
        self._Datasource: ConList=val
        self._grid.Datasource=val

    # ----------------------------------------------
    # Used to determine if anything has been updated
    def Signature(self) -> int:        # ConEditorFrame(GenConEditorFrame)
        s=self.Datasource.Signature()+hash(self.m_textCtrlTopText.GetValue().strip())
        return s


    def MarkAsSaved(self):        # ConEditorFrame(GenConEditorFrame)
        self._signature=self.Signature()
        self.UpdateNeedsSavingFlag()


    def NeedsSaving(self) -> bool:        # ConEditorFrame(GenConEditorFrame)
        v=self._signature != self.Signature()
        self.UpdateNeedsSavingFlag()
        return v


    def UpdateNeedsSavingFlag(self):        # ConEditorFrame(GenConEditorFrame)
        s=self.Title.removesuffix(" *")  # Remove existing Needs Saving marker, if any
        if self.Signature() != self._signature:
            s=s+" *"
        self.Title=s

    # ------------------
    # Serialize and deserialize
    def ToJson(self) -> str:        # ConEditorFrame(GenConEditorFrame)
        d={"ver": 1,
           "_datasource": self.Datasource.ToJson()
           }

        return json.dumps(d)

    def FromJson(self, val: str) -> ConEditorFrame:            # ConEditorFrame
        d=json.loads(val)
        self.Datasource=ConList().FromJson(d["_datasource"])

        return self

    # ------------------
    def Load(self):            # ConEditorFrame
        # Clear out any old information
        self.Datasource=ConList()

        Log("Loading root/index.html")
        file=FTP().GetFileAsString("", "index.html")
        if file is None:
            # Present an empty grid
            self.RefreshWindow()
            return

        # Get the JSON
        j=FindBracketedText(file, "fanac-json", stripHtml=False)[0]
        if j is None or j == "":
            wx.MessageBox("Can't load convention information from conpubs' index.html")
            return

        try:
            self.FromJson(j)
        except (json.decoder.JSONDecodeError):
            wx.MessageBox("JSONDecodeError when loading convention information from conpubs' index.html")
            return

        self._grid.MakeTextLinesEditable()
        self.RefreshWindow()
        self.MarkAsSaved()



    @property
    def Title(self) -> str:        # ConEditorFrame(GenConEditorFrame)
        return self.GetTitle()
    @Title.setter
    def Title(self, val) -> None:
        self.SetTitle(val)


    #------------------
    def OnButtonUploadClick(self, event):            # ConEditorFrame
        self.Upload()

    def Upload(self):        # ConEditorFrame(GenConEditorFrame)
        # First read in the template
        file=None
        try:
            with open(PyiResourcePath("Template-ConMain.html")) as f:
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
        for i, row in enumerate(self.Datasource.Rows):
            if i == 3:  # Add a crude horizontal rule between items 3 (Misc. Cons) and 4 (1st real con)
                newtable+="    <tr>\n      <td>------------------</td>\n    <tr>\n"
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


        UpdateLog().LogText("Uploaded Main convention list")

        self.MarkAsSaved()
        self.RefreshWindow()

    #------------------
    def RefreshWindow(self) -> None:        # ConEditorFrame(GenConEditorFrame)
        self._grid.RefreshWxGridFromDatasource()
        self.UpdateNeedsSavingFlag()

    #------------------
    def OnButtonSortClick(self, event):            # ConEditorFrame(GenConEditorFrame)
        # Worldcon sorts ahead of everything else; Then "Early Conventions"; Then all other conventions; Finally empty lines after everything else
        def sorter(c: Convention) -> str:
            n=c.Name.upper()        # Convert to all UC so that sort is case-insensitive
            if n == "WORLDCON":
                return " "
            if n == "EARLY CONVENTIONS":
                return " "
            if n == "MISC. CONVENTIONS":
                return " "
            if len(n.strip()) == 0:
                return "ZZZZZZZZZ"      # This should sort last
            return n
        self.Datasource.Rows=sorted(self.Datasource.Rows, key=sorter)
        self.RefreshWindow()

    #------------------
    def OnButtonExitClick(self, event):            # ConEditorFrame
        self.OnClose(event)

    #------------------
    def OnGridCellRightClick(self, event):            # ConEditorFrame
        self._grid.OnGridCellRightClick(event, self.m_GridPopup)  # Set enabled state of default items; set all others to False

        self.m_popupItemInsert.Enabled=True
        if self._grid.clickedRow < self.Datasource.NumRows:
            self.m_popupItemDelete.Enabled=True
            self.m_popupItemEdit.Enabled=True
            self.m_popupRename.Enabled=True
        self.m_popupItemInsert.Enabled=True
        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)

    # ------------------
    def OnGridEditorShown(self, event):        # ConEditorFrame(GenConEditorFrame)
        self._grid.OnGridEditorShown(event)

    # ------------------
    def OnGridCellDoubleClick(self, event):            # ConEditorFrame
        self._grid.OnGridCellDoubleClick(event)
        if event.GetRow() > self.Datasource.NumRows:
            return      # For now, we do nothing when you double-click in an empty cell

        self.EditConSeries()

    # ------------------
    def EditConSeries(self):        # ConEditorFrame(GenConEditorFrame)
        if self._grid.clickedRow >= self.Datasource.NumRows:
            self.Datasource.Rows.insert(self._grid.clickedRow, Convention())
            self.RefreshWindow()
        conseriesname=self.Datasource[self._grid.clickedRow][0]
        # Create list of con series required by the con series editor
        conserieslist=[row.Name for row in self.Datasource.Rows]
        with ModalDialogManager(ConSeriesFrame, self._baseDirFTP, conseriesname, conserieslist) as dlg:
            if len(dlg.Seriesname.strip()) == 0:  # If the user didn't supply a con series name, we exit and don't show the dialog
                return

            if dlg.ShowModal() == wx.OK:
                conseriesname=dlg.tConSeries.GetValue()
                self.Datasource.Rows[self._grid.clickedRow].URL="./"+conseriesname+"/index.html"
                self.Datasource.Rows[self._grid.clickedRow].Name=conseriesname

        self.RefreshWindow()

    #-------------------
    def OnKeyDown(self, event):            # ConEditorFrame(GenConEditorFrame)
        self._grid.OnKeyDown(event)
        self.UpdateNeedsSavingFlag()

    #-------------------
    def OnKeyUp(self, event):            # ConEditorFrame(GenConEditorFrame)
        self._grid.OnKeyUp(event)

    #------------------
    def OnPopupCopy(self, event):            # ConEditorFrame(GenConEditorFrame)
        self._grid.OnPopupCopy(event)

    #------------------
    def OnPopupPaste(self, event):        # ConEditorFrame(GenConEditorFrame)
        self._grid.OnPopupPaste(event)
        self.RefreshWindow()

    #------------------
    def OnGridCellChanged(self, event):            # ConEditorFrame (GenConEditorFrame)
        self._grid.OnGridCellChanged(event)
        self.RefreshWindow()

    #------------------
    def OnPopupInsertCon(self, event):            # ConEditorFrame
        self.Datasource.Rows.insert(self._grid.clickedRow, Convention())
        self.EditConSeries()    # clickedRow is set by the RMB clicked event that must have preceeded this.
        self.RefreshWindow()

    # ------------------
    def OnPopupDeleteCon(self, event):            # ConEditorFrame
        ret=wx.MessageBox(f"This will delete {self.Datasource.Rows[self._grid.clickedRow].Name} from the list of convention series, but will not delete its directory or files from fanac.org. You must use FTP to do that.", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
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
        oldname=self.Datasource[self._grid.clickedRow][0]
        dlg=wx.TextEntryDialog(None, "Enter the new name of the Convention Series.", "Edit Convention Series name", value=oldname)
        if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
            return
        newname=dlg.GetValue()
        if newname != oldname:
            # Make sure newname isn't already on the list
            for row in self.Datasource.Rows:
                if newname == row.Name:
                    wx.MessageBox("That is a duplicate convention name.", "Duplicate Con Name")
                    return
            self.Datasource[self._grid.clickedRow][0]=newname
            self.RefreshWindow()
            FTP().SetDirectory("/")
            FTP().Rename(oldname, newname)
            self.Upload()

    # ------------------
    def OnTopTextUpdated(self, event):        # ConEditorFrame(GenConEditorFrame)
        self.Datasource.toptext=self.m_textCtrlTopText.GetValue()
        self.RefreshWindow()

    # ------------------
    def OnClose(self, event):            # ConEditorFrame
        if OnCloseHandling(event, self.NeedsSaving(), "The main con list has been updated and not yet saved. Exit anyway?"):
            return

        # Save the window's position
        pos=self.GetPosition()
        Settings().Put("Top Level Window Position", (pos.x, pos.y))

        self.Destroy()

        LogFlush()
        sys.exit(1)


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")

if not os.path.exists("FTP Credentials.json"):
    MessageBox("Unable to find file 'FTP Credentials.json' file.", ignoredebugger=True)
    exit(0)

f=FTP()

if not f.OpenConnection("FTP Credentials.json"):
    MessageBox("Unable to open connection to FTP server fanac.org", ignoredebugger=True)
    Log("Main: OpenConnection('FTP Credentials.json' failed")
    exit(0)

# Attempt to download the version from the website and confirm that this executable is capable
conEditorVersion=2
v=FTP().GetAsString("version")
if v is None or len(v) == 0:
    Log("Main: GetAsString('version' failed")
    MessageBox("Unable to get version from FTP server fanac.org", ignoredebugger=True)
    exit(0)

Log("CWD="+os.getcwd())

vi=Int(v)
if vi > conEditorVersion:
    Log("Main: Obsolete ConEditor version!  fanac.org/conpubs is version "+str(vi)+" while this app is version "+str(conEditorVersion))
    MessageBox("Obsolete ConEditor version!  fanac.org/conpubs is version "+str(vi)+" while this app is version "+str(conEditorVersion), ignoredebugger=True)
    exit(0)
Log("Website version="+str(vi))

# Load the global settings dictionary
Settings().Load("ConEditor settings.json")

with open("FTP Credentials.json") as f:
    UpdateLog().Init(json.loads(f.read())["ID"])

UpdateLog().LogText("-----------------------------------------------------------------------\nConEditor starting.")
LogFlush()

app=wx.App(False)
frame=ConEditorFrame(None)

app.MainLoop()
Log("Exit mainloop")
pass


