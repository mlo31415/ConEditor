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

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, Log

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

        self.LoadConInstancePage()

        self._grid.RefreshGridFromData()
        self.ReturnValue=None




    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 1,
           "ConInstanceName": self.ConInstanceName,
           "ConInstanceStuff": self.ConInstanceStuff,
           "ConInstanceFancyURL": self.ConInstanceFancyURL,
           "_datasource": self._grid._datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> GenConInstanceFrame:
        d=json.loads(val)
        if d["ver"] == 1:
            self.ConInstanceName=d["ConInstanceName"]
            self.ConInstanceStuff=d["ConInstanceStuff"]
            self.ConInstanceFancyURL=d["ConInstanceFancyURL"]
            self._grid._datasource=ConInstancePage().FromJson(d["_datasource"])
        return self


    def OnAddFilesButton(self, event):
        self.AddFiles()

    def AddFiles(self):
        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select files to upload", ".", "", "*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Raise()
            dlg.Destroy()
            return

        for fn in dlg.GetFilenames():
            conf=ConFile()
            conf.DisplayTitle=fn
            conf.LocalPathname=os.path.join(os.path.join(dlg.Directory), fn)
            conf.Filename=fn
            conf.Size=os.path.getsize(conf.LocalPathname)
            self._grid._datasource.Rows.append(conf)
        dlg.Destroy()
        self._grid.RefreshGridFromData()


    def OnSaveConInstance(self, event):
        self.SaveConInstancePage()
        self.ReturnValue=wx.ID_OK
        self.EndModal(self.ReturnValue)
        self.Close()

    def OnClose(self, event):
        if self._grid._datasource.NumRows > 0:
            self.ReturnValue=wx.ID_OK
        self.EndModal(self.ReturnValue)

    def SaveConInstancePage(self) -> None:
        # First read in the template
        file=None
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConPage.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConPage.html'")


        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName), self.ConInstanceName)
        file=SubstituteHTML(file, "title", self.ConInstanceName)
        file=SubstituteHTML(file, "fanac-headerlink", link)
        file=SubstituteHTML(file, "fanac-fancylink", link)
        file=SubstituteHTML(file, "fanac-stuff", self.ConInstanceStuff)

        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        if self.m_radioBox1.GetSelection() == 0:
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
            i=1
            for row in self._grid._datasource.Rows:
                newtable+="    <tr>\n"
                newtable+='      <td>'+FormatLink(row.Filename, row.DisplayTitle)+'</td>\n'
                if row.Size > 0:
                    newtable+='      <td>'+"{:,}".format(math.floor(row.Size/1024))+' KB</td>\n'
                else:
                    newtable+='      <td>--</td>\n'
                newtable+='      <td>'+str(row.Notes)+'</td>\n'
                newtable+="    </tr>\n"
                i+=1
            newtable+="    </tbody>\n"
            newtable+="  </table>\n"
        else:
            # Construct a list which we'll then substitute.
            newtable="<ul>"
            for row in self._grid._datasource.Rows:
                newtable+="    <li>"+FormatLink(row.LocalPathname, row.DisplayTitle)+"&nbsp;&nbsp;"+str(row.Notes)+"</li>\n"
            newtable+="  </ul>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)

        FTP().PutFileAsString("/"+self._seriesname+"/"+self._coninstancename, "index.html", file, create=True)


        # Finally, FTP any files which are newly added.
        for row in self._grid._datasource.Rows:
            if not FTP().Exists(row.Filename):
                FTP().PutFile(row.LocalPathname, row.Filename)


    #------------------
    # Download a ConSeries
    def LoadConInstancePage(self) -> None:

        # Clear out any old information
        self._grid._datasource=ConInstancePage()

        # Read the existing CIP
        #self.ProgressMessage("Loading "+self._FTPbasedir+"/"+"index.html")
        file=FTP().GetFileAsString(self._FTPbasedir+"/"+self._coninstancename, "index.html")
        if file is None:
            return  # Just return with the ConInstance page empty

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is not None and j != "":
            self.FromJson(j)

        self._grid.RefreshGridFromData()
        self.tConInstanceFancyURL.Value=self.ConInstanceFancyURL


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        self.clickedColumn=event.GetCol()
        self.clickedRow=event.GetRow()

        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Add Files"))
        mi.Enabled=True

        if self._grid._datasource.NumRows > event.GetRow():
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Delete File(s)"))
            mi.Enabled=True

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

        self._grid.RefreshGridFromData()

    # ------------------
    def OnGridCellChanged(self, event):
        self._grid.OnGridCellChanged(event)

    # ------------------
    def OnTextConInstanceName(self, event):
        self.ConInstanceName=self.tConInstanceName.Value

    # ------------------
    def OnTextConInstanceNameKeyUp(self, event):

        self.tConInstanceFancyURL.Value="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConInstanceName.Value)

    # ------------------
    def OnTextConInstanceFancyURL(self, event):

        self.ConInstanceFancyURL=self.tConInstanceFancyURL.Value

    # ------------------
    def OnTextComments(self, event):

        self.ConInstanceStuff=self.tPText.Value
