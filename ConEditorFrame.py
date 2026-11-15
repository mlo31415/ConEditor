from __future__ import annotations

import os
import sys
import re
import wx
import wx.grid
import json
import html
from datetime import datetime

from GenConEditorFrame import GenConEditorFrame
from WxDataGrid import DataGrid, GridDataSource, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable
from ConSeriesFrame import ConSeriesFrame, CSP_FORMAT_VERSION
from ConInstanceFrame import SetHeaderLogo, PDF_HEADER_VERSION, CIP_FORMAT_VERSION
from ConInstance import IsTestSeries
from ConInstanceDeltaTracker import UpdateFTPLog
from FTP import FTP
from Settings import Settings

from HelpersPackage import SubstituteHTML, FindBracketedText2, FormatLink, Int, Int0, MessageBox, PyiResourcePath, FindLinkInString
from WxHelpers import ModalDialogManager, OnCloseHandling3, ProgressMessage2, SetWindowIcon, RestoreWindowPlacement
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
        Log(f"Main: could not load 'Fanac logo for pdf headers.jpg'; PDF headers will have no logo: {e}", isError=True)

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
        # Roll-up "bring up to date" marker for this whole series: the (CSP format, CIP format, PDF header)
        # versions it was last fully verified at. Stored on the main page as a hidden "<!--d=csp.cip.pdf-->"
        # so a site-wide run can skip a finished series without opening its series page. 0 = never verified.
        self._doneCspVersion: int=0
        self._doneCipVersion: int=0
        self._donePdfVersion: int=0
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

    # The (CSP format, CIP format, PDF header) versions this whole series was last fully brought up to. 0 = never.
    @property
    def DoneCspVersion(self) -> int:
        return self._doneCspVersion
    @DoneCspVersion.setter
    def DoneCspVersion(self, val: int) -> None:
        self._doneCspVersion=int(val)

    @property
    def DoneCipVersion(self) -> int:
        return self._doneCipVersion
    @DoneCipVersion.setter
    def DoneCipVersion(self, val: int) -> None:
        self._doneCipVersion=int(val)

    @property
    def DonePdfVersion(self) -> int:
        return self._donePdfVersion
    @DonePdfVersion.setter
    def DonePdfVersion(self, val: int) -> None:
        self._donePdfVersion=int(val)

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
        SetWindowIcon(self, PyiResourcePath("ConEditor.ico"))   # title-bar/taskbar icon (bundled in the exe via the .spec)

        # Class instance variables associated with RMB actions, etc.
        self.userSelection=None

        self._baseDirFTP: str=""

        self._signature=0

        self._grid: DataGrid=DataGrid(self.gRowGrid, ColorSingleCellByValue=self._TintTestSeriesRow)
        self.Datasource=ConList()

        self._grid.HideRowLabels()

        # "Bring everything up to date" RMB item: bring the WHOLE SITE up to date -- every series, its conventions,
        # their sub-pages and PDFs -- skipping anything already current. Added in code rather than in the generated
        # GenConEditorFrame.py. A site-wide action, so it is always available.
        self.m_popupBringEverythingUpToDate=wx.MenuItem(self.m_GridPopup, wx.ID_ANY, "Bring everything up to date", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_GridPopup.Append(self.m_popupBringEverythingUpToDate)
        self.Bind(wx.EVT_MENU, self.OnPopupBringEverythingUpToDate, id=self.m_popupBringEverythingUpToDate.GetId())

        # Position the window on the screen it was on before.
        # If that position is now off all connected screens (e.g. a monitor was unplugged),
        # centre on the primary display instead.
        RestoreWindowPlacement(self, Settings().Get("Top Level Window Position"), None)

        self.DownloadMainConlist()
        self.MarkAsSaved()
        self.Show()


    #------------------
    # Show test series (hidden on the web page) in grey. The grid calls this per cell after its own
    # coloring -- note the (icol, irow) argument order.
    def _TintTestSeriesRow(self, icol: int, irow: int) -> None:
        if irow >= self.Datasource.NumRows:
            return
        if IsTestSeries(self.Datasource.Rows[irow].Name):
            self._grid.SetCellBackgroundColor(irow, icol, wx.Colour(225, 225, 225))


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
        # Read the root index by absolute path: an empty directory means "stay in the current FTP directory",
        # which after any series navigation (e.g. BringEverythingUpToDate) is left deep inside a series folder.
        file=FTP().GetFileAsString("/", "index.html")
        if file is None:
            # Present an empty grid
            self.RefreshWindow()
            return

        table, _=FindBracketedText2(file, "fanac-table", caseInsensitive=True)

        # Each series is an <li> holding a link, in document order (a divider is <li><hr></li> with no link and
        # is skipped). A hidden "<!--d=csp.cip.pdf-->" in the <li> records how far that whole series was brought
        # up to date; the divider is re-synthesized on upload.
        rows:list[Convention]=[]
        for m in re.finditer(r"<li\b[^>]*>(.*?)</li>", table, flags=re.DOTALL|re.IGNORECASE):
            li=m.group(1)
            a, _=FindBracketedText2(li, "a", caseInsensitive=True, includeBrackets=True)
            if a == "":
                continue
            _, link, text, _=FindLinkInString(a)
            if link == "":
                continue
            # Unescape both: FormatLink HTML-escapes the name and the href (e.g. '&'->'&amp;') on write, so
            # reversing it here keeps a con whose name contains '&' from drifting on the next upload. Percent
            # encoding in the href (e.g. "%20") is left untouched.
            conv=Convention(html.unescape(text.strip()), html.unescape(link))
            md=re.search(r"<!--d=(\d+)\.(\d+)\.(\d+)-->", li)
            if md is not None:
                conv.DoneCspVersion=Int0(md.group(1))
                conv.DoneCipVersion=Int0(md.group(2))
                conv.DonePdfVersion=Int0(md.group(3))
            rows.append(conv)

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
                # Two dividers: one after Worldcon (item 0), which stands alone, and one after the
                # Early/Onesie/Misc. grouping (items 1-3), before the first alphabetical con (item 4).
                if i == 1 or i == 4:
                    newtable+='    <li><hr></li>\n'
                # A test series is written hidden: still on the page (so CE and the other tools find it) but not displayed
                hidden=" hidden" if IsTestSeries(row.Name) else ""
                # Hidden roll-up marker: how far this whole series has been brought up to date (invisible; lets
                # a site-wide run skip a finished series without opening its series page).
                mark=f"<!--d={row.DoneCspVersion}.{row.DoneCipVersion}.{row.DonePdfVersion}-->" if (row.DoneCspVersion or row.DoneCipVersion or row.DonePdfVersion) else ""
                newtable+=f'    <li{hidden}>{mark}{FormatLink(row.URL, row.Name)}</li>\n'
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
    # Bring the whole site up to date. For each series: skip it when the main-page marker already shows the whole
    # series current at the current (CSP, CIP, PDF) versions -- no series-page download; otherwise open it (its
    # window is never shown), bring it up to date (its cons, their PDFs and sub-pages, re-stamping only what is
    # behind), and -- only if that all succeeded -- record the series' marker and re-upload the main page, so a
    # later run resumes cheaply. Returns a list of what could not be done (empty if all OK).
    def BringEverythingUpToDate(self) -> list[str]:
        problems: list[str]=[]
        serieslist=[r.Name for r in self.Datasource.Rows]
        for conv in list(self.Datasource.Rows):
            if not conv.Name.strip() or not conv.URL.strip():
                continue    # a blank row, or a series with no page yet
            if (conv.DoneCspVersion >= CSP_FORMAT_VERSION and conv.DoneCipVersion >= CIP_FORMAT_VERSION
                    and conv.DonePdfVersion >= PDF_HEADER_VERSION):
                continue    # the whole series is already current -- skip it without opening its page
            frame=ConSeriesFrame(self._baseDirFTP, conv.Name, serieslist, show=False)
            try:
                if not frame._loadedFromServer:
                    problems.append(f"The series '{conv.Name}' could not be read, so it was not updated.")
                    continue
                serProblems=frame.BringSeriesUpToDate()
            finally:
                frame.Destroy()
            problems.extend(serProblems)
            if not serProblems:
                # The whole series is now current: record it and save the main page so this is not redone.
                conv.DoneCspVersion=CSP_FORMAT_VERSION
                conv.DoneCipVersion=CIP_FORMAT_VERSION
                conv.DonePdfVersion=PDF_HEADER_VERSION
                self.UploadMainConlist()
        return problems

    #------------------
    # RMB "Bring everything up to date": the whole-site counterpart to the con-series page's per-con and whole-series
    # items. Confirms (with a do-not-interrupt warning), then runs BringEverythingUpToDate -- which skips any series
    # already current, so re-running is cheap -- and reports the outcome.
    def OnPopupBringEverythingUpToDate(self, event):
        msg=("Bring the WHOLE SITE up to date?\n\n"
             "Every convention series will be checked, and any out-of-date PDF headers, pages and sub-pages "
             "re-stamped and regenerated. Anything already current is skipped, but the first full pass over the "
             "whole site can take a long time.\n\n"
             "Once it has started it must run to the end. Until ConEditor says it has finished, do NOT close "
             "ConEditor, let the computer sleep, or disconnect from the network.")
        if wx.MessageBox(msg, "Bring everything up to date", wx.OK|wx.CANCEL|wx.CANCEL_DEFAULT|wx.ICON_WARNING) != wx.OK:
            return

        problems=self.BringEverythingUpToDate()
        self.RefreshWindow()

        if problems:
            for p in problems:
                Log(f"Bring everything up to date: {p}", isError=True)
            wx.MessageBox("Finished, but some things could not be updated:\n\n    "+"\n    ".join(problems),
                          "Bring everything up to date", wx.OK|wx.ICON_ERROR)
        else:
            wx.MessageBox("Finished. The whole site is up to date.", "Bring everything up to date", wx.OK|wx.ICON_INFORMATION)

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
        self.m_popupBringEverythingUpToDate.Enabled=True        # a site-wide action; always available
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
        irow=self._grid.clickedRow
        rollSeries=(0, 0, 0)
        cspUploaded=False
        with ModalDialogManager(ConSeriesFrame, self._baseDirFTP, conseriesname, conserieslist) as dlg:
            if len(dlg.Seriesname.strip()) == 0:  # If the user didn't supply a con series name, we exit and don't show the dialog
                return

            dlg._isNewSeriesPage=IsNewSeries        # This will prevent attempt to back up non-existent current series file

            Log(f"EditConSeries: about to dlg.ShowModal()", Flush=True)
            if dlg.ShowModal() == wx.OK:
                conseriesname=dlg.tConSeries.GetValue()
                self.Datasource.Rows[irow].URL="./"+conseriesname+"/index.html"
                self.Datasource.Rows[irow].Name=conseriesname
                # Roll-up happens ONLY when the user explicitly uploaded the series page -- never from browsing.
                # If it was uploaded and every con in it now carries a current marker, the whole series is current;
                # record that on the main con list and persist it, so a later site-wide run can skip the series.
                cspUploaded=dlg._uploaded
                rollSeries=dlg.SeriesRollupDoneVersions()

        # Raise-only: never lowers an existing marker.
        rollCsp, rollCip, rollPdf=rollSeries
        row=self.Datasource.Rows[irow]
        if cspUploaded and rollCsp and (row.DoneCspVersion < rollCsp or row.DoneCipVersion < rollCip or row.DonePdfVersion < rollPdf):
            row.DoneCspVersion=rollCsp
            row.DoneCipVersion=rollCip
            row.DonePdfVersion=rollPdf
            self.UploadMainConlist()



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
    # Rename a convention series: its directory on the server, its line on this list (the name and the link),
    # and everything inside it that carries its location -- the series page, each convention's page and
    # sub-pages, and the header stamped in each PDF (which links to the convention's page). Cross-links to the
    # series from other series are not changed.
    # Because every PDF has to be downloaded and uploaded again, this can be a long job that must not be
    # interrupted, so the series is measured first and the user is told its size and warned before it starts.
    def OnPopupRename(self, event):
        irow=self._grid.clickedRow
        oldname=self.Datasource[irow][0]
        with wx.TextEntryDialog(None, "Enter the new name of the Convention Series.", "Edit Convention Series name", value=oldname) as dlg:     # (with: destroyed on Cancel, too)
            if dlg.ShowModal() != wx.ID_OK or len(dlg.GetValue().strip()) == 0:
                return
            newname=dlg.GetValue().strip()
        if newname == oldname:
            return
        if "/" in newname:
            wx.MessageBox("A convention series name can't contain a '/'.", "Can't rename")
            return
        # Make sure newname isn't already on the list
        for row in self.Datasource.Rows:
            if newname == row.Name:
                wx.MessageBox("That is a duplicate convention name.", "Duplicate Con Name")
                return

        # The new name must be free on the server. And is there a series page to work from?
        with ModalDialogManager(ProgressMessage2, f"Checking '{oldname}' on the server", parent=self) as pm:
            taken=not FTP().SetDirectory("/") or FTP().FileExists(newname)
            hasPage=not taken and FTP().FileExists(f"/{oldname}/index.html")
        if taken:
            wx.MessageBox(f"There is already a directory named '{newname}' on the server (or the server could not be reached), "
                          f"so nothing was changed.", "Can't rename", wx.OK|wx.ICON_ERROR)
            return

        # Load the series into a series window that is never shown: it does the work on the series' pages.
        frame=None
        if hasPage:
            frame=ConSeriesFrame(self._baseDirFTP, oldname, [row.Name for row in self.Datasource.Rows], show=False)
        try:
            if frame is not None and not frame._loadedFromServer:
                wx.MessageBox(f"The '{oldname}' series page could not be read, so nothing was changed. Try again.", "Can't rename", wx.OK|wx.ICON_ERROR)
                return

            # Measure the job and tell the user what they are about to start. Nothing has been changed yet.
            msg=(f"Renaming '{oldname}' as '{newname}' will:\n\n"
                 f"    • rename the series' directory on the server\n"
                 f"    • update and upload the main convention list\n")
            if frame is not None:
                survey=frame.SurveyForRegeneration()
                msg+=(f"    • regenerate the series page, {survey['cons']} convention page(s) and {survey['subpages']} sub-page(s)\n"
                      f"    • download, re-stamp and upload again {survey['pdfs']} PDF(s) -- {survey['mb']:,.0f} MB -- so that the "
                      f"header in each links to the new location\n")
                if survey["unreadable"]:
                    msg+=(f"\n{len(survey['unreadable'])} page(s) could not be read. They and their PDFs will be left as they are:\n    "+
                          "\n    ".join(survey["unreadable"][:10])+("\n    ..." if len(survey["unreadable"]) > 10 else "")+"\n")
                # A floor for the time: about three server round trips for each page and two for each PDF, at the
                # speed the survey just measured. Moving the PDFs' contents comes on top of that.
                minutes=max(1, round((3*(survey["cons"]+survey["subpages"])+2*survey["pdfs"])*survey["secondsPerPage"]/60))
                msg+=(f"\nExpect this to take at least {minutes} minute(s), plus the time it takes to move {survey['mb']:,.0f} MB "
                      f"in each direction.\n")
            msg+=("\nOnce it has started it must run to the end. Until ConEditor says that the rename has finished, do NOT close "
                  "ConEditor, do NOT let the computer sleep or shut down, and do NOT disconnect from the network.\n\n"
                  "Start the rename?")
            if wx.MessageBox(msg, "Rename a convention series", wx.OK|wx.CANCEL|wx.CANCEL_DEFAULT|wx.ICON_WARNING) != wx.OK:
                return

            # Rename the series' directory on the server. Nothing else is changed unless that succeeds.
            with ModalDialogManager(ProgressMessage2, f"Renaming '{oldname}' as '{newname}' on the server", parent=self) as pm:
                renamed=FTP().SetDirectory("/") and FTP().Rename(oldname, newname)
            if not renamed:
                Log(f"OnPopupRename: could not rename directory '{oldname}' as '{newname}'", isError=True)
                wx.MessageBox(f"Could not rename the directory '{oldname}' as '{newname}' on the server, so nothing was changed.",
                              "Rename failed", wx.OK|wx.ICON_ERROR)
                return

            # The directory now has its new name. Update this list (the name and the link) and upload it at once,
            # because the main page is what links to the directory.
            self.Datasource.Rows[irow].Name=newname
            self.Datasource.Rows[irow].URL="./"+newname+"/index.html"
            self.RefreshWindow()
            problems: list[str]=[]
            if not self.UploadMainConlist():
                problems.append("The main convention list could not be uploaded. Upload it, so that the main page links to the renamed series.")

            # Now everything inside the series that carries its location: each convention's page, its sub-pages
            # and PDFs, and finally the series page itself (uploaded last, inside this call, so it carries the
            # new name and the refreshed progress markers).
            if frame is not None:
                frame.Seriesname=newname
                problems.extend(frame.RegenerateConPagesAndPdfHeaders())
        finally:
            if frame is not None:
                frame.Destroy()

        # The user was told to wait for this.
        if problems:
            for problem in problems:
                Log(f"OnPopupRename ('{oldname}' as '{newname}'): {problem}", isError=True)
            wx.MessageBox(f"The rename of '{oldname}' as '{newname}' has finished, but not everything was updated:\n\n"+
                          "\n".join(problems[:25])+(f"\n... and {len(problems)-25} more (all are in the error log)" if len(problems) > 25 else ""),
                          "Rename finished, with problems", wx.OK|wx.ICON_WARNING)
        else:
            wx.MessageBox(f"The rename of '{oldname}' as '{newname}' has finished.", "Rename finished", wx.OK|wx.ICON_INFORMATION)

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