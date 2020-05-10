from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup, NavigableString
from urllib.request import urlopen
import json

from GeneratedConSeriesFrame import MainConSeriesFrame

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import LogOpen
from FanzineIssueSpecPackage import FanzineDateRange

from ConSeries import ConSeries, Con
from Grid import Grid

from dlgEnterFancyName import dlgEnterFancyName
from ConInstanceFramePage import MainConDialogClass


#####################################################################################
class dlgEnterFancyNameWindow(dlgEnterFancyName):
    def __init__(self, parent):
        dlgEnterFancyName.__init__(self, parent)
        self._FancyName: str=""
        self.ShowModal()

    def OnBuCreateConSeries(self, event):
        self.Hide()

    def OnTextChanged(self, event):
        self._FancyName=self.m_textCtrl4.Value



#####################################################################################
class MainWindow(MainConSeriesFrame):
    def __init__(self, parent, title):
        MainConSeriesFrame.__init__(self, parent)

        self.userSelection=None
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None
        self._filename: str=""
        self._dirname: str=""

        if len(sys.argv) > 1:
            self._dirname=os.getcwd()

        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConSeries()
        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(ConSeries._coldatatypes)
        self._grid.RefreshGridFromData()

        self._textConSeries: str=""
        self._textFancyURL: str=""
        self._textComments: str=""

        self.Show(True)


    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 3,
           "_textConSeries": self._textConSeries,
           "_textFancyURL": self._textFancyURL,
           "_textComments": self._textComments,
           "_filename": self._filename,
           "_dirname": self._dirname,
           "_datasource": self._grid._datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> MainConSeriesFrame:
        d=json.loads(val)
        if d["ver"] <= 3:
            self._textConSeries=d["_textConSeries"]
            self._textFancyURL=d["_textFancyURL"]
            self._textComments=d["_textComments"]
            self._grid._datasource=ConSeries().FromJson(d["_datasource"])
        if d["ver"] == 2:
            self._filename=d["filename"]
            self._dirname=d["dirname"]
        if d["ver"] == 3:
            self._filename=d["_filename"]
            self._dirname=d["_dirname"]
        return self

    #------------------
    def ProgressMessage(self, s: str) -> None:
        self.m_staticTextMessages.Label=s

    #------------------
    def OnLoadConSeries(self, event):
        self.LoadConSeries()
        pass

    #------------------
    # Download a ConSeries
    def LoadConSeries(self) -> None:

        # Clear out any old information
        self._grid._datasource=ConSeries()

        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select con series file to load", self._dirname, "", "*.html", style=wx.FD_OPEN|wx.STAY_ON_TOP)

        val=dlg.ShowModal()
        if val == wx.ID_CANCEL:
            return

        self._filename=dlg.GetFilename()
        self._dirname=dlg.GetDirectory()
        dlg.Destroy()

        self.ProgressMessage("Loading "+self._filename)
        with open(os.path.join(self._dirname, self._filename)) as f:
            file=f.read()

        # Get the JSON
        j=FindBracketedText(file, "fanac-json")[0]
        if j is None or j != "":
            wx.MessageBox("Can't load convention information from "+os.path.join(self._dirname, self._filename))
            return

        try:
            self.FromJson(j)
        except (json.decoder.JSONDecodeError):
            wx.MessageBox("JSONDecodeError when loading convention information from "+os.path.join(self._dirname, self._filename))
            return

        frame.tConSeries.Value=self._textConSeries
        frame.tComments.Value=self._textComments
        frame.tFancyURL.Value=self._textFancyURL

        # Insert the row data into the grid
        self._grid.RefreshGridFromData()
        self.ProgressMessage(self._filename+" Loaded")


    def SaveConSeries(self, filename: str) -> None:
        # First read in the template
        file=None
        with open(os.path.join(self._dirname, "Template-ConSeries")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self._textConSeries), self._textConSeries)
        file=SubstituteHTML(file, "abc", link)
        file=SubstituteHTML(file, "xyz", self._textComments)

        showempty=self.m_radioBoxShowEmpty.GetSelection() == 0  # Radion button: Show Empty cons?

        # Now construct the table which we'll then substitute.
        newtable='<table class="table">\n'
        newtable+="  <thead>\n"
        newtable+="    <tr>\n"
        newtable+='      <th scope="col">#</th>\n'
        newtable+='      <th scope="col">Conventions</th>\n'
        newtable+='      <th scope="col">Dates</th>\n'
        newtable+='      <th scope="col">Location</th>\n'
        newtable+='      <th scope="col">GoHs</th>\n'
        newtable+='    </tr>\n'
        newtable+='  </thead>\n'
        newtable+='  <tbody>\n'
        for row in self._grid._datasource.Rows:
            if (row.URL is None or row.URL == "") and not showempty:    # Skip empty cons?
                continue
            newtable+="    <tr>\n"
            newtable+='      <th scope="row">'+str(row.Seq)+'</th>\n'
            if row.URL is None or row.URL == "":
                newtable+='      <td>'+row.Name+'</td>\n'
            else:
                newtable+='      <td>'+FormatLink(row.URL+".htm", row.Name)+'</td>\n'
            newtable+='      <td>'+str(row.Dates)+'</td>\n'
            newtable+='      <td>'+row.Locale+'</td>\n'
            newtable+='      <td>'+row.GoHs+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "pdq", newtable)
        file=SubstituteHTML(file, "fanac-json", self.ToJson())
        with open(filename, "w+") as f:
            f.write(file)

    #------------------
    # Save a con series object to disk.
    def OnSaveConSeries(self, event):
        # Rename the old file
        wait=wx.BusyCursor()
        oldname=os.path.join(self._dirname, os.path.splitext(self._filename)[0]+".html")        # Make sure we have the proper extension
        newname=os.path.join(self._dirname, os.path.splitext(self._filename)[0]+"-old.html")
        if os.path.exists(oldname):
            try:
                i=0
                while os.path.exists(newname):
                    i+=1
                    newname=os.path.join(self._dirname, os.path.splitext(self._filename)[0]+"-old-"+str(i)+".html")

                os.rename(oldname, newname)
            except:
                Bailout(PermissionError, "OnSaveConseries fails when trying to rename "+oldname+" to "+newname, "ConEditorError")

        try:
            self.SaveConSeries(oldname)
        except:
            Bailout(PermissionError, "OnSaveConseries fails when trying to write file "+oldname, "ConEditorError")
        del wait    # End the wait cursor


    #--------------------------------------------
    # Given the name of the ConSeries, go to fancy 3 and fetch the con series information and fill in a con seres from it.
    def FetchConSeriesFromFancy(self, name):
        if name is None or name == "":
            return

        wait=wx.BusyCursor()
        pageurl="http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(name)
        try:
            response=urlopen(pageurl)
        except:
            del wait  # End the wait cursor
            wx.MessageBox("Fatch from Fancy 3 failed.")
            return

        html=response.read()
        soup=BeautifulSoup(html, 'html.parser')
        del wait  # End the wait cursor

        tables=soup.find_all("table", class_="wikitable mw-collapsible")
        if tables == None or len(tables) == 0:
            wx.MessageBox("Can't find a table in Fancy 3 page "+pageurl)
            return

        bsrows=tables[0].find_all("tr")
        headers=[]
        rows=[]
        for bsrow in bsrows:
            if len(headers) == 0:       #Save the header row separately
                heads=bsrow.find_all("th")
                if len(heads) > 0:
                    for head in heads:
                        headers.append(head.contents[0])
                    headers=[RemoveAllHTMLTags(UnformatLinks(str(h))).strip() for h in headers]
                    continue

            # Ordinary row
            cols=bsrow.find_all("td")
            row=[]
            print("")
            if len(cols) > 0:
                for col in cols:
                    row.append(RemoveAllHTMLTags(UnformatLinks(str(col))).strip())
            if len(row) > 0:
                rows.append(row)

        # Did we find anything?
        if len(headers) == 0 or len(rows) == 0:
            wx.MessageBox("Can't interpret Fancy 3 page '"+pageurl+"'")
            return

        # OK. We have the data.  Now fill in the ConSeries object
        # First, figure out which columns are which
        nname=FindIndexOfStringInList(headers, "Convention")
        if nname is None:
            nname=FindIndexOfStringInList(headers, "Name")
        ndate=FindIndexOfStringInList(headers, "Dates")
        if ndate is None:
            ndate=FindIndexOfStringInList(headers, "Date")
        nloc=FindIndexOfStringInList(headers, "Location")
        ngoh=FindIndexOfStringInList(headers, "GoHs")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "GoH")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "Guests")

        for row in rows:
            if len(row) != len(headers):    # Merged cells which usually signal a skipped convention.
                continue
            con=Con()
            if nname is not None:
                con.Name=row[nname]
            if ndate is not None:
                con.Dates=FanzineDateRange().Match(row[ndate])
            if nloc is not None:
                con.Locale=row[nloc]
            if ngoh is not None:
                con.GoHs=row[ngoh]

            self._grid._datasource.Rows.append(con)


    #------------------
    # Create a new, empty, con series
    def OnCreateConSeries(self, event):
        self._dlgEnterFancyName=dlgEnterFancyNameWindow(None)
        self.ProgressMessage("Loading "+self._dlgEnterFancyName._FancyName+" from Fancyclopedia 3")
        self._grid._datasource=ConSeries()
        self._grid._datasource.Name=self._dlgEnterFancyName._FancyName
        self._filename=self._dlgEnterFancyName._FancyName
        self.FetchConSeriesFromFancy(self._dlgEnterFancyName._FancyName)
        self._grid.RefreshGridFromData()
        self.ProgressMessage(self._dlgEnterFancyName._FancyName+" loaded successfully from Fancyclopedia 3")
        pass

    #------------------
    def OnCreateNewConPage(self, event):
        dlg=MainConDialogClass(None)
        row=self.rightClickedRow-1  # Get logical row & col
        name=""
        if row < self._grid._datasource.NumRows:
            if "Name" in self._grid._datasource.ColHeaders:
                col=self._grid._datasource.ColHeaders.index("Name")
                name=self._grid._datasource.GetData(row, col)
        dlg.tConInstanceName.Value=name
        dlg.LoadConInstancePage(name)
        dlg.ShowModal()
        cal=dlg.ReturnValue
        if cal == True:
            self._grid._datasource.Rows[row].URL=dlg.tConInstanceName.Value

        pass

    #------------------
    def OnTextFancyURL(self, event):
        self._textFancyURL=self.tFancyURL.GetValue()

    #------------------
    def OnTextConSeries( self, event ):
        self._textConSeries=self.tConSeries.GetValue()

    #------------------
    def OnTextComments(self, event):
        self._textComments=self.tComments.GetValue()

    #------------------
    def OnGridCellRightClick(self, event):
        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Create New Con Page"))
        mi.Enabled=True

        self._grid.OnGridCellRightClick(event, self.m_menuPopup)
        self.PopupMenu(self.m_menuPopup)


    # ------------------
    def OnGridCellDoubleClick(self, event):
        self.rightClickedColumn=event.GetCol()
        self.rightClickedRow=event.GetRow()
        self.OnCreateNewConPage(event)


    #-------------------
    def OnKeyDown(self, event):
        self._grid.OnKeyDown(event)

    #-------------------
    def OnKeyUp(self, event):
        self._grid.OnKeyUp(event)

    #------------------
    def OnPopupCopy(self, event):
        self._grid.OnPopupCopy(event)

    #------------------
    def OnPopupPaste(self, event):
        self._grid.OnPopupPaste(event)

    def OnGridCellChanged(self, event):
        self._grid.OnGridCellChanged(event)


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")
app = wx.App(False)
frame = MainWindow(None, "Convention series editor")
app.MainLoop()

