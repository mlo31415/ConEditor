from __future__ import annotations
from typing import Optional, List, Tuple

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
from DataGrid import DataGrid
from ConInstanceFramePage import ConInstanceDialogClass
from Settings import Settings

from HelpersPackage import ModalDialogManager, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import Log
from FanzineIssueSpecPackage import FanzineDateRange



#####################################################################################
class ConSeriesFrame(GenConSeriesFrame):
    def __init__(self, basedirFTP, conseriesname):
        GenConSeriesFrame.__init__(self, None)

        self.userSelection=None     #TODO: Still needed?
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None

        self._basedirectoryFTP: str=basedirFTP

        self._fancydownloadfailed: bool=False       # If a download from Fancyclopedia was attempted, did it fail? (This will be used to generate the return code)
        self._signature: int=0

        # Set up the grid
        self._grid: DataGrid=DataGrid(self.gRowGrid)
        self._grid.Datasource=ConSeries()

        self._grid.HideRowLabels()

        if len(conseriesname) == 0:
            dlg=wx.TextEntryDialog(None, "Please enter the name of the Convention Series you wish to create.", "Enter Convention Series name")
            if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
                return
            conseriesname=dlg.GetValue()

        self.Seriesname=conseriesname

        val=Settings().Get("ConSeriesFramePage:Show empty")
        if val is not None:
            self.m_radioBoxShowEmpty.SetSelection(int(val))

        # Download the convention series from the FTP server
        self.DownloadConSeries(conseriesname)

        self._uploaded=False    # Set to true if the con series was uploaded to the website

        self.MarkAsSaved()
        self.RefreshWindow()
        self.Show(True)


    # ----------------------------------------------
    # Used to determine if anything has been updated
    def Signature(self) -> int:
        stuff=self.Seriesname.strip()+self.TextFancyURL.strip()+self.TextComments.strip()+self._basedirectoryFTP.strip()
        return hash(stuff)+self._grid.Datasource.Signature()

    def MarkAsSaved(self):
        Log("MainConSeriesFrame.MarkAsSaved -- "+str(self.Signature()))
        self._signature=self.Signature()

    def NeedsSaving(self):
        if self._signature != self.Signature():
            Log("MainConSeriesFrame.NeedsSaving -- "+str(self._signature)+" != "+str(self.Signature()))
        return self._signature != self.Signature()


    # Serialize and deserialize
    def ToJson(self) -> str:                    # MainConSeriesFrame
        d={"ver": 4,
           "_textConSeries": self.Seriesname,
           "_textFancyURL": self.TextFancyURL,
           "_textComments": self.TextComments,
           "_datasource": self._grid.Datasource.ToJson()}
        return json.dumps(d)

    def FromJson(self, val: str) -> ConSeriesFrame:                    # MainConSeriesFrame
        d=json.loads(val)
        if d["ver"] >= 3:
            self.Seriesname=d["_textConSeries"]
            self.TextFancyURL=d["_textFancyURL"]
            self.TextComments=d["_textComments"]
            self._grid.Datasource=ConSeries().FromJson(d["_datasource"])
        return self

    @property
    def Seriesname(self) -> str:
        return self.tConSeries.GetValue()
    @Seriesname.setter
    def Seriesname(self, val: str) -> None:
        self.tConSeries.SetValue(val)

    @property
    def TextComments(self) -> str:
        return self.tComments.GetValue()
    @TextComments.setter
    def TextComments(self, val: str) -> None:
        self.tComments.SetValue(val)

    @property
    def TextFancyURL(self) -> str:
        return self.tFancyURL.GetValue()
    @TextFancyURL.setter
    def TextFancyURL(self, val: str) -> None:
        self.tFancyURL.SetValue(val)

    #------------------
    def ProgressMessage(self, s: str) -> None:                    # MainConSeriesFrame
        self.m_status.Label=s

    #------------------
    # Download a ConSeries from Fanac.org
    def DownloadConSeries(self, seriesname) -> bool:                    # MainConSeriesFrame

        # Clear out any old information
        self._grid.Datasource=ConSeries()

        if seriesname is None or len(seriesname) == 0:
            # Nothing to load. Just return.
            return False

        if self._basedirectoryFTP is None:
            assert(False)   # Never take this branch.  Delete when I'm sure.

        self.ProgressMessage("Loading "+self.Seriesname+"/index.html from fanac.org")
        file=FTP().GetFileAsString("/"+self.Seriesname, "index.html")

        pathname=self.Seriesname+"/index.html"
        if len(self._basedirectoryFTP) > 0:
            pathname=self._basedirectoryFTP+"/"+pathname

        if file is not None:

            # Get the JSON from the file
            j=FindBracketedText(file, "fanac-json")[0]
            if j is None or j == "":
                Log("DownloadConSeries: Can't load convention information from "+pathname)
                wx.MessageBox("Can't load convention information from "+pathname)
                return False

            try:
                self.FromJson(j)
            except (json.decoder.JSONDecodeError):
                Log("DownloadConSeries: JSONDecodeError when loading convention information from "+pathname)
                wx.MessageBox("JSONDecodeError when loading convention information from "+pathname)
                return False
        else:
            # Offer to download the data from Fancy 3
            self.Seriesname=seriesname
            resp=wx.MessageBox("Do you wish to download the convention series "+seriesname+" from Fancyclopedia 3?", 'Shortcut', wx.YES|wx.NO|wx.ICON_QUESTION)
            if resp == wx.YES:
                self.DownloadConSeriesFromFancy(seriesname)

        if self.TextFancyURL is None or len(self.TextFancyURL) == 0:
            self.TextFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(seriesname)

        self.RefreshWindow()
        self.ProgressMessage(self.Seriesname+" Loaded")
        Log("DownloadConSeries: "+self.Seriesname+" Loaded")
        return True


    #-------------------
    def UploadConSeries(self) -> None:                   # MainConSeriesFrame

        # First read in the template
        try:
            with open(os.path.join(os.path.split( sys.argv[0])[0], "Template-ConSeries.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConSeries.html'")

        # Determine if we're missing 100% of the data for the Dates, Location, or GoH columns so we can drop them from the listing


        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        link=FormatLink("http://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.Seriesname), self.Seriesname)
        file=SubstituteHTML(file, "title", self.Seriesname)
        file=SubstituteHTML(file, "fanac-instance", link)
        file=SubstituteHTML(file, "fanac-headertext", self.TextComments)
        file=SubstituteHTML(file, "fanac-fancylink", link)

        showempty=self.m_radioBoxShowEmpty.GetSelection() == 0  # Radio button: Show Empty cons?
        hasdates=len([d.Dates for d in self._grid.Datasource.Rows if not d.Dates.IsEmpty()]) > 0
        haslocations=len([d.Locale for d in self._grid.Datasource.Rows if len(d.Locale) > 0]) > 0
        hasgohs=len([d.GoHs for d in self._grid.Datasource.Rows if len(d.GoHs) > 0]) > 0

        # Now construct the table which we'll then substitute.
        newtable='<table class="table" id="conseriestable">\n'
        newtable+="  <thead>\n"
        newtable+='    <tr id="conseriestable">\n'
        newtable+='      <th scope="col">Conventions</th>\n'
        if hasdates:
            newtable+='      <th scope="col">Dates</th>\n'
        if haslocations:
            newtable+='      <th scope="col">Location</th>\n'
        if hasgohs:
            newtable+='      <th scope="col">GoHs</th>\n'
        newtable+='    </tr>\n'
        newtable+='  </thead>\n'
        newtable+='  <tbody>\n'
        for row in self._grid.Datasource.Rows:
            if (row.URL is None or row.URL == "") and not showempty:    # Skip empty cons?
                continue
            newtable+="    <tr>\n"
            if row.URL is None or row.URL == "":
                newtable+='      <td>'+row.Name+'</td>\n'
            else:
                newtable+='      <td>'+FormatLink(row.URL+"/index.html", row.Name)+'</td>\n'
            if hasdates:
                newtable+='      <td>'+str(row.Dates)+'</td>\n'
            if haslocations:
                newtable+='      <td>'+row.Locale+'</td>\n'
            if hasgohs:
                newtable+='      <td>'+row.GoHs+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)
        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", date.today().strftime("%A %B %d, %Y"))

        # Now try to FTP the data up to fanac.org
        if self.Seriesname is None or len(self.Seriesname) == 0:
            Log("UploadConSeries: No series name provided")
            return
        if not FTP().PutFileAsString("/"+self.Seriesname, "index.html", file, create=True):
            wx.MessageBox("Upload failed")

        self.MarkAsSaved()      # It was just saved, so unless it's updated again, the dialog can exit without uploading
        self._uploaded=True     # Something's been uploaded
        self.RefreshWindow()

    #------------------
    # Save a con series object to disk.
    def OnUploadConSeries(self, event):                    # MainConSeriesFrame
        if self.Seriesname is None or len(self.Seriesname) == 0:
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
            msg="Can't find a table in Fancy 3 page "+pageurl+".  Is it possible that its name on Fancy 3 is different?"
            Log(msg)
            self._fancydownloadfailed=True
            wx.MessageBox(msg)
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

            self._grid.Datasource.Rows.append(con)
        self.Seriesname=name
        self._fancydownloadfailed=False
        self.RefreshWindow()
        return True


    #------------------
    # Create a new, empty, con series
    def OnLoadSeriesFromFancy(self, event):                    # MainConSeriesFrame
        self.DownloadConSeriesFromFancy(self.tConSeries.GetValue())

    def DownloadConSeriesFromFancy(self, seriesname: str):
        self.Seriesname=seriesname

        self.ProgressMessage("Loading "+self.Seriesname+" from Fancyclopedia 3")
        self._grid.Datasource=ConSeries()
        self._grid.Datasource.Name=self.Seriesname

        ret=self.FetchConSeriesFromFancy(self.Seriesname)
        if not ret:
            return

        self.RefreshWindow()
        self.ProgressMessage(self.Seriesname+" loaded successfully from Fancyclopedia 3")
        pass

    #------------------
    def RefreshWindow(self) -> None:
        self._grid.RefreshGridFromData()
        s=self.Title
        if s.endswith(" *"):
            s=s[:-2]
        if self.NeedsSaving():
            s=s+" *"
        self.Title=s
        self.bUploadConSeries.Enabled=len(self.Seriesname) > 0
        self.bLoadSeriesFromFancy .Enabled=self._grid.Datasource.NumRows == 0  # If any con instances have been created, don't offer a download from Fancy


    #------------------
    def OnPopupCreateNewConPage(self, event):                    # MainConSeriesFrame
        irow=self.rightClickedRow
        self.EditConInstancePage("", irow)
        self.RefreshWindow()

    #------------------
    def OnPopupEditConPage(self, event):                    # MainConSeriesFrame
        irow=self.rightClickedRow
        # If the RMB is a click on a convention instance name, we edit that name
        if "Name" in self._grid.Datasource.ColHeaders:
            col=self._grid.Datasource.ColHeaders.index("Name")
            name=self._grid.Datasource.GetData(irow, col)
            self.EditConInstancePage(name, irow)
            self._grid.Grid.SelectBlock(irow, col, irow, col)
            self.RefreshWindow()


    #------------------
    def OnPopupAllowEditCell(self, event):
        irow=self.rightClickedRow
        icol=self.rightClickedColumn
        self._grid.Datasource.AllowCellEdits.append((irow, icol))   # Append a (row, col) tuple. This only lives for the life of this instance.


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


    #------------------
    def EditConInstancePage(self, instancename: str, irow: int) -> None:
        if len(instancename) == 0:
            dlg=wx.TextEntryDialog(None, "Please enter the name of the Convention Instance you wish to create.", "Enter Convention Instance name")
            if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0: # Do nothing if the user returns an empty string as name
                return
            instancename=dlg.GetValue()

        if irow >= self._grid.NumRows:
            self._grid.ExpandDataSourceToInclude(irow, 0)   # Add rows if needed


        with ModalDialogManager(ConInstanceDialogClass, self._basedirectoryFTP+"/"+self.Seriesname, self.Seriesname, instancename) as dlg:
            dlg.ConInstanceName=instancename

            # Construct a description of the convention from the information in the con series entry, if any.
            if irow < self._grid.Datasource.NumRows:
                row=self._grid.Datasource.Rows[irow]
                dates=None
                if row.Dates is not None and not row.Dates.IsEmpty():
                    dates=str(row.Dates)
                locale=None
                if row.Locale is not None and len(row.Locale) > 0:
                    locale=row.Locale
                description=instancename
                if dates is not None and locale is not None:
                    description+=" was held "+dates+" in "+locale+"."
                elif dates is not None:
                    description+=" was held "+dates+"."
                elif locale is not None:
                    description+=" was held in " +locale+"."
                if row.GoHs is not None and len(row.GoHs) > 0:
                    gohs=row.GoHs.replace("&amp;", "&")
                    if "," in gohs or "&" in gohs:
                        description+="  The GoHs were "+gohs
                    else:
                        description+="  The GoH was "+gohs
                dlg.ConInstanceStuff=description

            dlg.ConInstanceName=instancename
            dlg.ConInstanceFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(instancename)

            dlg.RefreshWindow()
            if dlg.ShowModal() == wx.ID_OK:
                if self._grid.Datasource.NumRows <= irow:
                    for i in range(irow-self._grid.Datasource.NumRows+1):
                        self._grid.Datasource.Rows.append(Con())
                self._grid.Datasource.Rows[irow].Name=dlg.ConInstanceName
                self._grid.Datasource.Rows[irow].URL=dlg.ConInstanceName
                self.RefreshWindow()

    #------------------
    def OnPopupDeleteConPage(self, event):                    # MainConSeriesFrame
        irow=self.rightClickedRow
        if irow >= 0 and irow < self._grid.Datasource.NumRows:
            row=self._grid.Datasource.Rows[irow]
            ret=wx.MessageBox("This will delete "+self._grid.Datasource.Rows[irow].Name+" from the list of conventions on this page, but will not delete "+
                              "its directory or files from fanac.org. You must use FTP to do that.", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
            if ret == wx.OK:
                del self._grid.Datasource.Rows[irow]
            self.RefreshWindow()

    #------------------
    def OnTextFancyURL(self, event):                    # MainConSeriesFrame
        self.RefreshWindow()

    #------------------
    def OnTextConSeriesName( self, event ):                    # MainConSeriesFrame
        self.RefreshWindow()

    #-----------------
    # When the user edits the ConSeries name, we update the Fancy URL (but not vice-versa)
    def ConTextConSeriesKeyUp(self, event):                    # MainConSeriesFrame
        self.TextFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConSeries.GetValue())

    #------------------
    def OnTextComments(self, event):                    # MainConSeriesFrame
        self.RefreshWindow()

    #------------------
    def OnGridCellRightClick(self, event):                    # MainConSeriesFrame
        irow=event.GetRow()
        icol=event.GetCol()
        self.rightClickedColumn=icol
        self.rightClickedRow=irow
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)  # Set enabled state of default items; set all others to False
        if icol == 0:      # All of the popup options work on the 1st column only
            if irow >= self._grid.Datasource.NumRows:
                self.m_popupCreateNewConPage.Enabled=True
            else:
                self.m_popupDeleteConPage.Enabled=True
                self.m_popupEditConPage.Enabled=True
        if self._grid.Datasource.ColEditable[icol] == "maybe":
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
                self.EditConInstancePage(name, self.rightClickedRow)
            self.RefreshWindow()

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

    def OnGridCellChanged(self, event):               # MainConSeriesFrame
        self._grid.OnGridCellChanged(event)

    # ------------------
    def OnClose(self, event):                        # MainConSeriesFrame
        self.SetReturnCode(wx.OK)

        if self._fancydownloadfailed:
            self.SetReturnCode(wx.CANCEL)   # We tried a download from Fancy and it failed.
        elif self.NeedsSaving():
            if event.CanVeto():
                resp=wx.MessageBox("The convention series has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return

        # If anything was upladed to the website, then we return OK indicating something happened
        if self._uploaded:
            self.EndModal(wx.OK)
            return

        # Otherwise, we return Cancel
        self.EndModal(wx.CANCEL)


    def OnSetShowEmptyRadioBox(self, event):
        Settings().Put("ConSeriesFramePage:Show empty", str(self.m_radioBoxShowEmpty.GetSelection()))