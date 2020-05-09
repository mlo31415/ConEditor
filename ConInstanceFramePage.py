import wx
import os
from bs4 import BeautifulSoup
import json

from GeneratedConInstanceFrame import MainConFrame
from Grid import Grid
from ConInstance import ConInstancePage, ConFile

from HelpersPackage import SubstituteHTML, StripExternalTags, FormatLink, FindBracketedText
from FanzineIssueSpecPackage import FanzineDateRange

#####################################################################################
class MainConFrameClass(MainConFrame):
    def __init__(self, parent):
        MainConFrame.__init__(self, parent)
        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConInstancePage()

        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(self._grid._datasource.ColDataTypes)
        self._grid.FillInRowNumbers(self._grid.NumrowsR)

        self._grid.RefreshGridFromData()
        self.ConInstanceName=""
        self.ConInstanceStuff=""
        self.ConInstanceFancyURL=""

        self.Show()

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 1,
           "ConInstanceName": self.ConInstanceName,
           "ConInstanceStuff": self.ConInstanceStuff,
           "ConInstanceFancyURL": self.ConInstanceFancyURL,
           "_datasource": self._grid._datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> MainConFrame:
        d=json.loads(val)
        if d["ver"] == 1:
            self.ConInstanceName=d["ConInstanceName"]
            self.ConInstanceStuff=d["ConInstanceStuff"]
            self.ConInstanceFancyURL=d["ConInstanceFancyURL"]
            self._grid._datasource=ConInstancePage().FromJson(d["_datasource"])
        return self


    def OnAddFilesButton(self, event):
        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select files to upload", ".", "", "*.*", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        conf=ConFile()
        conf.DisplayTitle=dlg.GetFilename()
        conf.LocalPathname=os.path.join(dlg.GetDirectory(), dlg.GetFilename())
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

    def SaveConInstancePage(self, filename: str) -> None:
        # First read in the template
        file=None
        with open(os.path.join(".", "Template-ConPage.html")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        link=FormatLink("http://fancyclopedia.org/"+self.ConInstanceName, self.ConInstanceName)
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

    def ConvertFromJSON(self):
        pass

    #------------------
    # Download a ConSeries
    def LoadConInstancePage(self, fname:str):

        # Clear out any old information
        self._grid._datasource=ConInstancePage()

        # Look to see if name is the name of a file
        if fname is not None and fname != "":
            base=os.path.splitext(fname)[0]
            self.filename=base+".htm"
            self.dirname="."
        else:
            # Call the File Open dialog to get a con series HTML file
            dlg=wx.FileDialog(self, "Select con series file to load", self.dirname, "", "*.htm", wx.FD_OPEN)
            dlg.SetWindowStyle(wx.STAY_ON_TOP)

            if dlg.ShowModal() != wx.ID_OK:
                dlg.Raise()
                dlg.Destroy()
                return

            self.filename=dlg.GetFilename()
            self.dirname=dlg.GetDirectory()
            dlg.Destroy()

        pathname=os.path.join(self.dirname, self.filename)
        if not os.path.exists(pathname):
            return  # Just return with the ConInstance page empty

        # Read the existing CIP
        with open(pathname) as f:
            file=f.read()

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is not None and j != "":
            self.FromJson(j)

        else:
            # Try parsing the HTML
            soup=BeautifulSoup(file, 'html.parser')

            # We need to extract three things:
            #   The convention series name
            #   The convention series text
            #   The convention series table
            self.tConInstanceName.Value=soup.find("fanac-headerlink").text
            self.tPText.Value=soup.find("fanac-stuff").text
            header=[l.text for l in soup.table.tr.contents if l != "\n"]
            rows=[[m for m in l if m != "\n"] for l in soup.table.tbody if l != "\n"]
            for r in rows:
                r=[StripExternalTags(str(l)) for l in r]
                con=ConFile()
                con.Seq=int(r[0])
                con.DisplayTitle=r[1]
                con.Description=r[2]
                self._grid._datasource.Rows.append(con)

        # Insert the row data into the grid
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

    def OnTextConInstanceFancyURL(self, event):
        self.ConInstanceFancyURL=self.tConInstanceFancyURL.Value

    def OnTextComments(self, event):
        self.ConInstanceStuff=self.tPText.Value
