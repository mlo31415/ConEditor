from __future__ import annotations
from typing import Optional

import wx
import os
import sys
import json
from datetime import date
import time
from PyPDF4 import PdfFileReader

from GenConInstanceFrame import GenConInstanceFrame
from DataGrid import DataGrid, Color
from ConInstance import ConInstancePage, ConFile
from ConInstanceDeltaTracker import ConInstanceDeltaTracker
from FTP import FTP
from Settings import Settings
from Log import Log

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, PrependHTTP, RemoveHTTP, ExtensionMatches
from WxHelpers import ProgressMessage


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
        self._grid.Datasource=ConInstancePage()

        self._grid.HideRowLabels()

        self._FTPbasedir=basedirFTP
        self._seriesname=seriesname
        self._coninstancename=coninstancename

        self._signature=0

        # A list of changes to the file stored on the website which will need to be made upon upload.
        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()

        self._uploaded=False    # Has this instance been uploaded? (This is needed to generate the return value from the dialog.)

        val=Settings().Get("ConInstanceFramePage:File list format")
        if val is not None:
            self.radioBoxFileListFormat.SetSelection(int(val))

        self._grid.Datasource.SpecialTextColor=None

        self.DownloadConInstancePage()

        self.SetEscapeId(wx.ID_CANCEL)

        self.MarkAsSaved()
        self.RefreshWindow()


    # ----------------------------------------------
    # Used to determine if anything has been updated
    def Signature(self) -> int:
        stuff=self.ConInstanceName.strip()+self.ConInstanceTopText.strip()+self.ConInstanceFancyURL.strip()
        return hash(stuff)+self._grid.Signature()

    def MarkAsSaved(self):
        Log("ConInstancePage.MarkAsSaved -- "+str(self.Signature()))
        self._signature=self.Signature()

    def NeedsSaving(self):
        if self._signature != self.Signature():
            Log("ConInstancePage.NeedsSaving -- "+str(self._signature)+" != "+str(self.Signature()))
        return self._signature != self.Signature()


    # ----------------------------------------------
    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 3,
           "ConInstanceName": self.ConInstanceName,
           "ConInstanceStuff": self.ConInstanceTopText,
           "ConInstanceFancyURL": self.ConInstanceFancyURL,
           "_datasource": self._grid.Datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> GenConInstanceFrame:
        d=json.loads(val)
        self.ConInstanceName=d["ConInstanceName"]
        self.ConInstanceTopText=d["ConInstanceStuff"]
        self.ConInstanceFancyURL=d["ConInstanceFancyURL"]
        self.ConInstanceFancyURL=RemoveHTTP(self.ConInstanceFancyURL)
        self._grid.Datasource=ConInstancePage().FromJson(d["_datasource"])
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
    def ConInstanceFancyURL(self) -> str:
        return self.tConInstanceFancyURL.GetValue()

    @ConInstanceFancyURL.setter
    def ConInstanceFancyURL(self, val: str) -> None:
        if val != self.tConInstanceFancyURL.GetValue():
            self.tConInstanceFancyURL.SetValue(val)

    # ----------------------------------------------
    def OnAddFilesButton(self, event):
        self.AddFiles()

    def AddFiles(self) -> bool:

        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog (None, "Select files to upload", ".", "", "*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)

        # Do we have a last directory?
        dir=Settings().Get("Last FileDialog directory")
        if dir is not None:
            if not os.path.exists(dir) or not os.path.isdir(dir):
                Log("AddFiles: SetDirectory("+dir+") failed because the directory does not exist")
                dlg.Destroy()
                return  False
            dlg.SetDirectory(dir)

        if dlg.ShowModal() == wx.ID_CANCEL:
            Settings().Put("Last FileDialog directory", dlg.GetDirectory())
            dlg.Destroy()
            return True #TODO: Is this the correct return?

        Settings().Put("Last FileDialog directory", dlg.GetDirectory())
        for fn in dlg.GetFilenames():
            conf=ConFile()
            conf.DisplayTitle=fn
            conf.SiteFilename=fn
            conf.SourceFilename=fn
            conf.LocalPathname=os.path.join(os.path.join(dlg.GetDirectory()), fn)
            conf.Size=os.path.getsize(conf.LocalPathname)
            conf.Pages=GetPdfPageCount(conf.LocalPathname)
            self.conInstanceDeltaTracker.Add(conf)
            self._grid.Datasource.Rows.append(conf)

        dlg.Destroy()
        self.RefreshWindow()
        return True


    # ----------------------------------------------
    def OnUploadConInstance(self, event):
        self.OnUploadConInstancePage()

    # ----------------------------------------------
    def OnClose(self, event):
        if self.NeedsSaving():
            if type(event) == wx._core.CommandEvent:  # When the close event is an ESC or the ID_Cancel button, it's not a vetoable event, so it needs to be handled separately
                resp=wx.MessageBox("This file list has been updated and not yet saved. Exit anyway?", 'Warning',
                                   wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    return
            elif event.CanVeto():
                resp=wx.MessageBox("This file list has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return

        self.EndModal(wx.ID_OK if self.Uploaded else wx.ID_CANCEL)

    # ----------------------------------------------
    # With V7 of the ConInstance file format we added page counts for PDFs.  Existing entries lack page counts.
    # Run through the list of files, and for each PDF see if it is missing a page count.
    # If it is, see if the file is locally available.
    # If it is, check the page count and add it to the table.
    def FillInMissingPDFPageCounts(self):
        for i, row in enumerate(self._grid.Datasource.Rows):
            if not row.IsText and not row.IsLink:
                if row.Pages is None or  row.Pages == 0:
                    if ExtensionMatches(row.LocalPathname, ".pdf"):
                        if os.path.exists(row.LocalPathname):
                            row.Pages=GetPdfPageCount(row.LocalPathname)
                            self._grid.Datasource.Rows[i]=row



    # ----------------------------------------------
    def OnUploadConInstancePage(self) -> None:

        # Delete any trailing blank rows.  (Blank rows anywhere are as error, but we only silently drop trailing blank rows.)
        # Find the last non-blank row.
        last=None
        for i, row in enumerate(self._grid.Datasource.Rows):
            if len((row.SourceFilename+row.SiteFilename+row.DisplayTitle+row.Notes).strip()) > 0:
                last=i
        # Delete the row or rows following it
        if last is not None and last < self._grid.Datasource.NumRows-1:
            del self._grid.Datasource.Rows[last+1:]

        # Check to see if the data is valid
        error=False
        for i, row in enumerate(self._grid.Datasource.Rows):
            # Valid data requires
            #   If a text row, that some text exists
            #   If an external link row, that text and a properly formed URL exists (but does not check to see target exists)
            #   For a file, that there is an entry in the "Source File Name", "Site Name", and "Display Name" columns
            if row.IsText:
                if len((row.SourceFilename+row.SiteFilename+row.DisplayTitle+row.Notes).strip()) == 0:
                    error=True
                    Log("Malformed text row: #"+str(i)+"  "+ str(row))
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
            elif row.IsLink:
                if len(row.URL.strip()) == 0  or len(row.DisplayTitle.strip()) == 0:
                    error=True
                    Log("Malformed link row: #"+str(i)+"  "+ str(row))
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
            else:
                if len(row.SourceFilename.strip()) == 0 or len(row.SiteFilename.strip()) == 0 or len(row.DisplayTitle.strip()) == 0:
                    error=True
                    Log("Malformed file row: #"+str(i)+"  "+ str(row))
                    for j in range(self._grid.NumCols):
                        self._grid.SetCellBackgroundColor(i, j, Color.Pink)
        if error:
            self._grid.Grid.ForceRefresh()
            wx.MessageBox("Malformed row found")
            return


        # Read in the template
        file=None
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConPage.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConPage.html'")
            Log("Can't read 'Template-ConPage.html'")
            return

        ProgressMessage(self).Show("Uploading /"+self._seriesname+"/"+self._coninstancename+"/index.html")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        fancylink=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName), self.ConInstanceName)
        file=SubstituteHTML(file, "title", self.ConInstanceName)
        file=SubstituteHTML(file, "fanac-instance", fancylink)
        file=SubstituteHTML(file, "fanac-stuff", self.ConInstanceTopText)

        # Fill in the top buttons
        s="<button onclick=\"window.location.href='http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName)+"'\"> Fancyclopedia 3 </button>&nbsp;&nbsp;"+ \
        "<button onclick=\"window.location.href='..'\">All "+self._seriesname+"s</button>"
        file=SubstituteHTML(file, "fanac-topbuttons", s)

        # If there are missing page counts for pdfs, try to gett hem. (This can eventually be eliminated as there will be no pre-V7 files on the server.)
        self.FillInMissingPDFPageCounts()

        file=SubstituteHTML(file, "fanac-json", self.ToJson())
        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y")+" EST")

        def FormatSizes(row) -> str:
            info=""
            if row.Size > 0 or (row.Pages is not None and row.Pages > 0):
                info="<small>("
                if row.Size > 0:
                    info+="{:,.1f}".format(row.Size/(1024**2))+'&nbsp;MB'
                if row.Pages is not None and row.Pages > 0:
                    if row.Size > 0:
                        info+="; "
                    info+=str(row.Pages)+" pp"
                info+=")</small>"
            return info

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
            for i, row in enumerate(self._grid.Datasource.Rows):
                newtable+="    <tr>\n"
                # Display title column
                if row.IsText:
                    newtable+='      <td colspan="3">'+row.SourceFilename+" "+row.SiteFilename+" "+row.DisplayTitle+" "+row.Notes+'</td>\n'
                elif row.IsLink:
                    newtable+='      <td colspan="3">'+FormatLink(row.URL, row.DisplayTitle)+'</td>\n'
                else:
                    # The document title/link column
                    newtable+='      <td>'+FormatLink(row.SiteFilename, row.DisplayTitle)+'</td>\n'

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
            for row in self._grid.Datasource.Rows:
                if row.IsText:
                    text=row.SourceFilename+" "+row.SiteFilename+" "+row.DisplayTitle+" "+row.Notes
                    newtable+='    </ul><b>'+text.strip()+'</b><ul id="conpagetable">\n'
                elif row.IsLink:
                    newtable+='    <li id="conpagetable">'+FormatLink(row.URL, row.DisplayTitle)+"</li>\n"
                else:
                    newtable+='    <li id="conpagetable">'+FormatLink(row.SiteFilename, row.DisplayTitle)

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
            if delta[0] == "add":
                ProgressMessage(self).Show("Adding "+delta[1].LocalPathname+" as "+delta[1].SiteFilename)
                FTP().PutFile(delta[1].LocalPathname, delta[1].SiteFilename)
            elif delta[0] == "rename":
                ProgressMessage(self).Show("Renaming "+delta[2]+ " to "+delta[1].SiteFilename)
                FTP().Rename(delta[2], delta[1].SiteFilename)
            elif delta[0] == "delete":
                if not delta[1].IsText and not delta[1].IsLink:
                    ProgressMessage(self).Show("Deleting "+delta[1].SiteFilename)
                    Log("delta-DELETE: "+delta[1].SiteFilename)
                    FTP().DeleteFile(delta[1].SiteFilename)
            else:
                Log("delta-UNRECOGNIZED: "+str(delta))

        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()  # The upload is complete. Start tracking changes afresh

        ProgressMessage(self).Show("Upload succeeded: /"+self._seriesname+"/"+self._coninstancename+"/index.html", close=True, delay=0.5)
        self.MarkAsSaved()
        self.Uploaded=True
        self.RefreshWindow()


    #------------------
    # Download a ConInstance
    def DownloadConInstancePage(self) -> None:

        # Clear out any old information
        self._grid.Datasource=ConInstancePage()

        # Read the existing CIP
        ProgressMessage(self).Show("Downloading "+self._FTPbasedir+"/"+self._coninstancename+"/index.html")
        file=FTP().GetFileAsString(self._FTPbasedir+"/"+self._coninstancename, "index.html")
        if file is None:
            Log("DownloadConInstancePage: "+self._FTPbasedir+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            #wx.MessageBox(self._FTPbasedir+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            ProgressMessage(self).Close()
            return  # Just return with the ConInstance page empty

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is not None and j != "":
            self.FromJson(j)

        self.Title="Editing "+self._coninstancename

        ProgressMessage(self).Show(self._FTPbasedir+"/"+self._coninstancename+"/index.html downloaded", close=True, delay=0.5)
        self._grid.MakeTextLinesEditable()
        self.MarkAsSaved()
        self.RefreshWindow()


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()

        self.m_popupAddFiles.Enabled=True
        self.m_popupInsertText.Enabled=True
        self.m_popupInsertLink.Enabled=True

        if self._grid.Datasource.NumRows > event.GetRow():
            self.m_popupDeleteFile.Enabled=True

        if self._grid.Datasource.ColEditable[self.clickedColumn] == "maybe":
            self.m_popupAllowEditCell.Enabled=True

        self.PopupMenu(self.m_menuPopup, pos=self.gRowGrid.Position+event.Position)

    # -------------------
    def OnKeyDown(self, event):
        self._grid.OnKeyDown(event)

    # -------------------
    def OnKeyUp(self, event):
        self._grid.OnKeyUp(event)

    # ------------------
    def OnPopupCopy(self, event):
        self._grid.OnPopupCopy(event)

    # ------------------
    def OnPopupPaste(self, event):
        self._grid.OnPopupPaste(event)

    # ------------------
    def OnPopupInsertText(self, event):
        irow=self._grid.rightClickedRow
        if irow >= self._grid.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)   # Insert empty rows into the datasource if necessary to keep things in sync
        self._grid.InsertEmptyRows(irow, 1)
        self._grid.Datasource.Rows[irow].IsText=True    #TODO: Add similar code for IsLink
        self._grid._grid.SetCellSize(irow, 0, 1, self._grid.NumCols)
        for icol in range(self._grid.NumCols):
            self._grid.AllowCellEdit(irow, icol)
        self.RefreshWindow()
        event.Skip()

    # ------------------
    def OnPopupInsertLink(self, event):
        irow=self._grid.rightClickedRow
        if irow >= self._grid.Datasource.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)   # Insert empty rows into the datasource if necessary to keep things in sync
        self._grid.InsertEmptyRows(irow, 1)
        self._grid.Datasource.Rows[irow].IsLink=True
        for icol in range(self._grid.NumCols):
            self._grid.AllowCellEdit(irow, icol)
        self.RefreshWindow()
        event.Skip()

    # ------------------
    def OnPopupAllowEditCell(self, event):
        irow=self._grid.rightClickedRow
        icol=self._grid.rightClickedColumn
        self._grid.AllowCellEdit(irow, icol)  # Append a (row, col) tuple. This only lives for the life of this instance.
        self.RefreshWindow()

    # ------------------
    def OnPopupAddFiles(self, event):
        self.AddFiles()

    # ------------------
    def OnPopupDeleteFile(self, event):
        if self._grid.HasSelection():
            top, left, bottom, right=self._grid.LocateSelection()
            nrows=self._grid.Datasource.NumRows
            if top >= nrows:
                top=nrows-1
            if bottom >= nrows:
                bottom=nrows-1
        else:
            if self._grid.rightClickedRow >= self._grid.Datasource.NumRows:
                return
            top=bottom=self._grid.rightClickedRow

        self._grid.Grid.ClearSelection()

        for row in self._grid.Datasource.Rows[top:bottom+1]:
            self.conInstanceDeltaTracker.Delete(row)
        del self._grid.Datasource.Rows[top:bottom+1]
        self._grid.Datasource.AllowCellEdits=[x for x in self._grid.Datasource.AllowCellEdits if x[0] >= top or x[0] < bottom+1]
        self.RefreshWindow()


    # ------------------
    def OnGridCellChanged(self, event):
        row=event.GetRow()
        col=event.GetCol()
        if row >= self._grid.Datasource.NumRows:    # Ignore (and thus reject) data entry beyond the last Datasource row.  (Rows must be added using AddFiles or new Text Line, etc)
            event.Veto()
            return

        if self._grid.Datasource.ColHeaders[col] == "Site Name":    # Editing the filename on the Conpubs site
            originalfname=self._grid.Datasource.GetData(row, col)
            _, oext=os.path.splitext(originalfname)
            self._grid.OnGridCellChanged(event)
            newfname=self._grid.Datasource.GetData(row, col)
            # If we don't allow extensions to be edited (the default), restore the old extension before proceeding.
            if not self.m_checkBoxAllowEditExtentions.IsChecked():
                newname, _=os.path.splitext(newfname)
                newfname=newname+oext
                self._grid.Datasource.SetDataVal(row, col, newfname)
                self.RefreshWindow()

            if originalfname != newfname:
                self.conInstanceDeltaTracker.Rename(self._grid.Datasource.Rows[row], originalfname)
        else:
            self._grid.OnGridCellChanged(event)
            self.RefreshWindow()

    # ------------------
    def OnGridEditorShown(self, event):
        irow=event.GetRow()
        icol=event.GetCol()
        if self._grid.Datasource.ColEditable[icol] == "no":
            event.Veto()
            return
        if self._grid.Datasource.ColEditable[icol] == "maybe":
            for it in self._grid.Datasource.AllowCellEdits:
                if (irow, icol) == it:
                    return
            event.Veto()
        return

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
    def OnRadioFileListFormat(self, event):
        Settings().Put("ConInstanceFramePage:File list format", str(self.radioBoxFileListFormat.GetSelection()))

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self.NeedsSaving():
            s=s+" *"
        self.Title=s
