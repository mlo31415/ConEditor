import wx
import os
import sys
import json
import math
from datetime import date

from GenConInstanceFrame import GenConInstanceFrame
from Grid import Grid
from ConInstance import ConInstancePage, ConFile
from FTP import FTP
from Settings import Settings
from Log import Log

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, PrependHTTP

#####################################################################################
class MainConInstanceDialogClass(GenConInstanceFrame):

    def __init__(self, basedirFTP, seriesname, coninstancename):
        GenConInstanceFrame.__init__(self, None)
        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConInstancePage()

        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(self._grid._datasource.ColDataTypes)
        self._grid._grid.HideRowLabels()

        self._FTPbasedir=basedirFTP
        self._seriesname=seriesname
        self._coninstancename=coninstancename
        self.ConInstanceName=""
        self.ConInstanceStuff=""
        self.ConInstanceFancyURL=""
        self.ConInstancePhotoURL=""

        self._updated=False
        self._uploaded=False    # Has this instance been uploaded? (This is needed to generate the return value from the dialog.)

        val=Settings().Get("ConInstanceFramePage:File list format")
        if val is not None:
            self.radioBoxFileListFormat.SetSelection(int(val))

        self.DownloadConInstancePage()

        self.RefreshWindow()
        self.ReturnValue=None


    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 2,
           "ConInstanceName": self.ConInstanceName,
           "ConInstanceStuff": self.ConInstanceStuff,
           "ConInstanceFancyURL": self.ConInstanceFancyURL,
           "ConInstancePhotoURL": self.ConInstancePhotoURL,
           "_datasource": self._grid._datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> GenConInstanceFrame:
        d=json.loads(val)
        self.ConInstanceName=d["ConInstanceName"]
        self.ConInstanceStuff=d["ConInstanceStuff"]
        self.ConInstanceFancyURL=d["ConInstanceFancyURL"]
        self._grid._datasource=ConInstancePage().FromJson(d["_datasource"])
        self.ConInstancePhotoURL=d["ConInstancePhotoURL"]
        return self


    @property
    def Updated(self) -> bool:
        return self._updated or (self._grid._datasource.Updated is not None and self._grid._datasource.Updated)
    @Updated.setter
    def Updated(self, val: bool) -> None:
        self._updated=val
        if val == False:    # If we're setting the updated flag to False, set the grid's flag, too.
            self._grid._datasource.Updated=False


    def OnAddFilesButton(self, event):
        self.AddFiles()

    def AddFiles(self) -> bool:

        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select files to upload", ".", "", "*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)

        # Do we have a last directory?
        dir=Settings().Get("Last FileDialog directory")
        if dir is not None:
            if not os.path.exists(dir) or not os.path.isdir(dir):
                Log("AddFiles: SetDirectory("+dir+") failed because the directory does not exist")
                return  False
            dlg.SetDirectory(dir)

        if dlg.ShowModal() == wx.ID_CANCEL:
            Settings().Put("Last FileDialog directory", dlg.GetDirectory())
            dlg.Raise()
            dlg.Destroy()
            return True #TODO: Is this the correct return?

        Settings().Put("Last FileDialog directory", dlg.GetDirectory())
        for fn in dlg.GetFilenames():
            conf=ConFile()
            conf.DisplayTitle=fn
            conf.LocalPathname=os.path.join(os.path.join(dlg.Directory), fn)
            conf.Filename=fn
            conf.Size=os.path.getsize(conf.LocalPathname)
            self._grid._datasource.Rows.append(conf)
            self._grid._datasource.Updated=True
        dlg.Destroy()
        self.RefreshWindow()
        return True

    def OnUploadConInstance(self, event):
        self.OnUploadConInstancePage()


    def OnClose(self, event):
        if self.Updated:
            if event.CanVeto():
                resp=wx.MessageBox("This file list has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return

        if self._grid._datasource.NumRows > 0 or self._uploaded:
            self.ReturnValue=wx.ID_OK
        if self.ReturnValue is None:
            self.ReturnValue=wx.ID_CANCEL
        self.EndModal(self.ReturnValue)


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
        file=SubstituteHTML(file, "fanac-stuff", self.ConInstanceStuff)
        file=SubstituteHTML(file, "fanac-linkupwards", FormatLink("..", "All "+self._seriesname+"s"))

        # Are there photos?\\
        if self.ConInstancePhotoURL is not None and len(self.ConInstancePhotoURL) > 0:
            link=FormatLink(PrependHTTP(self.ConInstancePhotoURL), "Convention Photos")
            file=SubstituteHTML(file, "fanac-photos", link)

        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        if self.radioBoxFileListFormat.GetSelection() == 0:
            # Now construct the table which we'll then substitute.
            newtable='<table class="table">\n'
            newtable+="  <thead>\n"
            newtable+="    <tr>\n"
            newtable+='      <th scope="col">Document</th>\n'
            newtable+='      <th scope="col">Size</th>\n'
            newtable+='      <th scope="col">Notes</th>\n'
            newtable+='    </tr>\n'
            newtable+='  </thead>\n'
            newtable+='  <tbody>\n'
            for i, row in enumerate(self._grid._datasource.Rows):
                newtable+="    <tr>\n"
                if len(row.Filename) > 0:
                    newtable+='      <td>'+FormatLink(row.Filename, row.DisplayTitle)+'</td>\n'
                    if row.Size > 0:
                        newtable+='      <td>'+"{:,.1f}".format(row.Size/(1024**2))+'&nbsp;MB</td>\n'
                    else:
                        newtable+='      <td>--</td>\n'
                    newtable+='      <td>'+str(row.Notes)+'</td>\n'
                else:
                    newtable+='    <td><b>'+row.DisplayTitle+'</b></td>\n'
                newtable+="    </tr>\n"
            newtable+="    </tbody>\n"
            newtable+="  </table>\n"
        else:
            # Construct a list which we'll then substitute.
            newtable="<ul>"
            for row in self._grid._datasource.Rows:
                if len(row.Filename) > 0:
                    newtable+="    <li>"+FormatLink(row.Filename, row.DisplayTitle)
                    if row.Size > 0:
                        newtable+="&nbsp;&nbsp;("+"{:,.1f}".format(row.Size/(1024**2))+'&nbsp;MB)</td>\n'
                    else:
                        newtable+='&nbsp;&nbsp;(--)\n'
                    newtable+="&nbsp;&nbsp;"+str(row.Notes)+"</li>\n"
                else:
                    newtable+='    </ul><b>'+row.DisplayTitle+'</b><ul>\n'

            newtable+="  </ul>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)

        if not FTP().PutFileAsString("/"+self._seriesname+"/"+self._coninstancename, "index.html", file, create=True):
            self.ProgressMessage("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            wx.MessageBox("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            Log("Upload failed: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
            return

        # Finally, Upload any files which are newly added.
        for row in self._grid._datasource.Rows:
            if row.Filename is not None and len(row.Filename) > 0:
                if not FTP().Exists(row.Filename):
                    if not FTP().PutFile(row.LocalPathname, row.Filename):
                        Log("OnUploadConInstancePage: Putfile of "+row.LocalPathname+" failed")

        # And remove any that have been dropped.  (PDFs only, for now.)
        files=[row.Filename for row in self._grid._datasource.Rows]
        fileupthere=FTP().g_ftp.nlst()
        for f in fileupthere:
            if f not in files:
                if os.path.splitext(f)[1] == ".pdf":
                    if not FTP().Delete(f):
                        Log("OnUploadConInstancePage: Delete("+f+") failed")

        self.ProgressMessage("Upload succeeded: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
        Log("Upload succeeded: /"+self._seriesname+"/"+self._coninstancename+"/index.html")
        self.Updated=False
        self._uploaded=True
        self.RefreshWindow()


    #------------------
    # Download a ConInstance
    def DownloadConInstancePage(self) -> None:

        # Clear out any old information
        self._grid._datasource=ConInstancePage()

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
        self.tConInstanceFancyURL.Value=self.ConInstanceFancyURL
        self.m_textPhotosURL.Value=self.ConInstancePhotoURL

        self.ProgressMessage(self._FTPbasedir+"/"+self._coninstancename+"/index.html downloaded")
        Log(self._FTPbasedir+"/"+self._coninstancename+"/index.html downloaded")
        self.Updated=False
        self.RefreshWindow()



    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()

        self.m_popupAddFiles.Enabled=True

        if self._grid._datasource.NumRows > event.GetRow():
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
    def OnPopupAddFiles(self, event):
        self.AddFiles()

    # ------------------
    def OnPopupDeleteFile(self, event):
        if self._grid.HasSelection():
            top, left, bottom, right=self._grid.LocateSelection()
            nrows=self._grid._datasource.NumRows
            if top >= nrows:
                top=nrows-1
            if bottom >= nrows:
                bottom=nrows-1
        else:
            if self._grid.rightClickedRow >= self._grid._datasource.NumRows:
                return
            top=bottom=self._grid.rightClickedRow
        self._grid.Grid.ClearSelection()
        del self._grid._datasource.Rows[top:bottom+1]
        self._grid._datasource.Updated=True

        self.RefreshWindow()

    # ------------------
    def OnGridCellChanged(self, event):
        self._grid.OnGridCellChanged(event)

    # ------------------
    def OnTextConInstanceName(self, event):
        self.ConInstanceName=self.tConInstanceName.Value

    # ------------------
    def OnTextConInstanceNameKeyUp(self, event):
        self.tConInstanceFancyURL.Value="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConInstanceName.Value)
        self.Updated=True
        self.RefreshWindow()

    # ------------------
    def OnGridEditorShown(self, event):
        icol=event.GetCol()
        if icol == 0:   # Don't allow editing of the 1st column
            event.Veto()

    # ------------------
    def OnTextConInstanceFancyURL(self, event):
        self.ConInstanceFancyURL=self.tConInstanceFancyURL.Value
        self.Updated=True
        self.RefreshWindow()

    # ------------------
    def OnTextPhotosURL(self, event):
        self.ConInstancePhotoURL=self.m_textPhotosURL.Value
        self.Updated=True
        self.RefreshWindow()

    # ------------------
    def OnTextComments(self, event):
        self.ConInstanceStuff=self.topText.Value

    # ------------------
    def OnRadioFileListFormat(self, event):
        Settings().Put("ConInstanceFramePage:File list format", str(self.radioBoxFileListFormat.GetSelection()))
        self.Updated=True

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self.Updated:
            s=s+" *"
        self.Title=s

    # ------------------
    def ProgressMessage(self, s: str) -> None:  # ConInstanceFramePage
        self.m_status.Label=s