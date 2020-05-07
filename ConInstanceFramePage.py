import wx
import os
from bs4 import BeautifulSoup

from GeneratedConInstanceFrame import MainConFrame
from Grid import Grid
from ConInstance import ConPage, ConFile

from HelpersPackage import SubstituteHTML, StripExternalTags
from FanzineIssueSpecPackage import FanzineDateRange

#####################################################################################
class MainConFrameClass(MainConFrame):
    def __init__(self, parent):
        MainConFrame.__init__(self, parent)
        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConPage()

        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(self._grid._datasource.ColDataTypes)
        self._grid.FillInRowNumbers(self._grid.NumrowsR)

        self._grid.RefreshGridFromData()
        self.ConInstanceName=""
        self.ConInstanceStuff=""
        self.ConInstanceFancyURL=""
        self.Show()


    def OnAddFilesButton(self, event):
        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select files to upload", ".", "", "*.*", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        conf=ConFile()
        conf._displayTitle=dlg.GetFilename()
        conf._localpathname=os.path.join(dlg.GetDirectory(), dlg.GetFilename())
        self._grid._datasource.Rows.append(conf)
        dlg.Destroy()
        self._grid.RefreshGridFromData()

    def OnSaveConInstance(self, event):
        fname=self.tConInstanceName.Value
        if fname is None or fname == "":
            wx.MessageBox("No convention instance named suppled!")
            return
        base=os.path.splitext(fname)[0]
        fname=base+".htm"   # We use "htm" here temporarily so it's easy to distinguish ConSeres pages from conInstance pages
        self.SaveConFilePage(fname)   #TODO: Need to make name cannonical

    def SaveConFilePage(self, filename: str) -> None:
        # First read in the template
        file=None
        with open(os.path.join(".", "Template-ConPage.html")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        file=SubstituteHTML(file, "abc", self.ConInstanceName)
        file=SubstituteHTML(file, "xyz", self.ConInstanceStuff)

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
            newtable+='      <td><a href="'+row._localpathname+'">'+row.DisplayTitle+'</a></td>\n'
            newtable+='      <td>'+str(row.Description)+'</td>\n'
            newtable+="    </tr>\n"
            i+=1
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "pdq", newtable)
        with open(filename, "w+") as f:
            f.write(file)

    #------------------
    # Download a ConSeries
    def ReadConFilePage(self):

        # Clear out any old information
        self._grid._datasource=ConPage()

        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select con series file to load", self.dirname, "", "*.html", wx.FD_OPEN)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        self.filename=dlg.GetFilename()
        self.dirname=dlg.GetDirectory()
        dlg.Destroy()

        with open(os.path.join(self.dirname, self.filename)) as f:
            file=f.read()

        soup=BeautifulSoup(file, 'html.parser')

        # We need to extract three things:
        #   The convention series name
        #   The convention series text
        #   The convention series table
        self.tConInstanceName.Value=soup.find("abc").text
        self.tPText.Value=soup.find("xyz").text
        header=[l.text for l in soup.table.tr.contents if l != "\n"]
        rows=[[m for m in l if m != "\n"] for l in soup.table.tbody if l != "\n"]
        for r in rows:
            r=[StripExternalTags(str(l)) for l in r]
            con=ConPage()
            con.Seq=int(r[0])
            con.Name=r[1]
            con.Dates=FanzineDateRange().Match(r[2])
            con.Locale=r[3]
            con.GoHs=r[4]
            self._grid._datasource.Rows.append(con)

        # Insert the row data into the grid
        self._grid.RefreshGridFromData()

        self.tConInstanceFancyURL.Value=self.ConInstanceFancyURL


    # ------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Create New Con Page"))
        mi.Enabled=True

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

    def OnTextConInstanceFancyURL(self, event):
        self.ConInstanceFancyURL=self.tConInstanceFancyURL.Value

    def OnTextComments(self, event):
        self.ConInstanceStuff=self.tPText.Value
