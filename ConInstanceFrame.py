from __future__ import annotations

import wx
import os

import re

from GenConInstanceFrame import GenConInstanceFrame
from WxDataGrid import DataGrid, Color, IsEditable
from ConInstance import ConInstanceDatasource, ConInstanceRow, ConInstance
from ConInstanceDeltaTracker import ConInstanceDeltaTracker, UpdateFTPLog
from FTP import FTP
from Settings import Settings
from Log import Log, LogError
from HelpersPackage import WikiPagenameToWikiUrlname, ExtensionMatches
from PDFHelpers import GetPdfPageCount, AddMissingMetadata
from WxHelpers import OnCloseHandling, ModalDialogManager, ProgressMessage2


#####################################################################################
class ConInstanceDialogClass(GenConInstanceFrame):

    def __init__(self, basedirFTP: str, seriesname: str, conname: str, prevconname: str= "", nextconname: str= "", Create: bool=False, pm=None):
        GenConInstanceFrame.__init__(self, None)

        self._grid: DataGrid=DataGrid(self.gRowGrid)
        self.Datasource=ConInstanceDatasource()

        self._grid.HideRowLabels()

        self._FTPbasedir=basedirFTP # The root of the convention's files, e.g., "/seriesName"
        self._seriesname=seriesname # The name of the series
        self.Conname=conname        # The actual name of the con directory on conpubs
        self._credits=""

        self._signature=0

        # A list of changes to the file stored on the website which will need to be made upon upload.
        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()

        self._returnMessage=""  # Error message if download failed
        self._uploaded=False    # Has this con instance been successfully uploaded since ut was initialized? (This is needed to generate the return value from the dialog.)
        self._downloaded=False  # Has this con instance been successfully downloaded?
        self._valid=False       # Is this a valid ConInstanceDialogClass?

        self.Datasource.SpecialTextColor=None

        if not Create:
            self._downloaded=self.DownloadConInstancePage(pm=pm)
            if not self._downloaded:
                self._returnMessage=f"Unable to download ConInstance page {self._FTPbasedir}/{self.Conname}/index.html"
                return

        #  Override any existing prev/next with the current prev/next
        self._prevConInstanceName=prevconname
        self._nextConInstanceName=nextconname

        self._valid=True
        self.SetEscapeId(wx.ID_CANCEL)

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
    def Signature(self) -> int:
        stuff=self.ConInstanceName.strip()+self.ConInstanceTopText.strip()+self.ConInstanceFancyURL.strip()+self.Credits.strip()
        return hash(stuff)+self.Datasource.Signature()

    def MarkAsSaved(self):
        self._signature=self.Signature()

    def NeedsSaving(self) -> bool:
        return self._signature != self.Signature()

    def UpdateNeedsSavingFlag(self):
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
                conf=ConInstanceRow()       # This is a new row
            else:
                conf=self.Datasource.Rows[replacerow]       # Update an existing row

            conf.SiteFilename=dname
            conf.SourceFilename=fn
            conf.SourcePathname=str(os.path.join(dlg.GetDirectory(), fn))
            conf.Pages=GetPdfPageCount(conf.SourcePathname)
            conf.Size=os.path.getsize(conf.SourcePathname)/(1024**2)

            if replacerow is None:
                conf.DisplayTitle=dname     # Note that we only update the name for a new row.
                self.conInstanceDeltaTracker.Add(conf)
                self.Datasource.Rows.append(conf)
            else:
                newfilename=os.path.join(dlg.GetDirectory(), fn)
                self.conInstanceDeltaTracker.Replace(conf, conf.SourcePathname)
                self.Datasource.Rows[replacerow].SourcePathname=newfilename

        dlg.Destroy()
        self.RefreshWindow()
        return


    # ----------------------------------------------
    def OnUploadConInstance(self, event):
        self.OnUploadConInstancePage()

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


    # ----------------------------------------------
    # This has been pulled out of the OnUploadConInstance() handler so it can also be called to auto update a series of pages
    def OnUploadConInstancePage(self) -> None:

        self.Uploaded=self.UploadConInstancePage()
        self.MarkAsSaved()



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
        ci.PrevConInstanceName=self._prevConInstanceName
        ci.NextConInstanceName=self._nextConInstanceName
        ci.ConInstanceRows=self._Datasource.Rows

        if not ci.Upload():
            return False

        if UploadFiles:
            self.UploadConInstanceFiles(pm)

        if pm is not None:
            pm.Update(f"Upload succeeded: /{self._seriesname}/{self.Conname}/index.html", delay=0.5)
        return True


    def UploadConInstanceFiles(self, pm):
        wd=f"/{self._seriesname}/{self.Conname}"
        FTP().CWD(wd)
        for delta in self.conInstanceDeltaTracker.Deltas:
            if delta.Verb == "add":
                if pm is not None:
                    pm.Update(f"Adding {delta.Con.SourcePathname} as {delta.Con.SiteFilename}")
                Log(f"delta-ADD: {delta.Con.SourcePathname} as {delta.Con.SiteFilename}")
                metadata={
                    '/Title': f'{self.Conname}: {delta.Con.DisplayTitle.strip().removesuffix(".pdf").removesuffix(".PDF")}'
                }
                AddMissingMetadata(delta.Con.SourcePathname, metadata)
                FTP().PutFile(delta.Con.SourcePathname, delta.Con.SiteFilename)
            elif delta.Verb == "rename":
                if pm is not None:
                    pm.Update(f"Renaming {delta.Oldname} to {delta.Con.SiteFilename}")
                Log(f"delta-RENAME: {delta.Oldname} to {delta.Con.SiteFilename}")
                if len(delta.Oldname.strip()) == 0:
                    Log("***Renaming an blank name can't be right! Ignored", isError=True)
                    continue
                FTP().Rename(delta.Oldname, delta.Con.SiteFilename)
            elif delta.Verb == "delete":
                if not delta.Con.IsTextRow and not delta.Con.IsLinkRow:
                    if pm is not None:
                        pm.Update(f"Deleting {delta.Con.SiteFilename}")
                    Log(f"delta-DELETE: {delta.Con.SiteFilename}")
                    if len(delta.Con.SiteFilename.strip()) > 0:
                        FTP().DeleteFile(delta.Con.SiteFilename)
            elif delta.Verb == "replace":
                if pm is not None:
                    pm.Update(f"Replacing {delta.Oldname} with new/updated file")
                Log(f"delta-REPLACE: {delta.Con.SourcePathname} <-- {delta.Oldname}")
                Log(f"   delta-DELETE: {delta.Con.SiteFilename}")
                if len(delta.Con.SiteFilename.strip()) > 0:
                    FTP().DeleteFile(delta.Con.SiteFilename)
                Log(f"   delta-ADD: {delta.Con.SourcePathname} as {delta.Con.SiteFilename}")
                FTP().PutFile(delta.Con.SourcePathname, delta.Con.SiteFilename)
            else:
                Log(f"delta-UNRECOGNIZED: {delta}")

            UpdateFTPLog.LogDeltas(self._seriesname, self.Conname, self.conInstanceDeltaTracker)

            self.conInstanceDeltaTracker=ConInstanceDeltaTracker()  # The upload is complete. Start tracking changes afresh


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

        self.Title=f"Editing {self.Conname}"
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
        self._prevConInstanceName=ci.PrevConInstanceName
        self._nextConInstanceName=ci.NextConInstanceName
        self._Datasource.Rows=ci.ConInstanceRows

        return True


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_GridPopup)

        row=event.GetRow()
        self._PopupInsertTextRow_RowNumber=row

        # Suppress the options used when double-clicking on an empty line's column 0
        flag=False
        if row < self.Datasource.NumRows:
            flag=self.Datasource.Rows[row].IsTextRow
        self.m_popupNewsletter.Enabled=flag
        self.m_popupMiscellaneous.Enabled=flag
        self.m_popupPublications.Enabled=flag
        self.m_popupConventionReports.Enabled=flag
        self.m_popupPhotosAndVideo.Enabled=flag

        self.m_popupAddFiles.Enabled=True
        self.m_popupInsertText.Enabled=True
        self.m_popupInsertLink.Enabled=True

        if row < self.Datasource.NumRows:
            self.m_popupDeleteRow.Enabled=True

        if self.Datasource.ColDefs[self._grid.clickedColumn].IsEditable == IsEditable.Maybe:
            self.m_popupAllowEditCell.Enabled=True

        if self._grid.clickedColumn == 0 and self._grid.clickedRow < self._grid.NumRows:
            if self._grid.clickedRow < self.Datasource.NumRows and \
                    not self.Datasource.Rows[self._grid.clickedRow].IsTextRow and \
                    not self.Datasource.Rows[self._grid.clickedRow].IsLinkRow:
                self.m_popupUpdateFile.Enabled=True

        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)


    # ------------------
    def OnGridCellDoubleClick(self, event):
        self._grid.OnGridCellDoubleClick(event)

        # Doubleclicking on and empty cell 0 of a line brings up a popup menu of standard text headings and makes th elink into a text row.
        row=event.GetRow()
        self._PopupInsertTextRow_RowNumber=row

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

        self.m_popupCopy.Enabled=False
        self.m_popupCopy.Enabled=False
        self.m_popupAddFiles.Enabled=False
        self.m_popupInsertText.Enabled=False
        self.m_popupInsertLink.Enabled=False
        self.m_popupUpdateFile.Enabled=False
        self.m_popupAllowEditCell.Enabled=False
        self.m_popupDeleteRow.Enabled=False

        # This caches row number for popup's use
        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)

    def OnPopupPublications(self, event):
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Publications"
        # Log("OnPopupPublications(): About to refresh")
        self.RefreshWindow()

    def OnPopuplMiscellaneous(self, event):
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Miscellaneous"
        # Log("OnPopuplMiscellaneous(): About to refresh")
        self.RefreshWindow()

    def OnPopupNewsletter(self, event):
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Newsletter"
        # Log("OnPopupNewsletter(): About to refresh")
        self.RefreshWindow()

    def OnPopupPhotosAndVideo(self, event):
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Photos and Videos"
        # Log("OnPopupPhotosAndVideo(): About to refresh")
        self.RefreshWindow()

    def OnPopupConventionReports(self, event):
        self.Datasource.Rows[self._PopupInsertTextRow_RowNumber][0]="Convention Reports"
        # Log("OnPopupConventionReports(): About to refresh")
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
        irow=self._grid.clickedRow
        if irow > self.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)   # If we're inserting past the end of the datasource, insert empty rows as necessary to fill in between
        self._grid.InsertEmptyRows(irow, 1)     # Insert the new empty row
        self.Datasource.Rows[irow].IsTextRow=True
        self._grid.Grid.SetCellSize(irow, 0, 1, self._grid.NumCols)
        for icol in range(self._grid.NumCols):
            self._grid.AllowCellEdit(irow, icol)

        # Log("OnPopupInsertText(): About to refresh")
        self.RefreshWindow()

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

