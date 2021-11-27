from __future__ import annotations
from typing import Optional

import wx
from wx import _core
import os
import sys
import json
import re
from datetime import datetime
from PyPDF4 import PdfFileReader

from GenConInstanceFrame import GenConInstanceFrame
from WxDataGrid import DataGrid, Color
from ConInstance import ConInstancePage, ConFile
from ConInstanceDeltaTracker import ConInstanceDeltaTracker, UpdateLog
from FTP import FTP
from Settings import Settings
from Log import Log

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, RemoveHTTP, ExtensionMatches, PyiResourcePath
from WxHelpers import ProgressMessage, OnCloseHandling


# Get the file's page count if it's a pdf
def GetPdfPageCount(pathname: str):
    if not ExtensionMatches(pathname, ".pdf"):
        return None
    try:
        with open(pathname, 'rb') as fl:
            reader=PdfFileReader(fl)
            return reader.getNumPages()
    except:
        Log("GetPdfPageCount: Exception raised while getting page count for '"+pathname+"'")
        return None

#####################################################################################
class ConInstanceDialogClass(GenConInstanceFrame):

    def __init__(self, basedirFTP, seriesname, coninstancename):
        GenConInstanceFrame.__init__(self, None)

        self._grid: DataGrid=DataGrid(self.gRowGrid)
        self.Datasource=ConInstancePage()

        self._grid.HideRowLabels()

        self._FTPbasedir=basedirFTP
        self._seriesname=seriesname
        self._coninstancename=coninstancename
        self._credits=""

        self._signature=0

        # A list of changes to the file stored on the website which will need to be made upon upload.
        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()

        self._uploaded=False    # Has this instance been uploaded? (This is needed to generate the return value from the dialog.)

        val=Settings().Get("ConInstanceFramePage:File list format", default=1)  # Default value is display as list
        self.radioBoxFileListFormat.SetSelection(val)

        val=Settings().Get("ConInstanceFramePage:Show Extensions", default=1)   # Default value is do not show extensions
        self.radioBoxShowExtensions.SetSelection(val)

        self.Datasource.SpecialTextColor=None

        self.DownloadConInstancePage()

        self.SetEscapeId(wx.ID_CANCEL)

        self.MarkAsSaved()
        self.RefreshWindow()


    @property
    def Datasource(self) -> ConInstancePage:
        return self._Datasource
    @Datasource.setter
    def Datasource(self, val: ConInstancePage):
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
    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 4,
           "ConInstanceName": self.ConInstanceName,
           "ConInstanceStuff": self.ConInstanceTopText,
           "ConInstanceFancyURL": self.ConInstanceFancyURL,
           "Credits": self.Credits,
           "_datasource": self.Datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> GenConInstanceFrame:
        d=json.loads(val)
        self.ConInstanceName=d["ConInstanceName"]
        self.ConInstanceTopText=d["ConInstanceStuff"]
        self.ConInstanceFancyURL=d["ConInstanceFancyURL"]
        if d["ver"] > 3:
            self.Credits=d["Credits"]
        self.ConInstanceFancyURL=RemoveHTTP(self.ConInstanceFancyURL)
        self.Datasource=ConInstancePage().FromJson(d["_datasource"])
        return self

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
    def AddFiles(self, seriesname: str, replacerow: Optional[int] = None) -> None:
        # Call the File Open dialog to get an con series HTML file
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

        if replacerow is None:
            for fn in dlg.GetFilenames():
                conf=ConFile()
                # We need to try to make the fn into a somewhat more useful display title.
                # Commonly, file names are prefixed by <conname> <con number/con year>, so we'll remove that if we find it.
                dname=fn
                pat=seriesname+"\s*(\'?[0-9]+|[IVXL]+)\s*(.+)"
                m=re.match(pat, dname, flags=re.IGNORECASE)
                if m is not None and len(m.groups()) == 2:
                    dname=m.groups()[1]
                conf.DisplayTitle=dname
                conf.SiteFilename=fn
                conf.SourceFilename=fn
                conf.SourcePathname=os.path.join(os.path.join(dlg.GetDirectory()), fn)
                conf.Size=os.path.getsize(conf.SourcePathname)
                conf.Pages=GetPdfPageCount(conf.SourcePathname)
                self.conInstanceDeltaTracker.Add(conf)
                self.Datasource.Rows.append(conf)
        else:
            if len(dlg.GetFilenames()) > 0:
                conf=self.Datasource.Rows[replacerow]
                fn=dlg.GetFilenames()[0]
                newfilename=os.path.join(os.path.join(dlg.GetDirectory()), fn)
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
    def OnUploadConInstancePage(self) -> None:

        # Delete any trailing blank rows.  (Blank rows anywhere are as error, but we only silently drop trailing blank rows.)
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
                    Log(f"Malformed text row: #{i}  {row}")
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
            elif row.IsLinkRow:
                if len(row.URL.strip()) == 0  or len(row.DisplayTitle.strip()) == 0:
                    error=True
                    Log(f"Malformed link row: #{i}  {row}")
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
            else:
                if len(row.SourceFilename.strip()) == 0 or len(row.SiteFilename.strip()) == 0 or len(row.DisplayTitle.strip()) == 0:
                    error=True
                    Log(f"Malformed file row: #{i}  {row}")
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
        if error:
            self._grid.Grid.ForceRefresh()
            wx.MessageBox("Malformed row found")
            return


        # Read in the template
        try:
            Log("sys.path[0]=  "+sys.path[0])
            Log("sys.argv[0]=  "+sys.argv[0])
            Log("os.path.join(sys.path[0], 'Template-ConPage.html')=  "+os.path.join(sys.path[0], "Template-ConPage.html"))
            with open(PyiResourcePath("Template-ConPage.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConPage.html'")
            Log("Can't read 'Template-ConPage.html'")
            return

        ProgressMessage(self).Show("Uploading /"+self._seriesname+"/"+self._coninstancename+"/index.html")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        fancylink=FormatLink("https://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName), self.ConInstanceName)
        file=SubstituteHTML(file, "title", self.ConInstanceName)
        file=SubstituteHTML(file, "fanac-instance", fancylink)
        file=SubstituteHTML(file, "fanac-stuff", self.ConInstanceTopText)

        # Fill in the top buttons
        s="<button onclick=\"window.location.href='https://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName)+"'\"> Fancyclopedia 3 </button>&nbsp;&nbsp;"+ \
        "<button onclick=\"window.location.href='..'\">All "+self._seriesname+"s</button>"
        file=SubstituteHTML(file, "fanac-topbuttons", s)

        # If there are missing page counts for pdfs, try to gett hem. (This can eventually be eliminated as there will be no pre-V7 files on the server.)
        self.FillInMissingPDFPageCounts()

        file=SubstituteHTML(file, "fanac-json", self.ToJson())
        file=SubstituteHTML(file, "fanac-date", datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST")
        if len(self.Credits.strip()) > 0:
            file=SubstituteHTML(file, "fanac-credits", 'Credits: '+self.Credits.strip()+"<br>")    #<p id="randomtext"><small>   +'</small></p>'

        def FormatSizes(row) -> str:
            info=""
            if row.Size > 0 or row.Pages > 0:
                info="<small>("
                if row.Size > 0:
                    info+="{:,.1f}".format(row.Size/(1024**2))+'&nbsp;MB'
                if row.Pages > 0:
                    if row.Size > 0:
                        info+="; "
                    info+=str(row.Pages)+" pp"
                info+=")</small>"
            return info

        showExtensions=self.radioBoxShowExtensions.GetSelection() != 0
        def MaybeSuppressPDFExtension(fn: str, suppress: bool) -> str:
            if suppress:
                parts=os.path.splitext(row.DisplayTitle)
                if parts[1].lower() in [".pdf", ".jpg", ".png", ".doc", ".docx"]:
                    fn = parts[0]
            return fn

        if self.radioBoxFileListFormat.GetSelection() == 0: # Are we to output a table?
            # Now construct the table which we'll then substitute.
            newtable='<table class="table"  id="conpagetable">\n'
            newtable+="  <thead>\n"
            newtable+="    <tr>\n"
            newtable+='      <th scope="col">Document</th>\n'
            newtable+='      <th scope="col">Size</th>\n'
            newtable+='      <th scope="col">Notes</th>\n'
            newtable+='    </tr>\n'
            newtable+='  </thead>\n'
            newtable+='  <tbody>\n'
            for i, row in enumerate(self.Datasource.Rows):
                newtable+="    <tr>\n"
                # Display title column
                if row.IsTextRow:
                    newtable+='      <td colspan="3">'+row.SourceFilename+" "+row.SiteFilename+" "+row.DisplayTitle+" "+row.Notes+'</td>\n'
                elif row.IsLinkRow:
                    newtable+='      <td colspan="3">'+FormatLink(row.URL, row.DisplayTitle)+'</td>\n'
                else:   # Ordinary row
                    # The document title/link column
                    s=MaybeSuppressPDFExtension(row.DisplayTitle, showExtensions)
                    newtable+='      <td>'+FormatLink(row.SiteFilename, s)+'</td>\n'

                    # This is the size & page count column
                    newtable+='      <td>'+FormatSizes(row)+'</td>\n'

                    # Notes column
                    info='      <td> </td>\n'
                    if len(row.Notes) > 0:
                        info='      <td>'+str(row.Notes)+'</td>\n'
                    newtable+=info

                newtable+="    </tr>\n"
            newtable+="    </tbody>\n"
            newtable+="  </table>\n"
        else:   # Output a list
            # Construct a list which we'll then substitute.
            newtable='<ul  id="conpagetable">\n'
            for row in self.Datasource.Rows:
                if row.IsTextRow:
                    text=row.SourceFilename+" "+row.SiteFilename+" "+row.DisplayTitle+" "+row.Notes
                    newtable+='    </ul><b>'+text.strip()+'</b><ul id="conpagetable">\n'
                elif row.IsLinkRow:
                    newtable+='    <li id="conpagetable">'+FormatLink(row.URL, row.DisplayTitle)+"</li>\n"
                else:
                    s=MaybeSuppressPDFExtension(row.DisplayTitle, showExtensions)
                    newtable+='    <li id="conpagetable">'+FormatLink(row.SiteFilename, s)

                    val=FormatSizes(row)
                    if len(val) > 0:
                        newtable+='&nbsp;&nbsp;'+val+'\n'
                    else:
                        newtable+='&nbsp;&nbsp;(--)\n'

                    # Notes
                    if len(row.Notes) > 0:
                        newtable+="&nbsp;&nbsp;("+str(row.Notes)+")"
                    newtable+="</li>\n"

            newtable+="  </ul>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)

        if not FTP().PutFileAsString("/"+self._seriesname+"/"+self._coninstancename, "index.html", file, create=True):
            Log("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            wx.MessageBox("OnUploadConInstancePage: Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            ProgressMessage(self).Close()
            return

        wd="/"+self._seriesname+"/"+self._coninstancename
        FTP().CWD(wd)
        for delta in self.conInstanceDeltaTracker.Deltas:
            if delta.Verb == "add":
                ProgressMessage(self).Show("Adding "+delta.Con.SourcePathname+" as "+delta.Con.SiteFilename)
                Log("delta-ADD: "+delta.Con.SourcePathname+" as "+delta.Con.SiteFilename)
                FTP().PutFile(delta.Con.SourcePathname, delta.Con.SiteFilename)
            elif delta.Verb == "rename":
                ProgressMessage(self).Show("Renaming "+delta.Oldname+ " to "+delta.Con.SiteFilename)
                Log("delta-RENAME: "+delta.Oldname+" to "+delta.Con.SiteFilename)
                if len(delta.Oldname.strip()) == 0:
                    Log("***Renaming an blank name can't be right! Ignored",isError=True)
                    continue
                FTP().Rename(delta.Oldname, delta.Con.SiteFilename)
            elif delta.Verb == "delete":
                if not delta.Con.IsTextRow and not delta.Con.IsLinkRow:
                    ProgressMessage(self).Show("Deleting "+delta.Con.SiteFilename)
                    Log("delta-DELETE: "+delta.Con.SiteFilename)
                    if len(delta.Con.SiteFilename.strip()) > 0:
                        FTP().DeleteFile(delta.Con.SiteFilename)
            elif delta.Verb == "replace":
                ProgressMessage(self).Show("Replacing "+delta.Oldname+" with new/updated file")
                Log("delta-REPLACE: "+delta.Con.SourcePathname+" <-- "+delta.Oldname)
                Log("   delta-DELETE: "+delta.Con.SiteFilename)
                if len(delta.Con.SiteFilename.strip()) > 0:
                    FTP().DeleteFile(delta.Con.SiteFilename)
                Log("   delta-ADD: "+delta.Con.SourcePathname+" as "+delta.Con.SiteFilename)
                FTP().PutFile(delta.Con.SourcePathname, delta.Con.SiteFilename)
            else:
                Log("delta-UNRECOGNIZED: "+str(delta))

        UpdateLog().Log(self._seriesname, self._coninstancename, self.conInstanceDeltaTracker)

        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()  # The upload is complete. Start tracking changes afresh

        ProgressMessage(self).Show("Upload succeeded: /"+self._seriesname+"/"+self._coninstancename+"/index.html", close=True, delay=0.5)
        self.MarkAsSaved()
        self.Uploaded=True
        self.RefreshWindow()


    #------------------
    # Download a ConInstance
    def DownloadConInstancePage(self) -> None:
        # Clear out any old information
        self.Datasource=ConInstancePage()

        # Read the existing CIP
        ProgressMessage(self).Show("Downloading "+self._FTPbasedir+"/"+self._coninstancename+"/index.html")
        file=FTP().GetFileAsString(self._FTPbasedir+"/"+self._coninstancename, "index.html")
        if file is None:
            Log("DownloadConInstancePage: "+self._FTPbasedir+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            #wx.MessageBox(self._FTPbasedir+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            ProgressMessage(self).Close()
            return  # Just return with the ConInstance page empty

        # Get the JSON
        j=FindBracketedText(file, "fanac-json", stripHtml=False)[0]
        if j is not None and j != "":
            self.FromJson(j)

        self.Title="Editing "+self._coninstancename

        ProgressMessage(self).Show(self._FTPbasedir+"/"+self._coninstancename+"/index.html downloaded", close=True, delay=0.5)
        self._grid.MakeTextLinesEditable()
        self.MarkAsSaved()
        self.RefreshWindow()


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_GridPopup)

        self.m_popupAddFiles.Enabled=True
        self.m_popupInsertText.Enabled=True
        self.m_popupInsertLink.Enabled=True

        if event.GetRow() < self.Datasource.NumRows:
            self.m_popupDeleteRow.Enabled=True

        if self.Datasource.ColDefs[self._grid.clickedColumn].IsEditable == "maybe":
            self.m_popupAllowEditCell.Enabled=True

        if self._grid.clickedColumn == 0 and self._grid.clickedRow < self._grid.NumRows:
            if self._grid.clickedRow < self.Datasource.NumRows and \
                    not self.Datasource.Rows[self._grid.clickedRow].IsTextRow and \
                    not self.Datasource.Rows[self._grid.clickedRow].IsLinkRow:
                self.m_popupUpdateFile.Enabled=True

        self.PopupMenu(self.m_GridPopup, pos=self.gRowGrid.Position+event.Position)

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
        self.RefreshWindow()

    # ------------------
    def OnPopupInsertLink(self, event):
        irow=self._grid.clickedRow
        if irow > self.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)   # Insert empty rows into the datasource if necessary to keep things in sync
        self._grid.InsertEmptyRows(irow, 1)
        self.Datasource.Rows[irow].IsLinkRow=True
        for icol in range(self._grid.NumCols):
            self._grid.AllowCellEdit(irow, icol)
        self.RefreshWindow()

    # ------------------
    def OnPopupAllowEditCell(self, event):
        # Append a (row, col) tuple. This only lives for the life of this instance.
        self._grid.AllowCellEdit(self._grid.clickedRow, self._grid.clickedColumn)
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
        self.RefreshWindow()


    # ------------------
    # The grid's contents have changed.  Update the Datasource and record a Delta if needed
    def OnGridCellChanged(self, event):
        row=event.GetRow()
        col=event.GetCol()
        if row >= self.Datasource.NumRows:    # Ignore (and thus reject) data entry beyond the last Datasource row.  (Rows must be added using AddFiles or new Text Line, etc)
            event.Veto()
            return

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
                self.RefreshWindow()

            if originalfname != newfname:
                self.conInstanceDeltaTracker.Rename(self.Datasource.Rows[row], originalfname)
        else:
            self._grid.OnGridCellChanged(event)
            if self.Datasource.Rows[row].IsLinkRow and col == 0:
                # We do some fiddling with the incoming URLs
                if not self.Datasource.Rows[row].URL.lower().startswith("http"):
                    self.Datasource[row][col]="https://"+self.Datasource.Rows[row].URL

            self.RefreshWindow()

    # ------------------
    def OnGridEditorShown(self, event):
        self._grid.OnGridEditorShown(event)

    # ------------------
    def OnTextConInstanceName(self, event):
        self.RefreshWindow()

    # ------------------
    def OnTextConInstanceNameKeyUp(self, event):
        self.ConInstanceFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConInstanceName.GetValue().strip())
        self.RefreshWindow()

    # ------------------
    def OnTextConInstanceFancyURL(self, event):
        self.RefreshWindow()

    # ------------------
    def OnTopTextComments(self, event):
        self.RefreshWindow()

    # ------------------
    def OnTextConInstanceCredits(self, event):
        self.RefreshWindow()

    # ------------------
    def OnRadioFileListFormat(self, event):
        Settings().Put("ConInstanceFramePage:File list format", self.radioBoxFileListFormat.GetSelection())

    # ------------------
    def OnRadioShowExtensions(self, event):
        Settings().Put("ConInstanceFramePage:Show Extensions", self.radioBoxShowExtensions.GetSelection())

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshWxGridFromDatasource()
        self.UpdateNeedsSavingFlag()

