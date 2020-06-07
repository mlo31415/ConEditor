from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup, NavigableString
from urllib.request import urlopen
import json
from datetime import date

from GenConSeriesFrame import GenConSeriesFrame
from FTP import FTP
from ConSeries import ConSeries, Con
from Grid import Grid
from dlgEnterFancyName import dlgEnterFancyNameWindow
from ConInstanceFramePage import MainConInstanceDialogClass
from Settings import Settings

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import Log
from FanzineIssueSpecPackage import FanzineDateRange



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

        self._allowCellEdits=[]     # A list of cells where editing has specifically been permitted

        self._grid._grid.HideRowLabels()

        self._textConSeriesName: str=""
        self._textFancyURL: str=""
        self._textComments: str=""

        val=Settings().Get("ConSeriesFramePage:Show empty")
        if val is not None:
            self.m_radioBoxShowEmpty.SetSelection(int(val))

        self._updated: bool=False                   # Has the class been changed since it was last uploaded?
        self._fancydownloadfailed: bool=False       # If a download from Fancyclopedia was attempted, did it fail? (This will be used to generate the return code)

        if len(conseriesname) > 0:
            self.DownloadConSeries(conseriesname)

        mi=self.bUploadConSeries.Enabled=len(self._textConSeriesName) > 0     # Enable only if a series name is present

        self.RefreshWindow()

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
        if d["ver"] >= 3:
            self._textConSeriesName=d["_textConSeries"]
            self._textFancyURL=d["_textFancyURL"]
            self._textComments=d["_textComments"]
            self._grid._datasource=ConSeries().FromJson(d["_datasource"])
        return self

    @property
    def Updated(self) -> bool:
        return self._updated or (self._grid._datasource.Updated is not None and self._grid._datasource.Updated)
    @Updated.setter
    def Updated(self, val: bool) -> None:
        self._updated=val
        if val == False:    # If we're setting the updated flag to False, set the grid's flag, too.
            self._grid._datasource.Updated=False

    #------------------
    def ProgressMessage(self, s: str) -> None:                    # MainConSeriesFrame
        self.m_status.Label=s


    #------------------
    # Download a ConSeries from Fanac.org
    def DownloadConSeries(self, seriesname) -> None:                    # MainConSeriesFrame

        # Clear out any old information
        self._grid._datasource=ConSeries()

        if seriesname is None or len(seriesname) == 0:
            # Nothing to load. Just return.
            return

        if self._basedirectoryFTP is None:
            assert(False)   # Never take this branch.  Delete when I'm sure.

        self.ProgressMessage("Loading "+self._seriesname+"/index.html from fanac.org")
        file=FTP().GetFileAsString("/"+self._seriesname, "index.html")

        pathname=self._seriesname+"/index.html"
        if len(self._basedirectoryFTP) > 0:
            pathname=self._basedirectoryFTP+"/"+pathname

        if file is not None:

            # Get the JSON from the file
            j=FindBracketedText(file, "fanac-json")[0]
            if j is None or j == "":
                Log("DownloadConSeries: Can't load convention information from "+pathname)
                wx.MessageBox("Can't load convention information from "+pathname)
                return

            try:
                self.FromJson(j)
            except (json.decoder.JSONDecodeError):
                Log("DownloadConSeries: JSONDecodeError when loading convention information from "+pathname)
                wx.MessageBox("JSONDecodeError when loading convention information from "+pathname)
                return
        else:
            # Leave it empty, but add in the name
            self._textConSeriesName=seriesname

        self.tConSeries.Value=self._textConSeriesName
        self.tComments.Value=self._textComments
        if self._textFancyURL is None or len(self._textFancyURL) == 0:
            self._textFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(seriesname)
        self.tFancyURL.Value=self._textFancyURL

        self.Updated=False
        self.RefreshWindow()
        self.ProgressMessage(self._seriesname+" Loaded")
        Log("DownloadConSeries: "+self._seriesname+" Loaded")


    #-------------------
    def UploadConSeries(self) -> None:                   # MainConSeriesFrame

        # First read in the template
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConSeries.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConSeries.html'")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self._textConSeriesName), self._textConSeriesName)
        file=SubstituteHTML(file, "title", self._textConSeriesName)
        file=SubstituteHTML(file, "fanac-instance", link)
        file=SubstituteHTML(file, "fanac-headertext", self._textComments)
        file=SubstituteHTML(file, "fanac-fancylink", link)

        showempty=self.m_radioBoxShowEmpty.GetSelection() == 0  # Radio button: Show Empty cons?

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

        file=SubstituteHTML(file, "fanac-table", newtable)
        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        # Now try to FTP the data up to fanac.org
        if self._seriesname is None or len(self._seriesname) == 0:
            Log("UploadConSeries: No series name provided")
            return
        if not FTP().PutFileAsString("/"+self._seriesname, "index.html", file, create=True):
            wx.MessageBox("Upload failed")

        self.Updated=False      # It was just saved
        self.RefreshWindow()

    #------------------
    # Save a con series object to disk.
    def OnUploadConSeries(self, event):                    # MainConSeriesFrame
        if self._seriesname is None or len(self._seriesname) == 0:
            wx.MessageBox("You must supply a convention series name to upload")
            return
        wait=wx.BusyCursor()
        self.UploadConSeries()
        del wait    # End the wait cursor


    #--------------------------------------------
    # Given the name of the ConSeries, go to fancy 3 and fetch the con series information and fill in a con seres from it.
    def FetchConSeriesFromFancy(self, name) -> bool:                    # MainConSeriesFrame
        if name is None or name == "":
            return False

        wait=wx.BusyCursor()    # The busy cursor will show until wait is destroyed
        pageurl="http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(name)
        try:
            response=urlopen(pageurl)
        except:
            Log("FetchConSeriesFromFancy: Got exception when trying to open "+pageurl)
            self._fancydownloadfailed=True
            del wait  # End the wait cursor
            return False

        html=response.read()
        soup=BeautifulSoup(html, 'html.parser')
        del wait  # End the wait cursor

        tables=soup.find_all("table", class_="wikitable mw-collapsible")
        if tables == None or len(tables) == 0:
            Log("FetchConSeriesFromFancy: Can't find a table in Fancy 3 page "+pageurl)
            self._fancydownloadfailed=True
            wx.MessageBox("Can't find a table in Fancy 3 page "+pageurl)
            return False

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
            Log("FetchConSeriesFromFancy: Can't interpret Fancy 3 page '"+pageurl+"'")
            self._fancydownloadfailed=True
            wx.MessageBox("Can't interpret Fancy 3 page '"+pageurl+"'")
            return False

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
            if len(row) != len(headers):    # Merged cells which usually signal a skipped convention.  Ignore them.
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
        self.tConSeries.Value=name
        self.Updated=True
        self._fancydownloadfailed=False
        self.RefreshWindow()
        return True


    #------------------
    # Create a new, empty, con series
    def OnCreateConSeries(self, event):                    # MainConSeriesFrame
        if len(self.tConSeries.Value) == 0:
            self._dlgEnterFancyName=dlgEnterFancyNameWindow(None)
            name=self._dlgEnterFancyName._FancyName
            self._seriesname=name
        else:
            name=self.tConSeries.Value
            self._seriesname=name

        self.ProgressMessage("Loading "+name+" from Fancyclopedia 3")
        self._grid._datasource=ConSeries()
        self._grid._datasource.Name=name

        ret=self.FetchConSeriesFromFancy(name)
        if not ret:
            self.ProgressMessage(name+" load from Fancyclopedia 3 failed")
            wx.MessageBox(name+" load from Fancyclopedia 3 failed. Is it possible that its name on Fancy 3 is different?")
            return

        self.RefreshWindow()
        self.ProgressMessage(name+" loaded successfully from Fancyclopedia 3")
        self.Updated=True
        pass

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self.Updated:
            s=s+" *"
        self.Title=s
        self.bUploadConSeries.Enabled=self.Updated

    #------------------
    def OnPopupCreateNewConPage(self, event):                    # MainConSeriesFrame
        irow=self.rightClickedRow
        self.EditConPage("", irow)

    #------------------
    def OnPopupEditConPage(self, event):                    # MainConSeriesFrame
        irow=self.rightClickedRow
        # If the RMB is a click on a convention instance name, we edit that name
        if "Name" in self._grid._datasource.ColHeaders:
            col=self._grid._datasource.ColHeaders.index("Name")
            name=self._grid._datasource.GetData(irow, col)
            self.EditConPage(name, irow)
            self._grid.Grid.SelectBlock(irow, col, irow, col)

    #------------------
    def OnPopupAllowEditCell(self, event):
        irow=self.rightClickedRow
        icol=self.rightClickedColumn
        self._allowCellEdits.append((irow, icol))   # Append a (row, col) tuple. This only lives for the life of this instance.

    # ------------------
    def OnGridEditorShown(self, event):
        irow=event.GetRow()
        icol=event.GetCol()
        if self._grid._datasource._coleditable[icol] == "no":
            event.Veto()
            return
        if self._grid._datasource._coleditable[icol] == "maybe":
            for it in self._allowCellEdits:
                if irow == it[0] and icol == it[1]:
                    return
        event.Veto()
        return


    #------------------
    def EditConPage(self, name: str, irow: int):
        dlg=MainConInstanceDialogClass(self._basedirectoryFTP+"/"+self._seriesname, self._seriesname, name)
        dlg.tConInstanceName.Value=name
        dlg.ShowModal()
        cal=dlg.ReturnValue
        if cal == wx.ID_OK:
            if self._grid._datasource.NumRows <= irow:
                for i in range(irow-self._grid._datasource.NumRows+1):
                    self._grid._datasource.Rows.append(Con())
            self._grid._datasource.Rows[irow].URL=dlg.tConInstanceName.Value
            self.Updated=True
            self.RefreshWindow()

    #------------------
    def OnPopupDeleteConPage(self, event):                    # MainConSeriesFrame
        irow=self.rightClickedRow
        if irow >=0 and irow < self._grid._datasource.NumRows:
            row=self._grid._datasource.Rows[irow]
            del self._grid._datasource.Rows[irow]
            if not FTP().SetDirectory(self._basedirectoryFTP+"/"+ self._seriesname):
                Log("OnPopupDeleteConPage: SetDirectory("+self._basedirectoryFTP+"/"+ self._seriesname+") failed")
                return
            if not FTP().Delete(row.Name):
                Log("OnPopupDeleteConPage: Delete("+row.Name+" failed")
            self.Updated=True
            self.RefreshWindow()


    #------------------
    def OnTextFancyURL(self, event):                    # MainConSeriesFrame
        self._textFancyURL=self.tFancyURL.GetValue()
        self.Updated=True
        self.RefreshWindow()

    #------------------
    def OnTextConSeriesName( self, event ):                    # MainConSeriesFrame
        self._textConSeriesName=self.tConSeries.GetValue()
        self.bUploadConSeries.Enabled=len(self._textConSeriesName) > 0
        self.Updated=True
        self.RefreshWindow()

    #-----------------
    # When the user edits the ConSeries name, we update the Fancy URL (but not vice-versa)
    def ConTextConSeriesKeyUp(self, event):                    # MainConSeriesFrame
        self.tFancyURL.Value="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConSeries.GetValue())
        self.Updated=True
        self.RefreshWindow()

    #------------------
    def OnTextComments(self, event):                    # MainConSeriesFrame
        self._textComments=self.tComments.GetValue()
        self.Updated=True
        self.RefreshWindow()

    #------------------
    def OnGridCellRightClick(self, event):                    # MainConSeriesFrame
        irow=event.GetRow()
        icol=event.GetCol()
        self.rightClickedColumn=icol
        self.rightClickedRow=irow
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)  # Set enabled state of default items; set all others to False
        if icol == 0:      # All of the popup options work on the 1st column only
            if irow >= self._grid._datasource.NumRows:
                self.m_popupCreateNewConPage.Enabled=True
            else:
                self.m_popupDeleteConPage.Enabled=True
                self.m_popupEditConPage.Enabled=True
        if self._grid._datasource._coleditable[icol] == "maybe":
            self.m_popupAllowEditCell.Enabled=True
        self.PopupMenu(self.m_menuPopup)

    # ------------------
    def OnGridCellDoubleClick(self, event):                    # MainConSeriesFrame
        self.rightClickedColumn=event.GetCol()
        self.rightClickedRow=event.GetRow()
        if self.rightClickedColumn == 0:
            name=self._grid.Get(self.rightClickedRow, 0)
            if name is None or len(name) == 0:
                self.OnPopupCreateNewConPage(event)
            else:
                self.EditConPage(name, self.rightClickedRow)

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

    # ------------------
    def OnClose(self, event):            # ConEditorFrame
        self.SetReturnCode(wx.OK)

        if self._fancydownloadfailed:
            self.SetReturnCode(wx.CANCEL)   # We tried a download from Fancy and it failed.
        elif self.Updated:
            if event.CanVeto():
                resp=wx.MessageBox("The convention series has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return

        self.Destroy()


    def OnSetShowEmptyRadioBox(self, event):
        Settings().Put("ConSeriesFramePage:Show empty", str(self.m_radioBoxShowEmpty.GetSelection()))
        self.Updated=True
