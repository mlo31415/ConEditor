from __future__ import annotations

import os
import sys
import wx
import wx.grid
import json
import html
from datetime import datetime

from GenConEditorFrame import GenConEditorFrame
from WxDataGrid import DataGrid, GridDataSource, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable
from ConSeriesFrame import ConSeriesFrame
from ConInstanceFrame import SetHeaderLogo
from ConInstanceDeltaTracker import UpdateFTPLog
from FTP import FTP
from Settings import Settings

from HelpersPackage import SubstituteHTML, FindBracketedText2, FormatLink, Int, MessageBox, PyiResourcePath, FindLinkInString
from WxHelpers import ModalDialogManager, OnCloseHandling3, ProgressMessage2
from Log import LogOpen, Log, LogFlush, LogSetTimestamping



def main():
    print("Starting main()")
    # Start the GUI and run the event loop
    LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")

    if not os.path.exists("FTP Credentials.json"):
        msg=f"Unable to find file 'FTP Credentials.json' file.  Expected to find it in {os.getcwd()}"
        MessageBox(msg, ignoredebugger=True)
        Log(msg)
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
    LogSetTimestamping(True)

    vi=Int(v)
    if vi > conEditorVersion:
        Log("Main: Obsolete ConEditor version!  fanac.org/conpubs is version "+str(vi)+" while this app is version "+str(conEditorVersion))
        MessageBox("Obsolete ConEditor version!  fanac.org/conpubs is version "+str(vi)+" while this app is version "+str(conEditorVersion), ignoredebugger=True)
        exit(0)
    Log("Website version="+str(vi))

    # Load the global settings dictionary
    Settings().Load("ConEditor settings.json")

    # Load the PDF page-header logo once. It is stamped onto uploaded PDFs' headers (see
    # ConInstanceFrame). A missing or unreadable file is non-fatal -- headers simply carry no logo.
    try:
        with open(PyiResourcePath("Fanac logo for pdf headers.jpg"), "rb") as f:
            SetHeaderLogo(f.read())
    except Exception as e:
        Log(f"Main: could not load 'Fanac logo for pdf headers.jpg'; PDF headers will have no logo: {e}")

    with open("FTP Credentials.json") as f:
        UpdateFTPLog.Init(json.loads(f.read())["ID"], "/updatelog.txt")

    UpdateFTPLog.LogText("-----------------------------------------------------------------------\nConEditor starting.")
    LogFlush()

    app=wx.App(False)
    frame=ConEditorFrame(None)      # Required. Frame need not ever be used, but must exist.

    app.MainLoop()



class Convention(GridDataRowClass):
    def __init__(self, Name: str="", URL: str="") -> None:
        self._name: str=""      # The name of the convention series
        self._URL: str=""       # The location of the convention series html page relative to the main cons page; empty if no series page exists yet
        self.Name=Name
        self.URL=URL

    def __hash__(self) -> int:
        s=hash(self._name.strip()+self._URL.strip())
        return s
    def Signature(self) -> int:
        return self.__hash__()

    # Get or set a value by name or column number
    def __getitem__(self, index: str|int|slice) -> str|int:     
        # (Could use return eval("self."+name))
        if index == "Convention" or index == 0:
            return self._name
        return "Convention.Val can't interpret '"+str(index)+"'"

    def __setitem__(self, nameOrCol: str|int|slice, value: ColDefinition|str) -> None:
        # (Could use return eval("self."+name))
        if isinstance(value, slice):
            raise KeyError(f"Convention.SetVal didn't really mean to allow slices")
        if isinstance(value, ColDefinition):
            value=value.Name
        if nameOrCol == "Convention" or nameOrCol == 0:
            self._name=value
            return
        raise KeyError(f"Convention.SetVal can't interpret '{nameOrCol}'")

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

    @property
    def IsEmptyRow(self) -> bool:
        return self._name == "" and self._URL == ""



class ConList(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList =ColDefinitionsList([
            ColDefinition("Convention Series", Type="url", IsEditable=IsEditable.No)
            ])    # There's only one column!
        self._gridDataRowClass: Convention=Convention()
        self._conlist: list[Convention]=[]  # This supplies the Rows property that GridDataSource needs



    def __hash__(self) -> int:
        return sum([hash(x)*(i+1) for i, x in enumerate(self._conlist)])+hash(self._colDefs)
    def Signature(self) -> int:
        return self.__hash__()

    @property
    def ColDefs(self) -> ColDefinitionsList:
        return self._colDefs

    @property
    def NumRows(self) -> int:
        return len(self._conlist)

    def __getitem__(self, index: int) -> Convention:
        assert index != -1
        return self.Rows[index]

    def __setitem__(self, index: int, val: Convention) -> None:
        assert index != -1
        self.Rows[index]=val

    @property
    def Rows(self) -> list:
        return self._conlist
    @Rows.setter
    def Rows(self, rows: list) -> None:
        self._conlist=rows


    def InsertEmptyRows(self, index: int, num: int=1) -> None:
        if num <= 0:
            return
        if index > len(self.Rows):
            index=len(self.Rows)
        self.Rows=self.Rows[:index]+[Convention() for _ in range(num)]+self.Rows[index:]



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

        # Position the window on the screen it was on before.
        # If that position is now off all connected screens (e.g. a monitor was unplugged),
        # centre on the primary display instead.
        tlwp=Settings().Get("Top Level Window Position")
        if tlwp:
            self.SetPosition(tlwp)
            pos=wx.Point(*tlwp)
            on_screen=any(wx.Display(i).GetGeometry().Contains(pos)
                          for i in range(wx.Display.GetCount()))
            if not on_screen:
                self.Centre()

        self.DownloadMainConlist()
        self.MarkAsSaved()
        self.Show()


    @property
    def Datasource(self) -> ConList:        
        return self._Datasource
    @Datasource.setter
    def Datasource(self, val: ConList):
        self._Datasource: ConList=val
        self._grid.Datasource=val

    # ----------------------------------------------
    # Used to determine if anything has been updated
    def __hash__(self) -> int:
        s=self.Datasource.Signature()+hash(self.m_textCtrlTopText.GetValue().strip())
        return s
    def Signature(self) -> int:
        return self.__hash__()


    def MarkAsSaved(self):        
        self._signature=self.Signature()
        self.UpdateNeedsSavingFlag()


    def NeedsSaving(self) -> bool:        
        v=self._signature != self.Signature()
        self.UpdateNeedsSavingFlag()
        return v


    def UpdateNeedsSavingFlag(self):        
        s=self.Title.removesuffix(" *")  # Remove existing Needs Saving marker, if any
        if self.Signature() != self._signature:
            s=s+" *"
        self.Title=s


    # ------------------
    def DownloadMainConlist(self):            
        # Clear out any old information
        self.Datasource=ConList()

        Log("Loading root/index.html")
        file=FTP().GetFileAsString("", "index.html")
        if file is None:
            # Present an empty grid
            self.RefreshWindow()
            return

        table, _=FindBracketedText2(file, "fanac-table", caseInsensitive=True)

        # Read every convention link inside the table, in document order. This handles both the old
        # single-column <table> layout and the new 3-column Bootstrap layout; non-link content (the
        # divider) has no <a> and is naturally skipped. The divider is re-synthesized on upload.
        rows:list[Convention]=[]
        rest=table
        while True:
            a, rest=FindBracketedText2(rest, "a", caseInsensitive=True, includeBrackets=True)
            if a == "":
                break
            _, link, text, _=FindLinkInString(a)
            if link == "":
                continue
            # Unescape both: FormatLink HTML-escapes the name and the href (e.g. '&'->'&amp;') on write, so
            # reversing it here keeps a con whose name contains '&' from drifting on the next upload. Percent
            # encoding in the href (e.g. "%20") is left untouched.
            rows.append(Convention(html.unescape(text.strip()), html.unescape(link)))

        if len(rows) > 0:
            self.Datasource.Rows=rows


        self._grid.MakeTextLinesEditable()
        self.RefreshWindow()
        self.MarkAsSaved()



    @property
    def Title(self) -> str:        
        return self.GetTitle()
    @Title.setter
    def Title(self, val) -> None:
        self.SetTitle(val)


    #------------------
    def OnButtonUploadClick(self, event):            
        self.UploadMainConlist()


    #------------------
    def UploadMainConlist(self) -> bool:

        with ModalDialogManager(ProgressMessage2, "Uploading index.html to fanac.org/conpubs", parent=self) as pm:
            # First read in the template
            file=None
            try:
                with open(PyiResourcePath("Template-ConMain.html"), encoding='utf-8') as f:
                    file=f.read()
            except Exception:
                wx.MessageBox("Can't read 'Template-ConMain.html'")

            # We want to do substitutions, replacing whatever is there now with the new data
            # The con's name might be tagged with <fanac-instance>, the random text with "fanac-headertext"
            file=SubstituteHTML(file, "title", "SF Convention Publications and Documents")
            file=file.replace("fanac-meta-title", "SF Convention Publications and Documents — fanac.org")
            file=SubstituteHTML(file, "fanac-stuff", self.m_textCtrlTopText.GetValue())

            # Render the whole list as a single multi-column list. CSS in Template-ConMain.html (the .conlist
            # rules) balances it into 3 / 2 / 1 equal columns as the screen narrows, filling column-major so
            # the first third stays in the left column. The divider <hr> sits inline after the grouping rows.
            newtable='  <ul class="list-unstyled conlist">\n'
            for i, row in enumerate(self.Datasource.Rows):
                if i == 4:      # the divider falls between items 3 (Misc. Cons) and 4 (1st real con)
                    newtable+='    <li><hr></li>\n'
                newtable+=f'    <li>{FormatLink(row.URL, row.Name)}</li>\n'
            newtable+='  </ul>\n'

            # Substitute the table into the template
            file=SubstituteHTML(file, "fanac-table", newtable)

            file=SubstituteHTML(file, "fanac-date", datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST")

            # Copyright terminal year: replace the template's tagged "26" with the current 2-digit year.
            file=SubstituteHTML(file, "fanac-copyright", datetime.now().strftime("%y"))

            Log("Uploading /index.html")
            # Save the old file as a backup.
            if not FTP().BackupServerFile(f"/index.html"):
                Log(f"Could not back up server file /index.html")
                return False

            if not FTP().PutFileAsString("/", "index.html", file):
                Log("Upload of /index.html failed")
                wx.MessageBox("Upload of /index.html failed")
                return False

            UpdateFTPLog.LogText("Uploaded Main convention list")
            pm.Update("Upload succeeded.", delay=0.5)

        self.MarkAsSaved()
        self.RefreshWindow()
        return True

    #------------------
    def RefreshWindow(self) -> None:        
        self._grid.RefreshWxGridFromDatasource()
        self.UpdateNeedsSavingFlag()

    #------------------
    def OnButtonSortClick(self, event):            
        # Worldcon sorts ahead of everything else; Then "Early Conventions"; Then all other conventions; Finally empty lines after everything else
        def sorter(c: Convention) -> str:
            n=c.Name.upper()        # Convert to all UC so that sort is case-insensitive
            if n == "WORLDCON":
                return " 0"
            if n == "EARLY CONVENTIONS":
                return " 1"
            if n == "ONESIE CONVENTIONS":
                return " 2"
            if n == "MISC. CONVENTIONS":
                return " 3"
            if len(n.strip()) == 0:
                return "ZZZZZZZZZ"      # This should sort last
            return n
        self.Datasource.Rows=sorted(self.Datasource.Rows, key=sorter)
        self.RefreshWindow()

    #------------------
    def OnButtonExitClick(self, event):            
        self.OnClose(event)

    #------------------
    def OnGridCellRightClick(self, event):            
        self._grid.OnGridCellRightClick(event, self.m_GridPopup)  # Set enabled state of default items; set all others to False

        self.m_popupItemInsertConventionSeries.Enabled=True
        if self._grid.clickedRow < self.Datasource.NumRows:
            self.m_popupItemDeleteConventionSeries.Enabled=True
            self.m_popupItemEdit.Enabled=True
            self.m_popupRename.Enabled=True
        self.m_popupItemInsertConventionSeries.Enabled=True
        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)

    # ------------------
    def OnGridEditorShown(self, event):        
        self._grid.OnGridEditorShown(event)

    # ------------------
    def OnGridCellDoubleClick(self, event):            
        self._grid.OnGridCellDoubleClick(event)
        if event.GetRow() > self.Datasource.NumRows:
            return      # For now, we do nothing when you double-click in an empty cell

        self.EditConSeries()

    # ------------------
    def EditConSeries(self, IsNewSeries: bool=False):
        if self._grid.clickedRow >= self.Datasource.NumRows:
            self.Datasource.Rows.insert(self._grid.clickedRow, Convention())
            self.RefreshWindow()
        conseriesname=self.Datasource[self._grid.clickedRow][0]
        Log(f"EditConSeries: {conseriesname=}", Flush=True)
        # Create list of con series required by the con series editor
        conserieslist=[row.Name for row in self.Datasource.Rows]
        with ModalDialogManager(ConSeriesFrame, self._baseDirFTP, conseriesname, conserieslist) as dlg:
            if len(dlg.Seriesname.strip()) == 0:  # If the user didn't supply a con series name, we exit and don't show the dialog
                return

            dlg._isNewSeriesPage=IsNewSeries        # This will prevent attempt to back up non-existent current series file

            Log(f"EditConSeries: about to dlg.ShowModal()", Flush=True)
            if dlg.ShowModal() == wx.OK:
                conseriesname=dlg.tConSeries.GetValue()
                self.Datasource.Rows[self._grid.clickedRow].URL="./"+conseriesname+"/index.html"
                self.Datasource.Rows[self._grid.clickedRow].Name=conseriesname



    #-------------------
    def OnKeyDown(self, event):            
        self._grid.OnKeyDown(event)
        self.UpdateNeedsSavingFlag()

    #-------------------
    def OnKeyUp(self, event):            
        self._grid.OnKeyUp(event)

    #------------------
    def OnPopupCopy(self, event):            
        self._grid.OnPopupCopy(event)

    #------------------
    def OnPopupPaste(self, event):        
        self._grid.OnPopupPaste(event)
        self.RefreshWindow()

    #------------------
    def OnGridCellChanged(self, event):
        self._grid.OnGridCellChanged(event)
        self.RefreshWindow()

    #------------------
    def OnPopupInsertConSeries(self, event):            
        self.Datasource.Rows.insert(self._grid.clickedRow, Convention())
        self.EditConSeries(IsNewSeries=True)    # clickedRow is set by the RMB clicked event that must have preceded this.
        self.RefreshWindow()

    # ------------------
    def OnPopupDeleteCon(self, event):            
        ret=wx.MessageBox(f"This will delete {self.Datasource.Rows[self._grid.clickedRow].Name} from the list of convention series, but will not delete its directory or files from fanac.org. You must use FTP to do that.", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
        if ret == wx.OK:
            self._grid.DeleteRows(self._grid.clickedRow, 1)
            self.RefreshWindow()
        event.Skip()

    # ------------------
    def OnPopupEditCon(self, event):            
        self.EditConSeries()    # clickedRow is set by the RMB clicked event that must have preceded this.
        event.Skip()

    # ------------------
    def OnPopupRename(self, event):            
        oldname=self.Datasource[self._grid.clickedRow][0]
        dlg=wx.TextEntryDialog(None, "Enter the new name of the Convention Series.", "Edit Convention Series name", value=oldname)
        if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
            return
        newname=dlg.GetValue()
        dlg.Destroy()
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
            self.UploadMainConlist()

    # ------------------
    def OnTopTextUpdated(self, event):        
        self.Datasource.toptext=self.m_textCtrlTopText.GetValue()
        self.RefreshWindow()

    # ------------------
    def OnClose(self, event):
        choice=OnCloseHandling3(event, self.NeedsSaving(), "The main con list has been changed but not yet uploaded.")
        if choice == "cancel":
            return
        if choice == "upload" and not self.UploadMainConlist():
            return                          # upload failed -- keep the window open so the changes aren't lost

        # Save the window's position
        pos=self.GetPosition()
        Settings().Put("Top Level Window Position", (pos.x, pos.y))

        self.Destroy()





if __name__ == "__main__":
    main()