from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup, NavigableString
from urllib.request import urlopen
import json

from GenConSeriesFrame import GenConSeriesFrame
from FTP import FTP
from ConSeries import ConSeries, Con
from Grid import Grid
from dlgEnterFancyName import dlgEnterFancyName
from ConInstanceFramePage import MainConInstanceDialogClass

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import Log
from FanzineIssueSpecPackage import FanzineDateRange


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
class MainConSeriesFrame(GenConSeriesFrame):
    def __init__(self, basedirFTP, conseriesname):
        GenConSeriesFrame.__init__(self, None)

        self.userSelection=None
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None
        self._seriesname: str=conseriesname
        self._basedirectoryFTP: str=basedirFTP

        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConSeries()
        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(ConSeries._coldatatypes)

        self._grid._grid.HideRowLabels()

        self._textConSeriesName: str=""
        self._textFancyURL: str=""
        self._textComments: str=""

        if len(conseriesname) > 0:
            self.LoadConSeries(conseriesname)

        self._grid.RefreshGridFromData()

        self.Show(True)


    # Serialize and deserialize
    def ToJson(self) -> str:                    # MainConSeriesFrame
        d={"ver": 3,
           "_textConSeries": self._textConSeriesName,
           "_textFancyURL": self._textFancyURL,
           "_textComments": self._textComments,
           "_filename": self._seriesname,
           "_dirname": self._basedirectoryFTP,
           "_datasource": self._grid._datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> MainConSeriesFrame:                    # MainConSeriesFrame
        d=json.loads(val)
        if d["ver"] <= 3:
            self._textConSeriesName=d["_textConSeries"]
            self._textFancyURL=d["_textFancyURL"]
            self._textComments=d["_textComments"]
            self._grid._datasource=ConSeries().FromJson(d["_datasource"])
        return self

    #------------------
    def ProgressMessage(self, s: str) -> None:                    # MainConSeriesFrame
        self.m_staticTextMessages.Label=s

    #------------------
    def OnLoadConSeries(self, event):                    # MainConSeriesFrame
        self.LoadConSeries(None)
        pass

    #------------------
    # Download a ConSeries
    def LoadConSeries(self, seriesname) -> None:                    # MainConSeriesFrame

        # Clear out any old information
        self._grid._datasource=ConSeries()

        if seriesname is None or len(seriesname) == 0:
            assert(False)   # Never take this branch.  Delete when I'm sure.
        if self._basedirectoryFTP is None:
            assert(False)   # Never take this branch.  Delete when I'm sure.

#        self._seriesname=seriesname

        self.ProgressMessage("Loading "+self._seriesname+"/index.html")
        file=None
        if not FTP().SetDirectory("/"+self._seriesname):
            Log("Bailing out...")
        file=FTP().GetAsString("index.html")

        pathname=self._seriesname+"/index.html"
        if len(self._basedirectoryFTP) > 0:
            pathname=self._basedirectoryFTP+"/"+pathname

        if file is not None:

            # Get the JSON from the file
            j=FindBracketedText(file, "fanac-json")[0]
            if j is None or j == "":
                wx.MessageBox("Can't load convention information from "+pathname)
                return

            try:
                self.FromJson(j)
            except (json.decoder.JSONDecodeError):
                wx.MessageBox("JSONDecodeError when loading convention information from "+pathname)
                return
        else:
            # Leave it empty, but add in the name
            self._textConSeriesName=seriesname

        self.tConSeries.Value=self._textConSeriesName
        self.tComments.Value=self._textComments
        self.tFancyURL.Value=self._textFancyURL

        # Insert the row data into the grid
        self._grid.RefreshGridFromData()
        self.ProgressMessage(self._seriesname+" Loaded")


    #-------------------
    def SaveConSeries(self) -> None:                    # MainConSeriesFrame
        # First read in the template
        file=None
        with open("Template-ConSeries.html") as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self._textConSeriesName), self._textConSeriesName)
        file=SubstituteHTML(file, "title", self._textConSeriesName)
        file=SubstituteHTML(file, "abc", link)
        file=SubstituteHTML(file, "xyz", self._textComments)

        showempty=self.m_radioBoxShowEmpty.GetSelection() == 0  # Radion button: Show Empty cons?

        # Now construct the table which we'll then substitute.
        newtable='<table class="table">\n'
        newtable+="  <thead>\n"
        newtable+="    <tr>\n"
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
            if row.URL is None or row.URL == "":
                newtable+='      <td>'+row.Name+'</td>\n'
            else:
                newtable+='      <td>'+FormatLink(row.URL+"/index.html", row.Name)+'</td>\n'
            newtable+='      <td>'+str(row.Dates)+'</td>\n'
            newtable+='      <td>'+row.Locale+'</td>\n'
            newtable+='      <td>'+row.GoHs+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "pdq", newtable)
        file=SubstituteHTML(file, "fanac-json", self.ToJson())


        # Now try to FTP the data up to fanac.org
        if not FTP().SetDirectory(self._seriesname, create=True):
            Log("Bailing out...")
        FTP().PutString("index.html", file)

    #------------------
    # Save a con series object to disk.
    def OnSaveConSeries(self, event):                    # MainConSeriesFrame
        # Rename the old file
        wait=wx.BusyCursor()
        self.SaveConSeries()
        del wait    # End the wait cursor


    #--------------------------------------------
    # Given the name of the ConSeries, go to fancy 3 and fetch the con series information and fill in a con seres from it.
    def FetchConSeriesFromFancy(self, name):                    # MainConSeriesFrame
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
    def OnCreateConSeries(self, event):                    # MainConSeriesFrame
        self._dlgEnterFancyName=dlgEnterFancyNameWindow(None)
        self.ProgressMessage("Loading "+self._dlgEnterFancyName._FancyName+" from Fancyclopedia 3")
        self._grid._datasource=ConSeries()
        self._grid._datasource.Name=self._dlgEnterFancyName._FancyName
        self._seriesname=self._dlgEnterFancyName._FancyName
        self.FetchConSeriesFromFancy(self._dlgEnterFancyName._FancyName)
        self._grid.RefreshGridFromData()
        self.ProgressMessage(self._dlgEnterFancyName._FancyName+" loaded successfully from Fancyclopedia 3")
        pass

    #------------------
    def OnCreateNewConPage(self, event):                    # MainConSeriesFrame
        row=self.rightClickedRow
        name=""
        if row < self._grid._datasource.NumRows:
            if "Name" in self._grid._datasource.ColHeaders:
                col=self._grid._datasource.ColHeaders.index("Name")
                name=self._grid._datasource.GetData(row, col)
        dlg=MainConInstanceDialogClass(self._basedirectoryFTP+"/"+ self._seriesname, self._seriesname, name)
        dlg.tConInstanceName.Value=name
        dlg.ShowModal()
        cal=dlg.ReturnValue
        if cal == wx.ID_OK:
            if self._grid._datasource.NumRows <= row:
                for i in range(row-self._grid._datasource.NumRows+1):
                    self._grid._datasource.Rows.append(Con())
            self._grid._datasource.Rows[row].URL=dlg.tConInstanceName.Value

        pass

    #------------------
    def OnTextFancyURL(self, event):                    # MainConSeriesFrame
        self._textFancyURL=self.tFancyURL.GetValue()

    #------------------
    def OnTextConSeriesName( self, event ):                    # MainConSeriesFrame
        self._textConSeriesName=self.tConSeries.GetValue()

    #-----------------
    # When the user edits the ConSeries name, we update the Fancy URL (but not vice-versa)
    def ConTextConSeriesKeyUp(self, event):                    # MainConSeriesFrame
        self.tFancyURL.Value="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConSeries.GetValue())

    #------------------
    def OnTextComments(self, event):                    # MainConSeriesFrame
        self._textComments=self.tComments.GetValue()

    #------------------
    def OnGridCellRightClick(self, event):                    # MainConSeriesFrame
        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Create New Con Page"))
        mi.Enabled=True

        self._grid.OnGridCellRightClick(event, self.m_menuPopup)
        self.PopupMenu(self.m_menuPopup)

    # ------------------
    def OnGridCellDoubleClick(self, event):                    # MainConSeriesFrame
        self.rightClickedColumn=event.GetCol()
        self.rightClickedRow=event.GetRow()
        self.OnCreateNewConPage(event)

    #-------------------
    def OnKeyDown(self, event):                    # MainConSeriesFrame
        self._grid.OnKeyDown(event)

    #-------------------
    def OnKeyUp(self, event):                    # MainConSeriesFrame
        self._grid.OnKeyUp(event)

    #------------------
    def OnPopupCopy(self, event):                    # MainConSeriesFrame
        self._grid.OnPopupCopy(event)

    #------------------
    def OnPopupPaste(self, event):                    # MainConSeriesFrame
        self._grid.OnPopupPaste(event)

    def OnGridCellChanged(self, event):                    # MainConSeriesFrame
        self._grid.OnGridCellChanged(event)


