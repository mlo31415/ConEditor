import wx
import os
import sys
import json
from datetime import date

from GenConInstanceFrame import GenConInstanceFrame
from DataGrid import DataGrid, Color
from ConInstance import ConInstancePage, ConFile
from ConInstanceDeltaTracker import ConInstanceDeltaTracker
from FTP import FTP
from Settings import Settings
from Log import Log

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, PrependHTTP, RemoveHTTP

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

        self.MarkAsSaved()
        self.RefreshWindow()


    # ----------------------------------------------
    # Used to determine if anything has been updated
    def Signature(self) -> int:
        stuff=self.ConInstanceName.strip()+self.ConInstanceTopText.strip()+self.ConInstanceFancyURL.strip()+self.ConInstancePhotoURL.strip()
        return hash(stuff)+self._grid.Datasource.Signature()

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
        d={"ver": 2,
           "ConInstanceName": self.ConInstanceName,
           "ConInstanceStuff": self.ConInstanceTopText,
           "ConInstanceFancyURL": self.ConInstanceFancyURL,
           "ConInstancePhotoURL": self.ConInstancePhotoURL,
           "_datasource": self._grid.Datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> GenConInstanceFrame:
        d=json.loads(val)
        self.ConInstanceName=d["ConInstanceName"]
        self.ConInstanceTopText=d["ConInstanceStuff"]
        self.ConInstanceFancyURL=d["ConInstanceFancyURL"]
        self.ConInstanceFancyURL=RemoveHTTP(self.ConInstanceFancyURL)
        self._grid.Datasource=ConInstancePage().FromJson(d["_datasource"])
        self.ConInstancePhotoURL=d["ConInstancePhotoURL"]
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
    def ConInstancePhotoURL(self) -> str:
        return self.m_textPhotosURL.GetValue()

    @ConInstancePhotoURL.setter
    def ConInstancePhotoURL(self, val: str) -> None:
        if val != self.m_textPhotosURL.GetValue():
            self.m_textPhotosURL.SetValue(val)

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
            if event.CanVeto():
                resp=wx.MessageBox("This file list has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return

        self.EndModal(wx.ID_OK if self.Uploaded else wx.ID_CANCEL)

    # ----------------------------------------------
    def OnUploadConInstancePage(self) -> None:
        # First read in the template
        file=None
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConPage.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConPage.html'")
            Log("Can't read 'Template-ConPage.html'")
            return

        self.ProgressMessage("Uploading /"+self._seriesname+"/"+self._coninstancename+"/index.html")
        Log("Uploading /"+self._seriesname+"/"+self._coninstancename+"/index.html")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName), self.ConInstanceName)
        file=SubstituteHTML(file, "title", self.ConInstanceName)
        file=SubstituteHTML(file, "fanac-instance", link)
        file=SubstituteHTML(file, "fanac-headerlink", link)
        file=SubstituteHTML(file, "fanac-fancylink", link)
        file=SubstituteHTML(file, "fanac-stuff", self.ConInstanceTopText)
        file=SubstituteHTML(file, "fanac-linkupwards", FormatLink("..", "All "+self._seriesname+"s"))

        # Are there photos?
        if self.ConInstancePhotoURL is not None and len(self.ConInstancePhotoURL) > 0:
            link=FormatLink(PrependHTTP(self.ConInstancePhotoURL), self.ConInstanceName+" "+"Convention Photos")
            file=SubstituteHTML(file, "fanac-photolink", "<p>See the "+link+" page on fanac.org.")

        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        if self.radioBoxFileListFormat.GetSelection() == 0:
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
                if not row.IsText:
                    newtable+='      <td>'+FormatLink(row.SiteFilename, row.DisplayTitle)+'</td>\n'
                    if row.Size > 0:
                        newtable+='      <td>'+"{:,.1f}".format(row.Size/(1024**2))+'&nbsp;MB</td>\n'
                    else:
                        newtable+='      <td>--</td>\n'
                    newtable+='      <td>'+str(row.Notes)+'</td>\n'
                else:
                    text=row.SourceFilename+" "+row.SiteFilename+" "+row.DisplayTitle+" "+row.Notes
                    newtable+='    <td><i><b>'+text.strip()+'</b></i></td>\n'
                newtable+="    </tr>\n"
            newtable+="    </tbody>\n"
            newtable+="  </table>\n"
        else:
            # Construct a list which we'll then substitute.
            newtable='<ul  id="conpagetable">\n'
            for row in self._grid.Datasource.Rows:
                if not row.IsText:
                    newtable+='    <li id="conpagetable">'+FormatLink(row.SiteFilename, row.DisplayTitle)
                    if row.Size > 0:
                        newtable+="&nbsp;&nbsp;("+"{:,.1f}".format(row.Size/(1024**2))+'&nbsp;MB)</td>\n'
                    else:
                        newtable+='&nbsp;&nbsp;(--)\n'
                    if len(row.Notes) > 0:
                        newtable+="&nbsp;&nbsp;("+str(row.Notes)+")"
                    newtable+="</li>\n"
                else:
                    text=row.SourceFilename+" "+row.SiteFilename+" "+row.DisplayTitle+" "+row.Notes
                    newtable+='    </ul><b>'+text.strip()+'</b><ul id="conpagetable">\n'

            newtable+="  </ul>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)

        if not FTP().PutFileAsString("/"+self._seriesname+"/"+self._coninstancename, "index.html", file, create=True):
            self.ProgressMessage("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            wx.MessageBox("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            Log("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            return

        wd="/"+self._seriesname+"/"+self._coninstancename
        FTP().CWD(wd)
        for delta in self.conInstanceDeltaTracker.Deltas:
            if delta[0] == "add":
                Log("delta-ADD: "+delta[1].SiteFilename)
                FTP().PutFile(delta[1].LocalPathname, delta[1].SiteFilename)
            elif delta[0] == "rename":
                Log("delta-RENAME: "+delta[2]+ "  to "+delta[1].SiteFilename)
                FTP().Rename(delta[2], delta[1].SiteFilename)
            elif delta[0] == "delete":
                Log("delta-DELETE: "+delta[1].SiteFilename)
                FTP().DeleteFile(delta[1].SiteFilename)
            else:
                Log("delta-UNRECOGNIZED: "+str(delta))

        self.conInstanceDeltaTracker=ConInstanceDeltaTracker()  # The upload is complete. Start tracking changes afresh

        self.ProgressMessage("Upload succeeded: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
        Log("Upload succeeded: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
        self.MarkAsSaved()
        self.Uploaded=True
        self.RefreshWindow()


    #------------------
    # Download a ConInstance
    def DownloadConInstancePage(self) -> None:

        # Clear out any old information
        self._grid.Datasource=ConInstancePage()

        # Read the existing CIP
        self.ProgressMessage("Downloading "+self._FTPbasedir+"/"+self._coninstancename+"/index.html")
        Log("Downloading "+self._FTPbasedir+"/"+self._coninstancename+"/index.html")
        file=FTP().GetFileAsString(self._FTPbasedir+"/"+self._coninstancename, "index.html")
        if file is None:
            self.ProgressMessage(self._FTPbasedir+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            Log(self._FTPbasedir+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            return  # Just return with the ConInstance page empty

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is not None and j != "":
            self.FromJson(j)

        self.Title="Editing "+self._coninstancename

        self.ProgressMessage(self._FTPbasedir+"/"+self._coninstancename+"/index.html downloaded")
        Log(self._FTPbasedir+"/"+self._coninstancename+"/index.html downloaded")
        self.MarkAsSaved()
        self.RefreshWindow()


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()

        self.m_popupAddFiles.Enabled=True
        self.m_popupInsertText.Enabled=True

        if self._grid.Datasource.NumRows > event.GetRow():
            self.m_popupDeleteFile.Enabled=True

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
        self._grid.InsertEmptyRows(irow, 1)
        self._grid.Datasource.Rows[irow].IsText=True
        self._grid._grid.SetCellSize(irow, 0, 1, self._grid.Numcols)
        for icol in range(self._grid.Numcols):
            self._grid.Datasource.AllowCellEdits.append((irow, icol))
        self.RefreshWindow()
        event.Skip()

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

        self.RefreshWindow()

    # ------------------
    def OnGridCellChanged(self, event):
        row=event.GetRow()
        col=event.GetCol()
        if row >= self._grid.Datasource.NumRows:
            event.Veto()
            return

        if self._grid.Datasource.ColHeaders[col] == "Site Name":
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
    def OnTextPhotosURL(self, event):
        self.RefreshWindow()

    # ------------------
    def OnTextComments(self, event):
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

    # ------------------
    def ProgressMessage(self, s: str) -> None:  # ConInstanceFramePage
        self.m_status.Label=s