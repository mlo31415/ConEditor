from __future__ import annotations

import os
import re
import shutil
import tempfile
from urllib.parse import quote

from WxHelpers import wxMessageBox
import wx
import wx.grid

from GenConInstanceFrame import GenConInstanceFrame
from WxDataGrid import DataGrid, Color, IsEditable
from ConInstance import ConInstanceDatasource, ConInstanceRow, ConInstance
from ConInstanceDeltaTracker import ConInstanceDeltaTracker, UpdateFTPLog
from FTP import FTP
from Settings import Settings
from Log import Log, LogError
from HelpersPackage import WikiPagenameToWikiUrlname, ExtensionMatches, RemoveAccents
from PDFHelpers import GetPdfPageCount, AddStdMetadata, AddPdfPageHeader
from WxHelpers import OnCloseHandling, ModalDialogManager, ProgressMessage2, MessageBoxInput


# The FANAC logo stamped onto uploaded PDFs' page headers. Loaded once at startup (see main() in
# ConEditorFrame) and held here as raw image bytes; None means no logo (file missing or unreadable).
_g_headerLogo: bytes|None=None

def SetHeaderLogo(data: bytes|None) -> None:
    global _g_headerLogo
    _g_headerLogo=data


# Draws a grid cell with the system folder icon to the left of its text -- used on the Display Name cell
# of a sub-page (SP) row so it reads like a folder. Data-safe: it only changes how the cell is painted,
# never the stored value. Falls back to plain text if the icon can't be loaded.
class _SubPageCellRenderer(wx.grid.GridCellRenderer):
    _bmp=None
    @classmethod
    def _Bitmap(cls):
        if cls._bmp is None:
            cls._bmp=wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_MENU, wx.Size(16, 16))
        return cls._bmp

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        bg=grid.GetSelectionBackground() if isSelected else attr.GetBackgroundColour()
        dc.SetBrush(wx.Brush(bg)); dc.SetPen(wx.TRANSPARENT_PEN); dc.DrawRectangle(rect)
        x=rect.x+2
        bmp=self._Bitmap()
        if bmp is not None and bmp.IsOk():
            dc.DrawBitmap(bmp, x, rect.y+(rect.height-bmp.GetHeight())//2, True)
            x+=bmp.GetWidth()+3
        dc.SetFont(attr.GetFont())
        dc.SetTextForeground(grid.GetSelectionForeground() if isSelected else attr.GetTextColour())
        dc.SetClippingRegion(rect)
        text=grid.GetCellValue(row, col)
        _, th=dc.GetTextExtent(text)
        dc.DrawText(text, x, rect.y+(rect.height-th)//2)
        dc.DestroyClippingRegion()

    def GetBestSize(self, grid, attr, dc, row, col):
        dc.SetFont(attr.GetFont())
        tw, th=dc.GetTextExtent(grid.GetCellValue(row, col))
        return wx.Size(tw+24, max(th, 18))

    def Clone(self):
        return _SubPageCellRenderer()


# Derive the document title used in the PDF header and metadata from the con-instance link text.
# Strips the file extension and expands fannish abbreviations ("PR 5" -> "Progress Report 5",
# "PB 5" -> "Program Book 5"). The con-instance page's link text itself is left unchanged.
def _CleanTitle(display_title: str) -> str:
    t=display_title.strip().removesuffix(".pdf").removesuffix(".PDF")
    # Expand the fannish abbreviations "PR"/"pr" -> "Progress Report" and "PB"/"pb" -> "Program Book".
    # Match a standalone PR/PB token (any case) whether or not a number follows and regardless of the
    # spacing: "PR 5", "PR5", "pr 5", "pr5" -> "...Report 5"; a bare "PR" -> "Progress Report".
    # The leading \b keeps it from matching inside words (e.g. "expr", "PROGRAM", "Spring").
    t=re.sub(r"\b[Pp][Rr] *(\d+)", r"Progress Report \1", t)   # PR/pr with a number (any spacing)
    t=re.sub(r"\b[Pp][Rr](?![A-Za-z0-9])", "Progress Report", t)   # bare PR/pr (no number)
    t=re.sub(r"\b[Pp][Bb] *(\d+)", r"Program Book \1", t)      # PB/pb with a number (any spacing)
    t=re.sub(r"\b[Pp][Bb](?![A-Za-z0-9])", "Program Book", t)      # bare PB/pb (no number)
    return t


#####################################################################################
class ConInstanceDialogClass(GenConInstanceFrame):

    def __init__(self, basedirFTP: str, seriesname: str, conname: str, prevconname: str= "", nextconname: str= "", Create: bool=False, pm=None,
                 is_subpage: bool=False, rootSeriesName: str="", rootConName: str=""):
        GenConInstanceFrame.__init__(self, None)

        # Sub-page support. When this dialog is editing a sub-page (SP) rather than a con instance, it
        # carries the identity of the owning con (the "root CIP") so the generated page can link back to
        # it; a CIP leaves _isSubPage False and is its own root.
        self._isSubPage=is_subpage
        self._rootSeriesName=rootSeriesName if is_subpage else seriesname
        self._rootConName=rootConName if is_subpage else conname

        self._grid: DataGrid=DataGrid(self.gRowGrid, ColorSingleCellByValue=self._DecorateSubPageCell)
        self.Datasource=ConInstanceDatasource()

        self._grid.HideRowLabels()

        self._FTPbasedir=basedirFTP # The root of the convention's files, e.g., "/seriesName" (for a sub-page, the parent page's full path)
        self._seriesname=seriesname # The name of the series
        self.Conname=conname        # The actual name of the con (or sub-page) directory on conpubs
        self.ConInstanceDates=""    # The con's date(s) (from its row on the con series page); used in the PDF page header. May be empty if unknown.
        self._credits=""

        self._signature=0

        # A list of changes to the file stored on the website which will need to be made upon upload.
        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()

        self._returnMessage=""  # Error message if download failed
        self._uploaded=False    # Has this con instance been successfully uploaded since ut was initialized? (This is needed to generate the return value from the dialog.)
        self._downloaded=False  # Has this con instance been successfully downloaded?
        self._valid=False       # Is this a valid ConInstanceDialogClass?

        self.Datasource.SpecialTextColor=None

        self._downloaded=self.DownloadConInstancePage(pm=pm)
        if not Create and not self._downloaded:
            self._returnMessage=f"Unable to download ConInstance page {self._FTPbasedir}/{self.Conname}/index.html"
            return

        #  Override any existing prev/next with the current prev/next
        self.PrevConInstanceName=prevconname
        self.NextConInstanceName=nextconname

        self._valid=True
        self.SetEscapeId(wx.ID_CANCEL)

        # A sub-page has no Convention name or Fancyclopedia URL of its own to edit -- both are derived
        # from the con instance it descends from -- so hide those two rows. Hide through the containing
        # sizer so the (now fully empty) grid rows collapse rather than leaving a gap.
        if self._isSubPage:
            for ctrl in (self.m_staticText1, self.tConInstanceName, self.m_staticText11, self.tConInstanceFancyURL):
                sizer=ctrl.GetContainingSizer()
                if sizer is not None:
                    sizer.Hide(ctrl)
                else:
                    ctrl.Hide()
            self.Layout()

        self.MarkAsSaved()
        # Log("ConInstanceDialogClass.__init__(): About to refresh window.")
        self.RefreshWindow()
        # Log("ConInstanceDialogClass.__init__(): Window refreshed.")



    @property
    def Datasource(self) -> ConInstanceDatasource:
        return self._Datasource
    @Datasource.setter
    def Datasource(self, val: ConInstanceDatasource):
        self._Datasource=val
        self._grid.Datasource=val


    # ----------------------------------------------
    # Used to determine if anything has been updated
    def __hash__(self) -> int:
        stuff=self.ConInstanceName.strip()+self.ConInstanceTopText.strip()+self.ConInstanceFancyURL.strip()+self.Credits.strip()
        return hash(stuff)+self.Datasource.Signature()
    def Signature(self) -> int:
        return self.__hash__()

    def MarkAsSaved(self) -> None:
        self._signature=self.Signature()


    def NeedsSaving(self) -> bool:
        return self._signature != self.Signature()

    def UpdateNeedsSavingFlag(self) -> None:
        s=self.Title.removesuffix(" *")     # Remove existing Needs Saving marker, if any
        if self.NeedsSaving():
            s=s+" *"
        self.Title=s


    # ----------------------------------------------
    @property
    def Uploaded(self) -> bool:
        return self._uploaded
    @Uploaded.setter
    def Uploaded(self, val: bool) -> None:
        self._uploaded=val

    # ----------------------------------------------
    @property
    def ConInstanceTopText(self) -> str:
        return self.topText.GetValue()

    @ConInstanceTopText.setter
    def ConInstanceTopText(self, val: str) -> None:
        self.topText.SetValue(val)

    # ----------------------------------------------
    @property
    def ConInstanceName(self) -> str:
        return self.tConInstanceName.GetValue()

    @ConInstanceName.setter
    def ConInstanceName(self, val: str) -> None:
        if val != self.tConInstanceName.GetValue():
            self.tConInstanceName.SetValue(val)

    # ----------------------------------------------
    @property
    def Conname(self) -> str:
        return self._conlink.strip()
    @Conname.setter
    def Conname(self, val: str) -> None:
        self._conlink=val

    # ----------------------------------------------
    @property
    def ReturnMessage(self) -> str:
        return self._returnMessage.strip()

    # ----------------------------------------------
    @property
    def Credits(self) -> str:
        return self.tCredits.GetValue()

    @Credits.setter
    def Credits(self, val: str) -> None:
        if val != self.tCredits.GetValue():
            self.tCredits.SetValue(val)

    # ----------------------------------------------
    @property
    def ConInstanceFancyURL(self) -> str:
        return self.tConInstanceFancyURL.GetValue()

    @ConInstanceFancyURL.setter
    def ConInstanceFancyURL(self, val: str) -> None:
        if val != self.tConInstanceFancyURL.GetValue():
            self.tConInstanceFancyURL.SetValue(val)

    # ----------------------------------------------
    def OnAddFilesButton(self, event):
        self.AddFiles(self._seriesname)

    # ------------------
    # Replace an existing file without changing anything else
    # The user must have clicked on column 0 in a row which contains files
    def OnPopupUpdateFile(self, event):
        self.AddFiles(self._seriesname, replacerow=self._grid.clickedRow)

    # ------------------
    def AddFiles(self, seriesname: str, replacerow: int|None = None) -> None:
        # Call the File Open dialog to get a con series HTML file
        if replacerow is None:
            dlg=wx.FileDialog (None, "Select files to upload", ".", "", "*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)
        else:
            dlg=wx.FileDialog (None, "Select a replacement file to upload", ".", "", "*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_CHANGE_DIR)

        # Do we have a last directory?
        directory=Settings().Get("Last FileDialog directory")
        if directory is not None:
            directory=os.path.normpath(directory)
            while directory:
                if os.path.exists(directory) and os.path.isdir(directory):
                    dlg.SetDirectory(directory)
                    break
                directory, _=os.path.split(directory)

        if dlg.ShowModal() == wx.ID_CANCEL:
            Settings().Put("Last FileDialog directory", dlg.GetDirectory())
            dlg.Destroy()
            return

        Settings().Put("Last FileDialog directory", dlg.GetDirectory())

        for fn in dlg.GetFilenames():
            if len(fn) ==0:
                continue

            # We need to try to make the fn into a somewhat more useful display title.
            # Commonly, file names are prefixed by <year> <conseriesname> <con number/con year>, so we'll remove those if we find them.
            _, dname=os.path.split(fn)
            m=re.match(r"\s*[0-9]{0,4}\s*"+seriesname+r"\s*(\'?[0-9]+|[IVXL]+|)\s*(.+)$", dname, flags=re.IGNORECASE)
            if m is not None and len(m.groups()) == 2:
                dname=m.groups()[1]
            # The conventions in the series may also have unique names rather than something like 'conseries 15', so we actually plug in the name
            m=re.match(r"\s*[0-9]{0,4}\s*"+self.Conname+r"\s*(.*)$", dname, flags=re.IGNORECASE)
            if m is not None and len(m.groups()) == 1:
                dname=m.groups()[0]

            if replacerow is None:
                conf: ConInstanceRow=ConInstanceRow()       # This is a new row
            else:
                conf: ConInstanceRow=self.Datasource.Rows[replacerow]       # Update an existing row

            # The new file's properties always update. The Site Name and Display Name are the file's
            # identity on the server, so they are set only when adding a brand-new row: a replace keeps
            # the existing names and swaps only the file behind them.
            conf.SourceFilename=fn
            conf.SourcePathname=str(os.path.join(dlg.GetDirectory(), fn))
            conf.Pages=GetPdfPageCount(conf.SourcePathname)
            conf.Size=os.path.getsize(conf.SourcePathname)/(1024**2)

            if replacerow is None:
                conf.SiteFilename=dname
                conf.DisplayTitle=dname     # Note that we only update the name for a new row.
                self.conInstanceDeltaTracker.Add(conf)
                self.Datasource.Rows.append(conf)
            else:
                self.conInstanceDeltaTracker.Replace(conf, conf.SiteFilename)

        dlg.Destroy()
        self.RefreshWindow()
        return

    # ----------------------------------------------
    def OnUploadConInstance(self, event):
        self.Uploaded=self.UploadConInstancePage()      # MarkAsSaved() runs inside on a successful upload
        self.RefreshWindow()

    # ----------------------------------------------
    def OnClose(self, event):
        if OnCloseHandling(event, self.NeedsSaving(), "This file list has been updated and not yet saved. Exit anyway?"):
            return

        self.EndModal(wx.ID_OK if self.Uploaded else wx.ID_CANCEL)

    # ----------------------------------------------
    # With V7 of the ConInstance file format we added page counts for PDFs.  Existing entries lack page counts.
    # Run through the list of files, and for each PDF see if it is missing a page count.
    # If it is, see if the file is locally available.
    # If it is, check the page count and add it to the table.
    def FillInMissingPDFPageCounts(self):
        for i, row in enumerate(self.Datasource.Rows):
            if not row.IsTextRow and not row.IsLinkRow:
                if row.Pages == 0:
                    if ExtensionMatches(row.SourcePathname, ".pdf"):
                        if os.path.exists(row.SourcePathname):
                            row.Pages=GetPdfPageCount(row.SourcePathname)
                            self.Datasource.Rows[i]=row


    def UploadConInstancePage(self, pm: ProgressMessage2=None, UploadFiles: bool=True) -> bool:
        if pm is not None:
           pm.Update(f"Updating {self.Conname}/index.html")

        # Delete any trailing empty rows.
        # Empty rows anywhere are as error, but we only silently drop trailing blank rows. Note that a blank text row is not an empty row.
        # Find the last non-blank row.
        last=None
        for i, row in enumerate(self.Datasource.Rows):
            if len((row.SourceFilename+row.SiteFilename+row.DisplayTitle+row.Notes).strip()) > 0:
                last=i
        # Delete the row or rows following it
        if last is not None and last < self.Datasource.NumRows-1:
            del self.Datasource.Rows[last+1:]

        # Check to see if the data is valid
        error=False
        for i, row in enumerate(self.Datasource.Rows):
            # Valid data requires
            #   If a text row, that some text exists
            #   If an external link row, that text and a properly formed URL exists (but does not check to see target exists)
            #   For a file, that there is an entry in the "Source File Name", "Site Name", and "Display Name" columns
            if row.IsTextRow:
                if len((row.SourceFilename+row.SiteFilename+row.DisplayTitle+row.Notes).strip()) == 0:
                    error=True
                    Log(f"Missing information in row {i}  {row}")
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
            else:   # Ordinary rows and Link rows
                if len(row.SiteFilename.strip()) == 0 or len(row.DisplayTitle.strip()) == 0:
                    error=True
                    Log(f"Missing sitename, or display name in row {i}  {row}")
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
        if error:
            self._grid.Grid.ForceRefresh()
            wx.MessageBox("Malformed row found")
            return False

        # If there are missing page counts for pdfs, try to get them. (This can eventually be eliminated as there will be no pre-V7 files on the server.)
        self.FillInMissingPDFPageCounts()

        if pm is None:
            with ModalDialogManager(ProgressMessage2, f"Uploading /{self._seriesname}/{self.Conname}/index.html", parent=self) as pm:
                return self.DoConInstanceUpload(pm, UploadFiles=UploadFiles)

        pm.Update(f"Uploading /{self._seriesname}/{self.Conname}/index.html")
        return self.DoConInstanceUpload(pm, UploadFiles=UploadFiles)



    def DoConInstanceUpload(self, pm: ProgressMessage2=None, UploadFiles: bool=True) -> bool:
        if pm is not None:
            Log(f"DoCIPUpload: Preparing {self.Conname} to be uploaded")
            pm.Update(f"Preparing {self.Conname} to be uploaded")


        ci=ConInstance(self._FTPbasedir, self._seriesname, self.Conname)

        pm.Update(f"{self._FTPbasedir}/{self.Conname}/index.html downloaded")

        ci.Toptext=self.topText.GetValue()
        ci.Credits=self.tCredits.GetValue()
        ci.PrevConInstanceName=self.PrevConInstanceName
        ci.NextConInstanceName=self.NextConInstanceName
        ci.ConInstanceRows=self._Datasource.Rows
        ci.IsSubPage=self._isSubPage
        ci.RootSeriesName=self._rootSeriesName
        ci.RootConName=self._rootConName

        # We have some conventions that have names of the form "Swancon 2004: Chronopolis"
        # The question is whether the ": Chronopolis" is part of the con's name or not.
        # First, we check to see if the con already exists and if it does, we follow precedent.
        # If it does not exist, we pop uo a query
        conname=self.Conname
        # We only need to do something if there is a colon int he conname (con instances only; a sub-page
        # name is taken literally).
        if not self._isSubPage and ":" in conname:
            # If there is a colon in the conname, we only need to do somehthing if the full-name-with-colon does not already exist.
            if not FTP().FileExists(f"/{self._seriesname}/{conname}/index.html"):
                # It does not.
                # Now check to see if it exists when truncated to before the colon. If that fails also, then we need to ask the user what to do.
                testname=conname[:conname.index(":")].strip()
                if FTP().FileExists(f"/{self._seriesname}/{testname}/index.html"):
                    conname=testname
                else:
                    rslt=wxMessageBox(f"The con's name contains a colon.\nConpub's default policy is to ignore everything following the colon, "
                                            f"making the con's name '{testname}'.\nDo you want to use that truncated name?\n('YES' is recommended unless there "
                                            f"is a specific reason to include the colon and material following it.)", style=wx.YES_NO)
                    if rslt == wx.ID_YES:
                        conname=testname

        if not ci.Upload(conname):
            return False

        if UploadFiles:
            self.UploadConInstanceFiles(pm)

        if pm is not None:
            pm.Update(f"Upload succeeded: /{self._seriesname}/{self.Conname}/index.html", delay=0.5)

        # The con instance is now saved to the server, so snapshot the current state as "saved".
        self.MarkAsSaved()
        return True


    # Build the PDF page-header format string and substitution items from real con-instance data.
    # See AddPdfPageHeader for the format/items conventions: a URL item is rendered as a hyperlink
    # whose display text is the immediately-following item; other items are plain text.
    #   * the con instance name -- linked to the con instance page
    #   * the item's title       -- plain text
    #   * the con's date(s)      -- plain text, in parentheses; omitted if unknown
    #   * "fanac.org/conpubs"    -- linked to the conpubs root
    def _BuildPageHeader(self, item_title: str) -> tuple[str, list]:
        # Build the page's conpubs URL from its full server path so it is correct for a sub-page too
        # (for a con instance this is just /conpubs/{series}/{con}/).
        segs=[s for s in self._FTPbasedir.split("/") if s]+[self.Conname]
        instance_url="https://www.fanac.org/conpubs/"+"/".join(quote(s, safe='') for s in segs)+"/"
        items=[instance_url, self.ConInstanceName, item_title]
        if self.ConInstanceDates.strip():
            fmt="{}: {} ({})  --  from {}"
            items.append(self.ConInstanceDates.strip())
        else:
            fmt="{}: {}  --  from {}"
        items+=["https://www.fanac.org/conpubs/", "fanac.org/conpubs"]
        return fmt, items


    # Return True if `row` falls in a "Newsletter" section of the con-instance table -- i.e. the
    # nearest preceding header (text) row is titled "Newsletter".
    def _IsInNewsletterSection(self, row) -> bool:
        rows=self.Datasource.Rows
        idx=next((i for i, x in enumerate(rows) if x is row), -1)
        if idx < 0:
            return False
        for i in range(idx-1, -1, -1):
            if rows[i].IsTextRow:
                return rows[i].DisplayTitle.strip().lower() == "newsletter"
        return False


    # Build the standard PDF document metadata from real con-instance data.
    # For an issue in a "Newsletter" section whose own title doesn't already mention "newsletter",
    # add "Newsletter" as an extra metadata keyword (the title and the page header are left unchanged).
    def _BuildMetadata(self, CleanTitle: str, is_newsletter: bool=False) -> dict:
        keywords=[self._seriesname, self.ConInstanceName, CleanTitle]
        if is_newsletter and "newsletter" not in CleanTitle.lower():
            keywords.append("Newsletter")
        keywords+=["fanac.org", "fan history", "science fiction convention"]
        return dict(title=f'{self.ConInstanceName}: {CleanTitle}',
                    author=self.Credits,
                    subject=f'Science fiction convention; {self._seriesname}; {self.ConInstanceName}; fan history; fanac.org',
                    keywords=", ".join(filter(None, keywords)))


    def _UploadPdfWithHeaderAndMetadata(self, src_path: str, site_name: str, metadata: dict,
                                        add_header: bool=True, header_format: str="", header_items: list=None) -> bool:
        """
        For PDF files: copy to a temp file, apply metadata and (optionally) page header to the
        copy, upload the copy, then delete it — leaving the original on disk untouched.
        For non-PDF files: upload the original directly.
        Returns True on success.
        """
        if not ExtensionMatches(src_path, ".pdf"):
            return FTP().PutFile(src_path, site_name)

        tmp_fd, tmp_path=tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        shutil.copy2(src_path, tmp_path)
        try:
            AddStdMetadata(tmp_path, **metadata)
            if add_header:
                try:
                    AddPdfPageHeader(tmp_path, header_format, header_items, logo=_g_headerLogo)
                except Exception as e:
                    msg=f"Failed to add page header to '{site_name}':\n{e}"
                    LogError(msg)
                    wx.MessageBox(msg, "Page Header Error", wx.OK|wx.ICON_WARNING)
            return FTP().PutFile(tmp_path, site_name)
        finally:
            try:
                os.remove(tmp_path)
            except Exception as e:
                Log(f"Could not delete temp file '{tmp_path}': {e}", isError=True)


    def UploadConInstanceFiles(self, pm):
        wd=f"{self._FTPbasedir}/{self.Conname}"   # the page's full server dir (handles sub-pages too)
        if not FTP().CWD(wd):
            msg=f"Could not change to server directory {wd} — file upload aborted."
            LogError(msg)
            wx.MessageBox(msg, f"Could not access server directory {wd}\nUpload failed", wx.OK|wx.ICON_ERROR)
            return

        # Check once whether PyMuPDF is available for page headers.
        fitz_available=True
        try:
            import fitz as _fitz_check  # noqa: F401
        except ImportError:
            fitz_available=False
            wx.MessageBox(
                "PyMuPDF is not installed — PDF page headers will be skipped for this upload.\n\n"
                "To install it, open a command prompt in the ConEditor folder and run:\n\n"
                "    .venv\\Scripts\\pip install pymupdf\n\n"
                "Then restart ConEditor.",
                "PyMuPDF not installed", wx.OK|wx.ICON_WARNING)

        failures: list[str]=[]

        for delta in self.conInstanceDeltaTracker.Deltas:
            # Each delta is processed independently: any unexpected error is logged and recorded as a
            # failure, but the loop continues with the remaining files rather than aborting the upload.
            try:
                if delta.Verb == "add":
                    if pm is not None:
                        pm.Update(f"Adding {delta.Con.SourcePathname} as {delta.Con.SiteFilename}")
                    Log(f"delta-ADD: {delta.Con.SourcePathname} as {delta.Con.SiteFilename}")
                    CleanTitle=_CleanTitle(delta.Con.DisplayTitle)
                    metadata=self._BuildMetadata(CleanTitle, self._IsInNewsletterSection(delta.Con))
                    header_format, header_items=self._BuildPageHeader(CleanTitle)
                    if not self._UploadPdfWithHeaderAndMetadata(delta.Con.SourcePathname, delta.Con.SiteFilename, metadata, add_header=fitz_available, header_format=header_format, header_items=header_items):
                        msg=f"Failed to upload '{delta.Con.SiteFilename}'"
                        LogError(msg)
                        failures.append(msg)
                        if pm is not None:
                            pm.Update(f"FAILED: could not upload {delta.Con.SiteFilename}")
                    else:
                        delta.Completed=True
                elif delta.Verb == "rename":
                    if pm is not None:
                        pm.Update(f"Renaming {delta.Oldname} to {delta.Con.SiteFilename}")
                    Log(f"delta-RENAME: {delta.Oldname} to {delta.Con.SiteFilename}")
                    if len(delta.Oldname.strip()) == 0:
                        Log("***Renaming a blank name can't be right! Ignored", isError=True)
                    elif not FTP().Rename(delta.Oldname, delta.Con.SiteFilename):
                        msg=f"Failed to rename '{delta.Oldname}' to '{delta.Con.SiteFilename}'"
                        LogError(msg)
                        failures.append(msg)
                        if pm is not None:
                            pm.Update(f"FAILED: could not rename {delta.Oldname}")
                    else:
                        delta.Completed=True
                elif delta.Verb == "delete":
                    if not delta.Con.IsTextRow and not delta.Con.IsLinkRow:
                        if pm is not None:
                            pm.Update(f"Deleting {delta.Con.SiteFilename}")
                        Log(f"delta-DELETE: {delta.Con.SiteFilename}")
                        if len(delta.Con.SiteFilename.strip()) > 0:
                            if not FTP().DeleteFile(delta.Con.SiteFilename):
                                msg=f"Failed to delete '{delta.Con.SiteFilename}'"
                                LogError(msg)
                                failures.append(msg)
                                if pm is not None:
                                    pm.Update(f"FAILED: could not delete {delta.Con.SiteFilename}")
                            else:
                                delta.Completed=True
                elif delta.Verb == "replace":
                    if pm is not None:
                        pm.Update(f"Replacing {delta.Oldname} with new/updated file")
                    Log(f"delta-REPLACE: {delta.Con.SourcePathname} <-- {delta.Oldname}")
                    Log(f"   delta-DELETE: {delta.Con.SiteFilename}")
                    delete_ok=True
                    if len(delta.Con.SiteFilename.strip()) > 0:
                        if not FTP().DeleteFile(delta.Con.SiteFilename):
                            msg=f"Failed to delete old file '{delta.Con.SiteFilename}' before replace"
                            LogError(msg)
                            failures.append(msg)
                            delete_ok=False
                    CleanTitle=_CleanTitle(delta.Con.DisplayTitle)
                    metadata=self._BuildMetadata(CleanTitle, self._IsInNewsletterSection(delta.Con))
                    Log(f"   delta-ADD: {delta.Con.SourcePathname} as {delta.Con.SiteFilename}")
                    header_format, header_items=self._BuildPageHeader(CleanTitle)
                    if not self._UploadPdfWithHeaderAndMetadata(delta.Con.SourcePathname, delta.Con.SiteFilename, metadata, add_header=fitz_available, header_format=header_format, header_items=header_items):
                        msg=f"Failed to upload replacement '{delta.Con.SiteFilename}'"
                        LogError(msg)
                        failures.append(msg)
                        if pm is not None:
                            pm.Update(f"FAILED: {delta.Con.SiteFilename}")
                    elif delete_ok:
                        delta.Completed=True
                else:
                    Log(f"delta-UNRECOGNIZED: {delta}")
            except Exception as e:
                name=delta.Con.SiteFilename or delta.Oldname or delta.Con.SourcePathname or "?"
                msg=f"Unexpected error during {delta.Verb} of '{name}': {e}"
                LogError(msg)
                failures.append(msg)
                if pm is not None:
                    pm.Update(f"FAILED: {name}")

            UpdateFTPLog.LogDelta(self._seriesname, self.Conname, delta)

        # The upload is complete. Start tracking changes afresh
        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()

        if failures:
            wx.MessageBox("The following file operations failed:\n\n" + "\n".join(failures),
                          "Upload Errors", wx.OK|wx.ICON_ERROR)


    #------------------
    # The page's name for the title bar: just the con name for a con instance; for a sub-page, the
    # breadcrumb from the owning con down to it (e.g. "ConFederation/Secrets"), dropping the series.
    def _PageBreadcrumb(self) -> str:
        if not self._isSubPage:
            return self.Conname
        parents=[c for c in self._FTPbasedir.split("/") if c][1:]   # drop the leading series component
        return "/".join(parents+[self.Conname])

    #------------------
    # Download a ConInstance
    def DownloadConInstancePage(self, pm=None) -> bool:
        # Clear out any old information
        self.Datasource=ConInstanceDatasource()

        # Read the existing CIP
        # We have two versions, one in which DownloadConInstancePage() is called with a ProgressMessage already showing and one where it must create it
        if pm is None:
            with (ModalDialogManager(ProgressMessage2, f"Downloading '{self._FTPbasedir}/{self.Conname}/index.html'", parent=self) as pm):
                if not FTP().FileExists(f"{self._FTPbasedir}/{self.Conname}/index.html"):
                    LogError(f"DownloadConInstancePage(): '{self._FTPbasedir}/{self.Conname}/index.html' not found")
                    return False
                ret=self.DoConInstanceDownload(pm=pm)
        else:
            pm.Update(f"Downloading {self._FTPbasedir}/{self.Conname}/index.html")
            if not FTP().FileExists(f"{self._FTPbasedir}/{self.Conname}/index.html"):
                LogError(f"DownloadConInstancePage(): '{self._FTPbasedir}/{self.Conname}/index.html' not found")
                return False
            ret=self.DoConInstanceDownload(pm=pm)

        self.Title=f"Editing {self._PageBreadcrumb()}"
        self._grid.MakeTextLinesEditable()
        # Log("DownloadConInstancePage() exit.")
        return ret


    # ----------------------------------------------
    def DoConInstanceDownload(self, pm: ProgressMessage2) -> bool:

        ci=ConInstance(self._FTPbasedir, self._seriesname, self.Conname)

        if not ci.Download():
            return False

        pm.Update(f"{self._FTPbasedir}/{self.Conname}/index.html downloaded")

        self.topText.SetValue(ci.Toptext)
        self.tCredits.SetValue(ci.Credits)
        self.PrevConInstanceName=ci.PrevConInstanceName
        self.NextConInstanceName=ci.NextConInstanceName
        self._Datasource.Rows=ci.ConInstanceRows

        return True


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_GridPopup)

        row=event.GetRow()
        self._PopupInsertTextRow_RowNumber=row

        self.m_popupNewsletter.Enabled=True
        self.m_popupMiscellaneous.Enabled=True
        self.m_popupPublications.Enabled=True
        self.m_popupConventionReports.Enabled=True
        self.m_popupPhotosAndVideo.Enabled=True
        self.m_popupWSFSstuff.Enabled=True
        self.m_popupBidding.Enabled=True

        self.m_popupAddFiles.Enabled=True
        self.m_popupInsertText.Enabled=True
        self.m_popupInsertLink.Enabled=True
        self.m_popupCreateSubPage.Enabled=True

        if row < self.Datasource.NumRows:
            self.m_popupDeleteRow.Enabled=True

        if self.Datasource.ColDefs[self._grid.clickedColumn].IsEditable == IsEditable.Maybe:
            self.m_popupAllowEditCell.Enabled=True

        if self._grid.clickedColumn == 0 and self._grid.clickedRow < self._grid.NumRows:
            if self._grid.clickedRow < self.Datasource.NumRows and \
                    not self.Datasource.Rows[self._grid.clickedRow].IsTextRow and \
                    not self.Datasource.Rows[self._grid.clickedRow].IsLinkRow:
                self.m_popupUpdateFile.Enabled=True

        # Enable "Regenerate PDF Header" when the row points to a PDF.
        if row < self.Datasource.NumRows:
            r=self.Datasource.Rows[row]
            if not r.IsTextRow and not r.IsLinkRow and ExtensionMatches(r.SiteFilename, ".pdf"):
                self.m_popupRegenPDFHeader.Enabled=True

        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)


    # ------------------
    # Regenerate the metadata and page header on a single already-uploaded PDF.
    # Downloads the row's PDF from the server, (re)applies current metadata and header, and uploads it
    # back. Returns "" on success or an error message.

    # This may be dumped after all pdfs in conpubs are brought up to current standards.
    def RegeneratePdfHeaderForRow(self, r, serverdir, pm) -> str:
        sitename=r.SiteFilename
        CleanTitle=_CleanTitle(r.DisplayTitle)
        tmp_fd, tmp_path=tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        try:
            pm.Update(f"Downloading {sitename}")
            if not FTP().GetFile(serverdir, sitename, tmp_path):
                msg=f"Could not download '{serverdir}/{sitename}' from the server (file not present?)."
                LogError(msg)
                return msg
            pm.Update(f"Updating metadata and header for {sitename}")
            try:
                AddStdMetadata(tmp_path, **self._BuildMetadata(CleanTitle, self._IsInNewsletterSection(r)))
                header_format, header_items=self._BuildPageHeader(CleanTitle)
                AddPdfPageHeader(tmp_path, header_format, header_items, logo=_g_headerLogo)
            except Exception as e:
                LogError(f"Failed to update metadata/header for '{sitename}':\n{e}")
                return f"Failed to update metadata/header for '{sitename}':\n{e}"
            pm.Update(f"Uploading {sitename}")
            if not FTP().CWD(serverdir) or not FTP().PutFile(tmp_path, sitename):
                msg=f"Could not upload '{sitename}' to the server."
                LogError(msg)
                return msg
            # Update the row to match the regenerated file so the grid and the con instance page
            # show the correct size (and page count).
            r.Size=os.path.getsize(tmp_path)/(1024**2)
            pages=GetPdfPageCount(tmp_path)
            if pages is not None:
                r.Pages=pages
            return ""
        finally:
            try:
                os.remove(tmp_path)
            except Exception as e:
                Log(f"Could not delete temp file '{tmp_path}': {e}", isError=True)


    # Regenerate metadata+header for the clicked PDF, or for all selected rows when the
    # click landed on a selected row. Non-PDF rows in the selection are skipped.
    def OnPopupRegeneratePDFHeader(self, event):
        try:
            import fitz as _fitz_check  # noqa: F401
        except ImportError:
            wx.MessageBox("PyMuPDF is not installed — cannot regenerate the PDF header.", "PyMuPDF not installed", wx.OK|wx.ICON_WARNING)
            return

        # Operate on the whole selection only when the click landed inside it; otherwise just the clicked row.
        clicked=self._grid.clickedRow
        if self._grid.HasSelection():
            top, _, bottom, _=self._grid.LocateSelection()
        else:
            top=bottom=-1
        rownums=list(range(top, bottom+1)) if top <= clicked <= bottom else [clicked]

        # Keep only real PDF rows.
        rownums=[i for i in rownums if 0 <= i < self.Datasource.NumRows
                 and not self.Datasource.Rows[i].IsTextRow
                 and not self.Datasource.Rows[i].IsLinkRow
                 and ExtensionMatches(self.Datasource.Rows[i].SiteFilename, ".pdf")]
        if not rownums:
            return

        serverdir=f"/{self._seriesname}/{self.Conname}"
        failures=[]
        nsuccess=0
        with ModalDialogManager(ProgressMessage2, f"Regenerating {len(rownums)} PDF header(s)", parent=self) as pm:
            for i in rownums:
                err=self.RegeneratePdfHeaderForRow(self.Datasource.Rows[i], serverdir, pm)
                if err:
                    failures.append(err)
                else:
                    nsuccess+=1

            # The regenerated files have new sizes. Refresh the grid and re-upload index.html so both
            # the grid and the live con instance page reflect the updated sizes.
            if nsuccess > 0:
                self._grid.RefreshWxGridFromDatasource()
                pm.Update(f"Updating {self.Conname}/index.html")
                try:
                    ci=ConInstance(self._FTPbasedir, self._seriesname, self.Conname)
                    ci.Toptext=self.topText.GetValue()
                    ci.Credits=self.tCredits.GetValue()
                    ci.PrevConInstanceName=self.PrevConInstanceName
                    ci.NextConInstanceName=self.NextConInstanceName
                    ci.ConInstanceRows=self.Datasource.Rows
                    if not ci.Upload(self.Conname):
                        failures.append(f"Could not update '{self.Conname}/index.html' with the new sizes.")
                    else:
                        # The con instance index.html was re-uploaded with the new sizes, so it's now saved.
                        self.MarkAsSaved()
                        self.UpdateNeedsSavingFlag()    # Clear the " *" needs-saving marker in the title
                except Exception as e:
                    LogError(f"OnPopupRegeneratePDFHeader: failed to re-upload index.html: {e}")
                    failures.append(f"Could not update '{self.Conname}/index.html': {e}")

            pm.Update(f"Regenerated {nsuccess} of {len(rownums)} PDF header(s)", delay=0.5)

        if failures:
            wx.MessageBox("\n".join(failures), "Regenerate PDF Header", wx.OK|wx.ICON_ERROR)


    # ------------------
    def OnGridCellDoubleClick(self, event):
        self._grid.OnGridCellDoubleClick(event)

        # Doubleclicking on and empty cell 0 of a line brings up a popup menu of standard text headings and makes th elink into a text row.
        row=event.GetRow()
        self._PopupInsertTextRow_RowNumber=row

        # Double-clicking a sub-page row opens it -- creating it (seeded from its Notes) on first entry,
        # exactly like double-clicking an unlinked con row on a ConSeries page.
        if row < self.Datasource.NumRows and self.Datasource.Rows[row].IsSubPageRow:
            self._EnterSubPage(row)
            return

        if row > self.Datasource.NumRows:
            return  # We do nothing when you double-click in an empty cell beyond the 1st empty row
        if event.GetCol() > 0:
            return  # Only doubleclicks on the first column work
        if self._grid.Grid.GetCellValue(row, 0) != "":
            return  # Only of the 1st cell is empty

        # OK, we're going to turn this row -- which may need to be added -- into text row
        if row >= self.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(row, 0)  # If we're inserting past the end of the datasource, insert empty rows as necessary to fill in between
            self._grid.InsertEmptyRows(row, 1)
        self.Datasource.Rows[row].IsTextRow=True

        self.m_popupNewsletter.Enabled=True
        self.m_popupMiscellaneous.Enabled=True
        self.m_popupPublications.Enabled=True
        self.m_popupConventionReports.Enabled=True
        self.m_popupPhotosAndVideo.Enabled=True
        self.m_popupWSFSstuff.Enabled=True
        self.m_popupBidding.Enabled=True

        self.m_popupCopy.Enabled=False
        self.m_popupAddFiles.Enabled=False
        self.m_popupInsertText.Enabled=False
        self.m_popupInsertLink.Enabled=False
        self.m_popupUpdateFile.Enabled=False
        self.m_popupAllowEditCell.Enabled=False
        self.m_popupDeleteRow.Enabled=False

        # This caches row number for popup's use
        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)

    # ------------------
    # Open a sub-page (SP) row for editing. On first entry an SP that does not yet exist is created on the
    # server -- its index.html seeded (once) from the row's Notes -- then the row is marked linked, mirroring
    # how an unlinked con row on a ConSeries page is created when you enter it.
    def _EnterSubPage(self, row: int) -> None:
        r=self.Datasource.Rows[row]
        spname=r.DisplayTitle.strip()
        if spname == "":
            return
        parentpath=f"{self._FTPbasedir}/{self.Conname}"   # sub-pages live under the current page's directory
        folder=r.SiteFilename.strip()
        if folder == "":
            # Not yet created. Confirm, then create the sub-page (seeded from this row's Notes) on entry.
            if wx.ID_YES != wxMessageBox(f"No sub-page exists for '{spname}'. Do you wish to create one?", style=wx.YES_NO):
                return
            folder=RemoveAccents(spname)
            with ModalDialogManager(ProgressMessage2, f"Creating sub-page '{spname}'", parent=self) as pm:
                ci=ConInstance(parentpath, self._seriesname, folder)
                ci.IsSubPage=True
                ci.RootSeriesName=self._rootSeriesName
                ci.RootConName=self._rootConName
                ci.Toptext=r.Notes      # one-time seed from the row's Notes; independent thereafter
                ci.Credits=""
                ci.ConInstanceRows=[]
                if not ci.Upload(folder):
                    wx.MessageBox(f"Could not create the sub-page '{spname}'.", "Create Sub-Page failed", wx.OK|wx.ICON_ERROR)
                    return
            r.SiteFilename=folder       # the SP now exists -> mark the row as a working (linked) folder link
            self.RefreshWindow()
            self.UpdateNeedsSavingFlag()

        # Open the sub-page for editing (it now exists on the server).
        with ModalDialogManager(ConInstanceDialogClass, parentpath, self._seriesname, folder, "", "",
                                Create=False, is_subpage=True,
                                rootSeriesName=self._rootSeriesName, rootConName=self._rootConName) as dlg:
            if len(dlg.ReturnMessage) > 0:
                wx.MessageBox(dlg.ReturnMessage)
                return
            dlg.ShowModal()

    # ------------------
    # RMB "Create Sub-Page": add a (not-yet-created) sub-page row. Like filling in a con row on a ConSeries
    # page, this only records the row; the SP itself is created when the user double-clicks to enter it.
    def OnPopupCreateSubPage(self, event):
        name=MessageBoxInput("Enter the name of the new sub-page.", title="Create Sub-Page", Parent=self)
        if name is None or name.strip() == "":
            return
        name=name.strip()
        irow=self._grid.clickedRow
        if irow > self.Datasource.NumRows:
            irow=self.Datasource.NumRows
        self._grid.InsertEmptyRows(irow, 1)
        r=self.Datasource.Rows[irow]
        r.IsSubPageRow=True
        r.DisplayTitle=name
        r.SiteFilename=""       # uncreated until the user enters it
        self.RefreshWindow()

    # ------------------
    # Per-cell grid hook (runs after each refresh): give the Display Name cell of a sub-page row a folder
    # icon so it is recognizable as a link to a lower page. The full grid rebuild resets renderers, so this
    # re-applies it each time; non-sub-page cells keep the default renderer.
    def _DecorateSubPageCell(self, icol: int, irow: int) -> None:
        if irow < self.Datasource.NumRows and icol == 0 and self.Datasource.Rows[irow].IsSubPageRow:
            self._grid.Grid.SetCellRenderer(irow, icol, _SubPageCellRenderer())

    def OnPopupPublications(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Publications"
        # Log("OnPopupPublications(): About to refresh")
        self.RefreshWindow()

    def OnPopuplMiscellaneous(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Miscellaneous"
        # Log("OnPopupMiscellaneous(): About to refresh")
        self.RefreshWindow()

    def OnPopupNewsletter(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Newsletter"
        # Log("OnPopupNewsletter(): About to refresh")
        self.RefreshWindow()

    def OnPopupPhotosAndVideo(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Photos and Videos"
        # Log("OnPopupPhotosAndVideo(): About to refresh")
        self.RefreshWindow()

    def OnPopupConventionReports(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Convention Reports"
        # Log("OnPopupConventionReports(): About to refresh")
        self.RefreshWindow()

    def OnPopupWSFSstuff(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="WSFS, Hugos, Site Selection"
        self.RefreshWindow()

    def OnPopupBidding(self, event):
        self.InsertTextRow()
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Bidding"
        self.RefreshWindow()

    # -------------------
    def OnKeyDown(self, event):
        self._grid.OnKeyDown(event)
        self.UpdateNeedsSavingFlag()

    # -------------------
    def OnKeyUp(self, event):
        self._grid.OnKeyUp(event)

    # ------------------
    def OnPopupCopy(self, event):
        self._grid.OnPopupCopy(event)

    # ------------------
    def OnPopupPaste(self, event):
        self._grid.OnPopupPaste(event)
        # Log("OnPopupPaste(): About to refresh")
        self.RefreshWindow()

    # ------------------
    def OnPopupInsertText(self, event):
        self.InsertTextRow()
        # Log("OnPopupInsertText(): About to refresh")
        self.RefreshWindow()

    #--------------------
    def InsertTextRow(self):
        irow=self._grid.clickedRow
        if irow > self.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)  # If we're inserting past the end of the datasource, insert empty rows as necessary to fill in between
        self._grid.InsertEmptyRows(irow, 1)  # Insert the new empty row
        self.Datasource.Rows[irow].IsTextRow=True
        self._grid.Grid.SetCellSize(irow, 0, 1, self._grid.NumCols)
        for icol in range(self._grid.NumCols):
            self._grid.AllowCellEdit(irow, icol)

    # ------------------
    def OnPopupInsertLink(self, event):
        irow=self._grid.clickedRow
        if irow > self.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)   # Insert empty rows into the datasource if necessary to keep things in sync
        self._grid.InsertEmptyRows(irow, 1)     # Insert the new empty row
        self.Datasource.Rows[irow].IsLinkRow=True
        for icol in range(self._grid.NumCols):
            self._grid.AllowCellEdit(irow, icol)

        # Log("OnPopupInsertLink(): About to refresh")
        self.RefreshWindow()

    # ------------------
    def OnPopupAllowEditCell(self, event):
        # Append a (row, col) tuple. This only lives for the life of this instance.
        self._grid.AllowCellEdit(self._grid.clickedRow, self._grid.clickedColumn)
        # Log("OnPopupAllowEditCell(): About to refresh")
        self.RefreshWindow()

    # ------------------
    def OnPopupAddFiles(self, event):
        self.AddFiles(self._seriesname)

    # ------------------
    def OnPopupDeleteRow(self, event):
        if self._grid.HasSelection():
            top, left, bottom, right=self._grid.LocateSelection()
            nrows=self.Datasource.NumRows
            if top >= nrows:
                top=nrows-1
            if bottom >= nrows:
                bottom=nrows-1
        else:
            if self._grid.clickedRow >= self.Datasource.NumRows:
                return
            top=bottom=self._grid.clickedRow

        self._grid.Grid.ClearSelection()

        for row in self.Datasource.Rows[top:bottom+1]:
            self.conInstanceDeltaTracker.Delete(row)
        self._grid.DeleteRows(top, bottom-top+1)
        # Log("OnPopupDeleteRow(): About to refresh")
        self.RefreshWindow()


    # ------------------
    # The grid's contents have changed.  Update the Datasource and record a Delta if needed
    def OnGridCellChanged(self, event):
        row=event.GetRow()
        col=event.GetCol()
        if row >= self.Datasource.NumRows:    # Ignore (and thus reject) data entry beyond the last Datasource row.  (Rows must be added using AddFiles or new Text Line, etc)
            event.Veto()
            return

        # Handle the column "Site Name" specially
        if self.Datasource.ColHeaders[col] == "Site Name":    # Editing the filename on the Conpubs site
            originalfname=self.Datasource[row][col]
            _, oext=os.path.splitext(originalfname)
            self._grid.OnGridCellChanged(event)

            # If this is a Link line, then Site Name is the foreign URL and user has full control over it.
            # Everything else needs to run through some checks
            if not self.Datasource[row].IsLinkRow:
                newfname=self.Datasource[row][col]
                # If we don't allow extensions to be edited (the default), restore the old extension before proceeding.
                if not self.m_checkBoxAllowEditExtentions.IsChecked():
                    newname, _=os.path.splitext(newfname)
                    newfname=newname+oext
                    self.Datasource[row][col]=newfname
                    # Log("OnGridCellChanged(): About to refresh #1")
                    self.RefreshWindow()

                if originalfname != newfname:
                    self.conInstanceDeltaTracker.Rename(self.Datasource.Rows[row], originalfname)
                return

        # All other columns
        self._grid.OnGridCellChanged(event)
        textCol, hrefCol=self.Datasource.TextAndHrefCols
        if self.Datasource.Rows[row].IsLinkRow and col == hrefCol:
            # We do some fiddling with the incoming URLs
            if not self.Datasource.Rows[row].SiteFilename.lower().startswith("http"):
                self.Datasource[row][col]=f"https://{self.Datasource.Rows[row].SiteFilename}"
        # Log("OnGridCellChanged(): About to refresh #2")
        self.RefreshWindow()

    # ------------------
    def OnGridEditorShown(self, event):
        self._grid.OnGridEditorShown(event)

    # ------------------
    def OnTextConInstanceName(self, event):
        self.RefreshWindow(DontRefreshGrid=True)

    # ------------------
    def OnTextConInstanceNameKeyUp(self, event):
        self.ConInstanceFancyURL=f"fancyclopedia.org/{WikiPagenameToWikiUrlname(self.tConInstanceName.GetValue().strip())}"
        self.RefreshWindow(DontRefreshGrid=True)

    # ------------------
    def OnTextConInstanceFancyURL(self, event):
        self.RefreshWindow(DontRefreshGrid=True)

    # ------------------
    def OnTopTextComments(self, event):
        self.RefreshWindow(DontRefreshGrid=True)

    # ------------------
    def OnTextConInstanceCredits(self, event):
        self.RefreshWindow(DontRefreshGrid=True)

    #------------------
    def RefreshWindow(self, DontRefreshGrid: bool=False) -> None:
        # Log(f"ConInstanceFrame.RefreshWindow({DontRefreshGrid=}) called from {inspect.stack()[2][3]}  called from {inspect.stack()[3][3]}  called from {inspect.stack()[4][3]}")
        if not DontRefreshGrid:
            self._grid.RefreshWxGridFromDatasource()
        self.UpdateNeedsSavingFlag()

