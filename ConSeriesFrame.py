from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup
from urllib.request import urlopen
import json
from datetime import datetime

from GenConSeriesFrame import GenConSeriesFrame
from FTP import FTP
from ConInstanceDeltaTracker import UpdateLog
from ConSeries import ConSeries, Con
from DataGrid import DataGrid
from ConInstanceFrame import ConInstanceDialogClass
from Settings import Settings

from HelpersPackage import SubstituteHTML, FormatLink, FindWikiBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags, RemoveAccents
from HelpersPackage import FindIndexOfStringInList, PyiResourcePath
from WxHelpers import ModalDialogManager, ProgressMessage
from Log import Log
from FanzineIssueSpecPackage import FanzineDateRange



#####################################################################################
class ConSeriesFrame(GenConSeriesFrame):
    def __init__(self, basedirFTP, conseriesname, conserieslist, show=True):
        GenConSeriesFrame.__init__(self, None)

        self._basedirectoryFTP: str=basedirFTP

        self._fancydownloadfailed: bool=False       # If a download from Fancyclopedia was attempted, did it fail? (This will be used to generate the return code)
        self._signature: int=0
        self._conserieslist=conserieslist

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
        if val is None:
            val=0       # Default is to show empty slots
        self.m_radioBoxShowEmpty.SetSelection(int(val))

        # Download the convention series from the FTP server
        self.DownloadConSeries(conseriesname)

        self._uploaded=False    # Set to true if the con series was uploaded to the website

        self.SetEscapeId(wx.ID_CANCEL)

        self.MarkAsSaved()
        self.RefreshWindow()
        self.Show(show)


    # ----------------------------------------------
    # Used to determine if anything has been updated
    def Signature(self) -> int:
        stuff=self.Seriesname.strip()+self.TextFancyURL.strip()+self.TextComments.strip()+self._basedirectoryFTP.strip()
        return hash(stuff)+self._grid.Signature()

    def MarkAsSaved(self):
        self._signature=self.Signature()

    def NeedsSaving(self):
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
            self.Seriesname=RemoveAccents(d["_textConSeries"])
            self.TextFancyURL=RemoveAccents(d["_textFancyURL"])
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
    # Download a ConSeries from Fanac.org
    def DownloadConSeries(self, seriesname) -> bool:                    # MainConSeriesFrame

        # Clear out any old information
        self._grid.Datasource=ConSeries()

        if seriesname is None or len(seriesname) == 0:
            # Nothing to load. Just return.
            return False

        if self._basedirectoryFTP is None:
            assert False   # Never take this branch.  Delete when I'm sure.

        ProgressMessage(self).Show("Loading "+self.Seriesname+"/index.html from fanac.org")
        file=FTP().GetFileAsString("/"+self.Seriesname, "index.html")

        pathname=self.Seriesname+"/index.html"
        if len(self._basedirectoryFTP) > 0:
            pathname=self._basedirectoryFTP+"/"+pathname

        if file is not None:

            # Get the JSON from the file
            j=FindWikiBracketedText(file, "fanac-json", stripHtml=False)[0]
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

        self._grid.MakeTextLinesEditable()
        self.RefreshWindow()
        ProgressMessage(self).Show(self.Seriesname+" Loaded", close=True, delay=0.5)
        return True


    #-------------------
    def UploadConSeries(self) -> bool:                   # MainConSeriesFrame

        # First read in the template
        try:
            with open(PyiResourcePath("Template-ConSeries.html")) as f:
                file=f.read()
        except:
            wx.MessageBox("Can't read 'Template-ConSeries.html'")
            return False

        # Delete any trailing blank rows.  (Blank rows anywhere are as error, but we only silently drop trailing blank rows.)
        # Find the last non-blank row.
        last=None
        for i, row in enumerate(self._grid.Datasource.Rows):
            if len((row.GoHs+row.Locale+row.Name+row.URL).strip()) > 0 or not row.Dates.IsEmpty:
                last=i
        # Delete the row or rows following it
        if last is not None and last < self._grid.Datasource.NumRows-1:
            del self._grid.Datasource.Rows[last+1:]

        # Determine if we're missing 100% of the data for the Dates, Location, or GoH columns so we can drop them from the listing

        ProgressMessage(self).Show("Uploading /"+self.Seriesname+"/index.html")

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        link=FormatLink("https://fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.Seriesname), self.Seriesname)
        file=SubstituteHTML(file, "title", self.Seriesname)
        file=SubstituteHTML(file, "fanac-instance", link)
        file=SubstituteHTML(file, "fanac-headertext", self.TextComments)

        showempty=self.m_radioBoxShowEmpty.GetSelection() == 0  # Radio button: Show Empty cons?
        hasdates=len([d.Dates for d in self._grid.Datasource.Rows if d.Dates is not None and not d.Dates.IsEmpty()]) > 0
        haslocations=len([d.Locale for d in self._grid.Datasource.Rows if d.Locale is not None and len(d.Locale) > 0]) > 0
        hasgohs=len([d.GoHs for d in self._grid.Datasource.Rows if d.GoHs is not None and len(d.GoHs) > 0]) > 0

        # Now construct the table which we'll then substitute.
        newtable='<table class="table" id="conseriestable">\n'
        newtable+="  <thead>\n"
        newtable+='    <tr id="conseriestable">\n'
        newtable+='      <th scope="col">Convention</th>\n'
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
                newtable+='      <td>'+FormatLink(RemoveAccents(row.URL)+"/index.html", row.Name)+'</td>\n'
            if hasdates:
                newtable+='      <td>'+str(row.Dates) if not None else ""+'</td>\n'
            if haslocations:
                newtable+='      <td>'+row.Locale+'</td>\n'
            if hasgohs:
                newtable+='      <td>'+row.GoHs+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)
        file=SubstituteHTML(file, "fanac-json", self.ToJson())

        file=SubstituteHTML(file, "fanac-date", datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST")

        # Now try to FTP the data up to fanac.org
        if self.Seriesname is None or len(self.Seriesname) == 0:
            Log("UploadConSeries: No series name provided")
            return False
        if not FTP().PutFileAsString("/"+self.Seriesname, "index.html", file, create=True):
            wx.MessageBox("Upload failed")
            return False

        UpdateLog().LogText("Uploaded ConSeries: "+self.Seriesname)

        ProgressMessage(self).Show("Upload succeeded: /"+self.Seriesname+"/index.html", close=True, delay=0.5)
        self.MarkAsSaved()      # It was just saved, so unless it's updated again, the dialog can exit without uploading
        self._uploaded=True     # Something's been uploaded
        self.RefreshWindow()
        return True

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
    def FetchConSeriesFromFancy(self, name, retry: bool=False) -> bool:                    # MainConSeriesFrame
        if name is None or name == "":
            return False

        wait=wx.BusyCursor()    # The busy cursor will show until wait is destroyed
        pageurl="https://fancyclopedia.org/"+WikiPagenameToWikiUrlname(name)
        try:
            response=urlopen(pageurl)
        except:
            del wait  # End the wait cursor
            Log("FetchConSeriesFromFancy: Got exception when trying to open "+pageurl)
            if not retry:
                dlg=wx.TextEntryDialog(None, "Load failed. Enter a different name and press OK to retry.", "Try a different name?", value=name)
                if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
                    return False
                response=dlg.GetValue()
                return self.FetchConSeriesFromFancy(response)
            self._fancydownloadfailed=True
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
        if nloc is None:
            nloc=FindIndexOfStringInList(headers, "Site, Location")
        if nloc is None:
            nloc=FindIndexOfStringInList(headers, "Site, City")
        if nloc is None:
            nloc=FindIndexOfStringInList(headers, "Site")

        ngoh=FindIndexOfStringInList(headers, "GoHs")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "GoH")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "Guests of Honor")
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

        ProgressMessage(self).Show("Loading "+self.Seriesname+" from Fancyclopedia 3")
        self._grid.Datasource=ConSeries()
        self._grid.Datasource.Name=self.Seriesname

        ret=self.FetchConSeriesFromFancy(self.Seriesname)
        if not ret:
            return

        self.RefreshWindow()
        ProgressMessage(self).Show(self.Seriesname+" loaded successfully from Fancyclopedia 3", close=True, delay=0.5)
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
        irow=self._grid.clickedRow
        self._grid.InsertEmptyRows(irow, 1)
        self.EditConInstancePage("", irow)
        self.RefreshWindow()

    #------------------
    def OnPopupEditConPage(self, event):                    # MainConSeriesFrame
        irow=self._grid.clickedRow
        # If the RMB is a click on a convention instance name, we edit that name
        if "Name" in self._grid.Datasource.ColHeaders:
            col=self._grid.Datasource.ColHeaders.index("Name")
            name=self._grid.Datasource.GetData(irow, col)
            self.EditConInstancePage(name, irow)
            self._grid.Grid.SelectBlock(irow, col, irow, col)
            self.RefreshWindow()


    #------------------
    def OnPopupAllowEditCell(self, event):
        # Append a (row, col) tuple. This only lives for the life of this instance.
        self._grid.AllowCellEdit(self._grid.clickedRow, self._grid.clickedColumn)
        self.RefreshWindow()

    # ------------------
    def OnPopupUnlink(self, event):
        self._grid.Datasource.Rows[self._grid.clickedRow].URL=""
        self.RefreshWindow()


    # ------------------
    def OnGridEditorShown(self, event):
        self._grid.OnGridEditorShown(event)


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
            if irow < self._grid.Datasource.NumRows and len(dlg.ConInstanceTopText.strip()) == 0:
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
                    if ("," in gohs and not ", jr" in gohs) or "&" in gohs or " and " in gohs:
                        description+="  The GoHs were "+gohs+"."
                    else:
                        description+="  The GoH was "+gohs+"."
                dlg.ConInstanceTopText=description

            dlg.ConInstanceName=instancename
            dlg.ConInstanceFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(instancename)

            dlg.MarkAsSaved()
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
        irow=self._grid.clickedRow
        if irow >= 0 and irow < self._grid.Datasource.NumRows:
            ret=wx.MessageBox("This will delete "+self._grid.Datasource.Rows[irow].Name+" from the list of conventions on this page, but will not delete "+
                              "its directory or files from fanac.org. You must use FTP to do that.", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
            if ret == wx.OK:
                self._grid.DeleteRows(irow, 1)
                self.RefreshWindow()


    #------------------
    def OnPopupChangeConSeries(self, event):                    # MainConSeriesFrame
        irow=self._grid.clickedRow
        if irow < 0 or irow >= self._grid.Datasource.NumRows:
            Log("OnPopupChangeConSeries: bad irow="+str(irow))
            return

        # Create a popup list dialog to select target con series.  Remove self to prevent user error
        # Do not allow selection of same series
        conserieslist=[x for x in self._conserieslist if x != self.Seriesname]
        newSeriesName=""
        with wx.SingleChoiceDialog(None, "Pick a convention series to move it to", "Move a Convention", conserieslist) as dialog:
            if wx.ID_OK == dialog.ShowModal():
                newSeriesName=dialog.GetStringSelection()

        if newSeriesName == "":
            return

        instanceName=self._grid.Datasource.Rows[irow].Name

        # Ask for confirmation
        ret=wx.MessageBox("Move convention instance '"+instanceName+"' to new convention series '"+newSeriesName+"'?", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
        if ret != wx.OK:
            return

        # Move it
        # Get list of cons in selected con series
        csf=ConSeriesFrame(self._basedirectoryFTP, newSeriesName, conserieslist, show=False)
        newconlist=[x.Name for x in csf._grid.Datasource.Rows]

        # The target con instance directory must not exist.
        newDirPath="/"+newSeriesName+"/"+instanceName
        if len(self._basedirectoryFTP) > 0:
            newDirPath=self._basedirectoryFTP+"/"+newDirPath
        if FTP().PathExists(newDirPath):
            Log("OnPopupChangeConSeries: newDirPath '"+newDirPath+"' already exists", isError=True)
            wx.MessageBox("OnPopupChangeConSeries: newDirPath '"+newDirPath+"' already exists", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
            return

        # Find a location in the new con series list for this one to go to -- assume the list is in alphabetic order
        # Note that this does not check for duplicate con instance names.  That needs to be sorted out by hand.
        loc=len(newconlist)
        if len(newconlist) == 0:
            loc=0
        elif newSeriesName < newconlist[0]:
            loc=0
        else:
            for i in range(1, len(newconlist)):
                if newSeriesName > newconlist[i]:
                    loc=i
                    break

        # Insert an empty row there and then copy the old con series data to the new row.
        # (Note that this is just copying the entry in the con series table, not the data it points to.)
        csf._grid.InsertEmptyRows(loc, 1)
        csf._grid.Datasource.Rows[loc]=self._grid.Datasource.Rows[irow]

        oldDirPath = "/" + self.Seriesname + "/" + instanceName
        UpdateLog().LogText("Moving '"+instanceName+"' from '"+oldDirPath+"' to '"+newDirPath+"'")

        # Copy the con instance directory from the old con series directory to the new con series directory
        # Create the new con instance directory.
        ProgressMessage(self).Show("Creating "+newDirPath+" and copying contents to it.")

        # Make a list of the files in the old con instance directory
        FTP().MKD(newDirPath)

        # Copy the contents of the old con instance directory to the new one
        if len(self._basedirectoryFTP) > 0:
            oldDirPath=self._basedirectoryFTP+"/"+oldDirPath
        fileList=FTP().Nlst(oldDirPath)
        for file in fileList:
            ProgressMessage(self).UpdateMessage("Copying "+file)
            if not FTP().CopyFile(oldDirPath, newDirPath, file):
                msg="OnPopupChangeConSeries: Failure copying "+file+" from "+oldDirPath+" to " +newDirPath+"\nThis will require hand cleanup"
                Log(msg, isError=True)
                wx.MessageBox(msg, 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
                return
        ProgressMessage(self).Close()

        # Save the old and new con series. Don't upload the modified old series if uploading the new one failed
        if csf.UploadConSeries():
            # Remove the old link and upload
            self._grid.DeleteRows(irow)
            self.UploadConSeries()
        else:
            return

            # Delete the old con instance info from site
        i=0


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
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)  # Set enabled state of default items; set all others to False

        icol=self._grid.clickedColumn
        irow=self._grid.clickedRow

        if icol == 0:      # All of the popup options work on the 1st column only
            self.m_popupCreateNewConPage.Enabled=True
            if irow < self._grid.Datasource.NumRows:
                self.m_popupDeleteConPage.Enabled=True
                self.m_popupEditConPage.Enabled=True
                if len(self._grid.Datasource.Rows[irow].URL) > 0:   # Only if there's a link in the cell
                    self.m_popupUnlink.Enabled=True

        if icol < len(self._grid.Datasource.ColEditable) and self._grid.Datasource.ColEditable[icol] == "maybe":
            self.m_popupAllowEditCell.Enabled=True

        if irow < self._grid.Datasource.NumRows and self._grid.Datasource.Rows[irow].URL is not None and self._grid.Datasource.Rows[irow].URL != "":
            self.m_popupChangeConSeries.Enabled=True    # Enable only for rows that exist and point to a con instance

        self.PopupMenu(self.m_menuPopup)

    # ------------------
    def OnGridCellDoubleClick(self, event):                    # MainConSeriesFrame
        self._grid.OnGridCellDoubleClick(event)
        if self._grid.clickedColumn == 0:
            name=self._grid.Get(self._grid.clickedRow, 0)
            self.EditConInstancePage(name, self._grid.clickedRow)
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
        self.RefreshWindow()

    # ------------------
    def OnClose(self, event):                        # MainConSeriesFrame
        self.SetReturnCode(wx.OK)

        if self._fancydownloadfailed:
            self.SetReturnCode(wx.CANCEL)   # We tried a download from Fancy and it failed.
        elif self.NeedsSaving():
            if type(event) == wx._core.CommandEvent:    # When the close event is an ESC or the ID_Cancel button, it's not a vetoable event, so it needs to be handled separately
                resp=wx.MessageBox("The convention series has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    return
            elif event.CanVeto():
                resp=wx.MessageBox("The convention series has been updated and not yet saved. Exit anyway?", 'Warning',
                       wx.OK|wx.CANCEL|wx.ICON_WARNING)
                if resp == wx.CANCEL:
                    event.Veto()
                    return

        # If anything was uploaded to the website, then we return OK indicating something happened
        if self._uploaded:
            self.EndModal(wx.OK)
            return

        # Otherwise, we return Cancel
        self.EndModal(wx.CANCEL)


    def OnSetShowEmptyRadioBox(self, event):
        Settings().Put("ConSeriesFramePage:Show empty", str(self.m_radioBoxShowEmpty.GetSelection()))
