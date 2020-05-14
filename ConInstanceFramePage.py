import wx
import os
import json

from GenConInstanceFrame import GenConInstanceFrame
from Grid import Grid
from ConInstance import ConInstancePage, ConFile

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname

#####################################################################################
class MainConDialogClass(GenConInstanceFrame):
    def __init__(self, rootdir, seriesname, coninstancename):
        GenConInstanceFrame.__init__(self, None)
        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConInstancePage()

        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(self._grid._datasource.ColDataTypes)
#        self._grid.FillInRowNumbers(self._grid.NumrowsR)

        self._grid.RefreshGridFromData()
        self.ConInstanceName=""
        self.ConInstanceStuff=""
        self.ConInstanceFancyURL=""
        self.ReturnValue=None
        self._rootdir=rootdir
        self._seriesname=seriesname
        self._filename=coninstancename


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
        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select files to upload", ".", "", "*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Raise()
            dlg.Destroy()
            return

        for fn in dlg.GetFilenames():
            conf=ConFile()
            conf.DisplayTitle=fn
            conf.LocalPathname=os.path.join(dlg.GetDirectory(), fn)
            self._grid._datasource.Rows.append(conf)
        dlg.Destroy()
        self._grid.RefreshGridFromData()

    def OnSaveConInstance(self, event):
        fname=self.tConInstanceName.Value
        if fname is None or fname == "":
            wx.MessageBox("No convention instance name supplied!")
            return
        base=os.path.splitext(fname)[0]
        fname=base+".htm"   # We use "htm" here temporarily so it's easy to distinguish ConSeres pages from conInstance pages
        self.SaveConInstancePage(fname)   #TODO: Need to make name cannonical
        self.ReturnValue=wx.ID_OK
        self.EndModal(self.ReturnValue)
        self.Close()

    def SaveConInstancePage(self, filename: str) -> None:
        # First read in the template
        file=None
        with open(os.path.join(self._rootdir, "Template-ConPage.html")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.ConInstanceName), self.ConInstanceName)
        file=SubstituteHTML(file, "title", self.ConInstanceName)
        file=SubstituteHTML(file, "fanac-headerlink", link)
        file=SubstituteHTML(file, "fanac-fancylink", link)
        file=SubstituteHTML(file, "fanac-stuff", self.ConInstanceStuff)

        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        if self.m_radioBox1.GetSelection() == 0:
            # Now construct the table which we'll then substitute.
            newtable='<table class="table">\n'
            newtable+="  <thead>\n"
            newtable+="    <tr>\n"
            newtable+='      <th scope="col">#</th>\n'
            newtable+='      <th scope="col">Document</th>\n'
            newtable+='      <th scope="col">Description</th>\n'
            newtable+='    </tr>\n'
            newtable+='  </thead>\n'
            newtable+='  <tbody>\n'
            i=1
            for row in self._grid._datasource.Rows:
                newtable+="    <tr>\n"
                newtable+='      <th scope="row">'+str(1)+'</th>\n'
                newtable+='      <td>'+FormatLink(row.LocalPathname, row.DisplayTitle)+'</td>\n'
                newtable+='      <td>'+str(row.Description)+'</td>\n'
                newtable+="    </tr>\n"
                i+=1
            newtable+="    </tbody>\n"
            newtable+="  </table>\n"
        else:
            # Construct a list which we'll then substitute.
            newtable="<ul>"
            for row in self._grid._datasource.Rows:
                newtable+="    <li>"+FormatLink(row.LocalPathname, row.DisplayTitle)+"&nbsp;&nbsp;"+str(row.Description)+"</li>\n"
            newtable+="  </ul>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)

        with open(filename, "w+") as f:
            f.write(file)


    #------------------
    # Download a ConSeries
    def LoadConInstancePage(self, rootdir: str, seriesname: str, fname: str) -> None:

        # Clear out any old information
        self._grid._datasource=ConInstancePage()

        # Look to see if name is the name of a file
        if fname is not None and fname != "":
            base=os.path.splitext(fname)[0]
            self.filename=base
            self._rootdir=rootdir
            self._seriesname=seriesname
        else:
            # Call the File Open dialog to get a con series HTML file
            if self._rootdir is None or self._rootdir == "":
                return
            dlg=wx.FileDialog(self, "Select con series file to load", self._rootdir, "", "*.htm", wx.FD_OPEN)
            dlg.SetWindowStyle(wx.STAY_ON_TOP)

            if dlg.ShowModal() == wx.ID_CANCEL:
                dlg.Raise()
                dlg.Destroy()
                return

            self.filename=dlg.GetFilename()
            self._rootdir=dlg.GetDirectory()
            dlg.Destroy()

        pathname=os.path.join(self._rootdir, self._seriesname, fname, fname)+".htm"
        if not os.path.exists(pathname):
            return  # Just return with the ConInstance page empty

        # Read the existing CIP
        with open(pathname) as f:
            file=f.read()

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is not None and j != "":
            self.FromJson(j)

        self._grid.RefreshGridFromData()
        self.tConInstanceFancyURL.Value=self.ConInstanceFancyURL


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        self.PopupMenu(self.m_menuPopup)

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

    def OnGridCellChanged(self, event):
        self._grid.OnGridCellChanged(event)

    def OnTextConInstanceName(self, event):
        self.ConInstanceName=self.tConInstanceName.Value

    def OnTextConInstanceNameKeyUp(self, event):
        self.tConInstanceFancyURL.Value="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConInstanceName.Value)

    def OnTextConInstanceFancyURL(self, event):
        self.ConInstanceFancyURL=self.tConInstanceFancyURL.Value

    def OnTextComments(self, event):
        self.ConInstanceStuff=self.tPText.Value
