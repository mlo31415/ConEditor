from __future__ import annotations

import re
import wx, wx.grid
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import unquote
from datetime import datetime

from GenConSeriesFrame import GenConSeriesFrame
from FTP import FTP
from ConInstanceDeltaTracker import UpdateFTPLog
from ConSeries import ConSeries, Con
from ConInstance import ConInstance
from WxDataGrid import DataGrid, IsEditable
from ConInstanceFrame import ConInstanceDialogClass
from Settings import Settings

from HelpersPackage import SubstituteHTML, FormatLink, FindBracketedText2, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags, RemoveAccents
from HelpersPackage import FindIndexOfStringInList, PyiResourcePath, MessageBox
from WxHelpers import ModalDialogManager, ProgressMessage2, OnCloseHandling, MessageBoxInput, wxMessageDialogInput, wxMessageBox
from Log import Log, LogError
from FanzineDateTime import FanzineDateRange



#####################################################################################
class ConSeriesFrame(GenConSeriesFrame):
    def __init__(self, basedirFTP: str, conseriesname: str, conserieslist: list[str], show: bool=True):
        GenConSeriesFrame.__init__(self, None)

        self._basedirectoryFTP: str=basedirFTP
        Log(f"ConSeriesFrame: {self._basedirectoryFTP=}", Flush=True)

        self._fancydownloadfailed: bool=False       # If a download from Fancyclopedia was attempted, did it fail? (This will be used to generate the return code)
        self._signature: int=0

        self._isNewSeriesPage=False     # Must be overridden after class is instantiated if needed

        # Set up the grid
        self._grid: DataGrid=DataGrid(self.gRowGrid)    # Old, New
        self.Datasource=ConSeries()

        self._grid.HideRowLabels()

        if len(conseriesname) == 0:
            dlg=wx.TextEntryDialog(None, "Please enter the name of the Convention Series you wish to create.", "Enter Convention Series name")
            if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
                return
            conseriesname=dlg.GetValue()

        self.Seriesname=conseriesname
        self._conserieslist=conserieslist

        val=Settings().Get("ConSeriesFramePage:Show empty", default=0)      # Default is to show empty slots
        self.m_radioBoxShowEmpty.SetSelection(val)

        # Download the convention series from the FTP server
        self.DownloadConSeries(conseriesname)
        Log(f"ConSeriesFrame.__init__: self.DownloadConSeries() has run", Flush=True)
        self._uploaded=False    # Set to true if the con series was uploaded to the website

        self.SetEscapeId(wx.ID_CANCEL)

        self.MarkAsSaved()
        self.RefreshWindow()
        FTP().LoggingOff()
        self.Show(show)


    @property
    def Datasource(self) -> ConSeries:
        return self._Datasource
    @Datasource.setter
    def Datasource(self, val: ConSeries):
        self._Datasource=val
        self._grid.Datasource=val

    # ----------------------------------------------
    # Used to determine if anything has been updated
    def __hash__(self) -> int:
        stuff=self.Seriesname.strip()+self.TextFancyURL.strip()+self.TextComments.strip()+self._basedirectoryFTP.strip()
        return hash(stuff)+self.Datasource.Signature()+hash(self.m_radioBoxShowEmpty)
    def Signature(self) -> int:
        return self.__hash__()

    def MarkAsSaved(self):     
        self._signature=self.Signature()

    def NeedsSaving(self) -> bool:     
        return self._signature != self.Signature()

    def UpdateNeedsSavingFlag(self):
        s=self.Title.removesuffix(" *") # Remove any existing Needs Saving marker
        if self.NeedsSaving():
            s=s+" *"
        self.Title=s


    @property
    def Seriesname(self) -> str:     
        return self.tConSeries.GetValue().strip()
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
    def DownloadConSeries(self, seriesname) -> bool:      

        # Clear out any old information
        self.Datasource=ConSeries()

        if seriesname is None or len(seriesname) == 0:
            # Nothing to load. Just return.
            return False

        if self._basedirectoryFTP is None:
            assert False   # Never take this branch.  Delete when I'm sure.

        with ModalDialogManager(ProgressMessage2, f"Loading {self.Seriesname}/index.html from fanac.org", parent=self) as pm:
            file=FTP().GetFileAsString("/"+self.Seriesname, "index.html")

            if file is not None:
                if not self.LoadConSeriesFromHTML(file):
                    pm.Update(f"{self.Seriesname} Load Failed", delay=0.5)
                    return False
            else:
                # Offer to download the data from Fancy 3
                self.Seriesname=seriesname
                resp=wx.MessageBox(f"Do you wish to download the convention series {seriesname} from Fancyclopedia 3?", 'Shortcut', wx.YES|wx.NO|wx.ICON_QUESTION)
                if resp == wx.YES:      # If no, we just present an empty form.
                    self.DownloadConSeriesFromFancy(seriesname)

            if self.TextFancyURL is None or len(self.TextFancyURL) == 0:
                self.TextFancyURL=f"fancyclopedia.org/{WikiPagenameToWikiUrlname(seriesname)}"

            self._grid.MakeTextLinesEditable()
            self.RefreshWindow()
            pm.Update(f"{self.Seriesname} Loaded")
            return True


    #----------------------------------------------------------------------
    # Read a row from an HTML table and output a list of cell contents
    # The input is normally the text bounded by <tr>...</tr>
    # The cells are all the strings delimited by <delim>...</delim>
    @staticmethod
    def ReadTableRow(row: str, delim="td") -> list[str]:
        rest=row
        out=[]
        while True:
            item, rest=FindBracketedText2(rest, delim, caseInsensitive=True)
            if item == "":
                break
            if f"<{delim}>" in item:    # This corrects for an error in which we have the pattern '<td>xxx<td>yyy</td>' which displays perfectly well
                item=item.split(f"<{delim}>")
                out.extend(item)
            else:
                out.append(item)

        return out


    #----------------------------
    # Populate the ConSeriesFrame structure
    def LoadConSeriesFromHTML(self, file: str) -> bool:
        # Look for the series name in the header
        head, rest=FindBracketedText2(file, "head", caseInsensitive=True)
        series, _=FindBracketedText2(head, "title", caseInsensitive=True)
        if series == "":
            Log("LoadConSeriesFromHTML() could not find <title>...</title> in <head>...</head>")
            return False
        self.Seriesname=series

        # Locate the Fancy 3 reference
        ref, _=FindBracketedText2(rest, "fanac-instance", caseInsensitive=True)
        if ref == "":
            Log(f"DecodeConSeriesHTML(): failed to find the <fanac-instance> tags in the body")
            return False
        m=re.match('<a href="(https://fancyclopedia.org/.*?)">.*?</a>$', ref, re.IGNORECASE)
        if m is None:
            Log(f"DecodeConSeriesHTML(): failed to find the fancyclopedia link in the <fanac-instance> tag in the main table")
            return False
        self.TextFancyURL=RemoveAccents(m.groups()[0])

        self.TextComments, _=FindBracketedText2(rest, "fanac-headertext", caseInsensitive=True)

        # There should only be one table and that contains the list of con instances
        table, _=FindBracketedText2(rest, "fanac-table", caseInsensitive=True)
        if table == "":
            Log(f"DecodeConSeriesHTML(): failed to find the <fanac-table> tags")
            return False

        # Read the table
        # Get the table header and decode the columns
        header, rest=FindBracketedText2(table, "thead", caseInsensitive=True)
        if header == "":
            Log(f"DecodeConSeriesHTML(): failed to find the <thead> tags in the body")
            return False
        # Find the column headings
        headers=ConSeriesFrame.ReadTableRow(header, "th")

        # Now read the rows
        rows=[]
        while True:
            rowtext, rest=FindBracketedText2(rest, "tr", caseInsensitive=True)
            if rowtext == "":
                break
            row=self.ReadTableRow(rowtext)
            if len(row) < len(headers):
                row.extend(" "*(len(headers)-len(row)))
            rows.append(row)

        cons=[]
        for row in rows:
            con=Con()
            for icol, header in enumerate(headers):
                match header:
                    case "Convention":
                        con.Name, con.URL, con.Extra = self.ConNameInfoUnpack(row[icol])
                    case "Location":
                        con.Locale=row[icol]
                    case _:
                        con[header]=row[icol]

            cons.append(con)
        self.Datasource.Rows=cons

        return True


    #---------------------
    # Unpack a conpubs conname from a con instance convention column  which may include a url, the url's text (a name), and some extra material
    # header is of the form <a href=xxxx>yyyy</a>zzzz
    # Generate the Name, URL and extra columns
    # Reversed by ConNameInfoPack()
    @staticmethod
    def ConNameInfoUnpack(packed: str) -> (str, str, str):
        name=packed
        url=""
        extra=""

        m=re.match('<a href=\"?(.*?)\"?>(.*?)</a>(.*)$', packed, re.IGNORECASE)
        if m is not None:
            url=m.groups()[0].strip()
            name=m.groups()[1].strip()
            extra=m.groups()[2].strip()

        # If there is no extra found and if name is of the form "xxx (yyy)", set name=xxx and extra=(yyy)
        if extra == "":
            m=re.match(r"(.*)\((.*)\)$", name)
            if m is not None:
                if len(m.groups(2)) > 0:
                    name=m.groups()[0]
                    extra=f"({m.groups()[1]})"

        if url == f"{name}/index.html" or url == name:
            url="index.html"

        return name, url, extra


    #---------------------
    # Generate the contents of the Convention column from the Name, URL and extra columns
    # Reverse of ConNameInfoUnpack()
    @staticmethod
    def ConNameInfoPack(name: str, url: str, extra: str) -> str:
        packed=""
        if url == "":
            packed+=f"{name}"
        elif url == "index.html":
            packed+=f'<a href="{name}/index.html">{name}</a>'
        else:
            packed+=f'<a href="{url}">{name}</a>'
        if extra != "":
            packed+=f" {extra}"

        return packed


    # ---------------------
    # Unpack extra: something like stuff (con name) stuff, and ignore some things that might look like con names but aren't. (E.g., (virtual))
    # Return first-stuff, con-name, later-stuff.  If no con-name, it's all in first-stuff
    @staticmethod
    def UnpackExtra(extra: str) -> tuple[str, str, str]:
        m=re.match(r"^([^()]*)(\(.*?\))?(.*)$", extra)
        if m is None:
            return "", "", ""
        if len(m.groups()) == 3:
            g2=str(m.groups()[1])
            if g2.lower() == "(virtual)":    # A Common parenthesized extra that is not a con's name
                return extra, "", ""
            return str(m.groups()[0]), g2, str(m.groups()[2])   # m.groups()[n] is some sort of generalized str
        return extra, "", ""    # No match -- just return


    #-------------------
    # Upload a con series page to the location specified in the class
    def UploadConSeries(self) -> bool:       

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
        for i, row in enumerate(self.Datasource.Rows):
            if len((row.GoHs+row.Locale+row.Name+row.URL).strip()) > 0 or not row.Dates.IsEmpty:
                last=i
        # Delete the row or rows following it
        if last is not None and last < self.Datasource.NumRows-1:
            del self.Datasource.Rows[last+1:]

        # Determine if we're missing 100% of the data for the Dates, Location, or GoH columns so we can drop them from the listing
        #TODO: Do we want to add this??

        # Begin generating the file for uploading
        with ModalDialogManager(ProgressMessage2, f"Uploading /{self.Seriesname}/index.html", parent=self) as pm:

            # We want to do substitutions, replacing whatever is there now with the new data
            # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
            link=FormatLink(f"https://fancyclopedia.org/{WikiPagenameToWikiUrlname(self.Seriesname)}", self.Seriesname)
            file=SubstituteHTML(file, "title", self.Seriesname)
            file=file.replace("fanac-meta-description", f"{self.Seriesname}")
            file=file.replace("fanac-meta-keywords", f"{self.Seriesname}")
            file=SubstituteHTML(file, "fanac-instance", link)
            file=SubstituteHTML(file, "fanac-headertext", self.TextComments)

            showempty=self.m_radioBoxShowEmpty.GetSelection() == 0  # Radio button: Show Empty cons?
            hasdates=len([d.Dates for d in self.Datasource.Rows if d.Dates is not None and isinstance(d.Dates, FanzineDateRange) and not d.Dates.IsEmpty()]) > 0
            haslocations=len([d.Locale for d in self.Datasource.Rows if d.Locale is not None and len(d.Locale) > 0]) > 0
            hasgohs=len([d.GoHs for d in self.Datasource.Rows if d.GoHs is not None and len(d.GoHs) > 0]) > 0

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
            for row in self.Datasource.Rows:
                if (row.URL is None or row.URL == "") and (row.Name is None or row.Name == "") and not showempty:    # Skip empty cons?
                    continue
                newtable+="    <tr>\n"

                # Generate the first column from the name, url and extra
                newtable+=f"    <td>{ConSeriesFrame.ConNameInfoPack(row.Name, row.URL, row.Extra)}</td>\n"

                # And the rest
                if hasdates:
                    newtable+='      <td>'
                    newtable+=str(row.Dates) if row.Dates is not None else ""
                    newtable+='</td>\n'
                if haslocations:
                    newtable+=f'      <td>{row.Locale}</td>\n'
                if hasgohs:
                    newtable+=f'      <td>{row.GoHs}</td>\n'
                newtable+="    </tr>\n"
            newtable+="    </tbody>\n"
            newtable+="  </table>\n"

            file=SubstituteHTML(file, "fanac-table", newtable)

            file=SubstituteHTML(file, "fanac-date", datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST")

            # Now try to FTP the data up to fanac.org
            if self.Seriesname is None or len(self.Seriesname) == 0:
                Log("UploadConSeries: No series name provided")
                return False

            # If there is an old file, save it as a backup.
            if not self._isNewSeriesPage:
                if not FTP().BackupServerFile(f"/{self.Seriesname}/index.html"):
                    Log(f"UploadConSeries: Could not back up server file /{self.Seriesname}/index.html")
                    return False

            if not FTP().PutFileAsString(f"/{self.Seriesname}", "index.html", file, create=True):
                wx.MessageBox("Upload failed")
                return False

            UpdateFTPLog.LogText("Uploaded ConSeries: "+self.Seriesname)

            pm.Update(f"Upload succeeded: /{self.Seriesname}/index.html")
            # Log("UploadConSeries: About to close progress message gadget")
        # Log("UploadConSeries: Finished uploading ConSeries")

        self.MarkAsSaved()      # It was just saved, so unless it's updated again, the dialog can exit without uploading
        self._uploaded=True     # Something's been uploaded
        self.RefreshWindow()

        return True

    #------------------
    # Save a con series object to disk.
    def OnUploadConSeries(self, event):      
        if self.Seriesname is None or len(self.Seriesname) == 0:
            wx.MessageBox("You must supply a convention series name to upload")
            return
        self.UploadConSeries()

    #--------------------------------------------
    # Given the name of the ConSeries, go to fancy 3 and fetch the con series information and fill in a con seres from it.
    def FetchConSeriesFromFancy(self, name, retry: bool=False) -> bool:     
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
        if tables is None or len(tables) == 0:
            msg="fCan't find a table in Fancy 3 page {pageurl}.  Is it possible that its name on Fancy 3 is different?"
            Log(msg)
            self._fancydownloadfailed=True
            wx.MessageBox(msg)
            return False

        bsrows=tables[0].find_all("tr")
        headers=[]
        rows=[]
        for bsrow in bsrows:
            if len(headers) == 0:       # Save the header row separately
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
            Log(f"FetchConSeriesFromFancy: Can't interpret Fancy 3 page '{pageurl}'")
            self._fancydownloadfailed=True
            wx.MessageBox(f"Can't interpret Fancy 3 page '{pageurl}'")
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
        if nloc is None:
            nloc=FindIndexOfStringInList(headers, "Place")

        ngoh=FindIndexOfStringInList(headers, "GoHs")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "GoH")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "Guests of Honor")
        if ngoh is None:
            ngoh=FindIndexOfStringInList(headers, "Guests of Honour")
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

            self.Datasource.Rows.append(con)
        self.Seriesname=name
        self._fancydownloadfailed=False
        self.RefreshWindow()
        return True


    #------------------
    # Create a new, empty, con series
    def OnLoadSeriesFromFancy(self, event):     
        self.DownloadConSeriesFromFancy(self.tConSeries.GetValue())


    def DownloadConSeriesFromFancy(self, seriesname: str):     
        self.Seriesname=seriesname

        with ModalDialogManager(ProgressMessage2, f"Loading {self.Seriesname} from Fancyclopedia 3", parent=self) as pm:
            self.Datasource=ConSeries()
            self.Datasource.Name=self.Seriesname

            ret=self.FetchConSeriesFromFancy(self.Seriesname)
            if not ret:
                return

            self.RefreshWindow()
            pm.Update(f"{self.Seriesname} loaded successfully from Fancyclopedia 3", delay=0.5)


    #------------------
    def RefreshWindow(self, StartRow: int=-1, EndRow: int=-1, StartCol: int=-1, EndCol: int=-1) -> None:
        # Log(f"RefreshWindow: Called: Refreshing {self.Seriesname}")
        self._grid.RefreshWxGridFromDatasource(StartRow=StartRow, EndRow=EndRow, StartCol=StartCol, EndCol=EndCol)
        # Log(f"RefreshWindow: RefreshWxGridFromDatasource() finished")
        self.UpdateNeedsSavingFlag()
        self.bUploadConSeries.Enabled=len(self.Seriesname) > 0
        self.bLoadSeriesFromFancy.Enabled=self.Datasource.NumRows == 0  # If any con instances have been created, don't offer a download from Fancy
        # Log(f"RefreshWindow: Done")

    #------------------
    def OnPopupCreateNewConPage(self, event):     
        irow=self._grid.clickedRow
        self._grid.Datasource.InsertEmptyRows(irow, 1)
        name=MessageBoxInput("Enter name of convention instance to be added.", title="Create a New Convention Instance", Parent=self)
        if name == "":
            return
        # Check to make sure this instance name is not already present.
        for row in self.Datasource.Rows:
            if row.URL == name:
                MessageBox(f"Convention instance {name} already exists in this convention series.")
                return

        # Add the new instance
        self.Datasource.Rows[irow].Name=name
        self.EditConInstancePage(irow, Create=True)

        self._grid.RefreshWxGridFromDatasource()

        self.RegenerateAdjacentConInstancePages(irow)


    #------------------
    def OnPopupAllowEditCell(self, event):     
        # Append a (row, col) tuple for each cell allowing edit. This only lives for the life of this instance.
        icol=self._grid.clickedColumn
        irow=self._grid.clickedRow
        # Have we clicked on a selected block?
        if len(self._grid.Grid.SelectionBlockBottomRight) > 0 and len(self._grid.Grid.SelectionBlockTopLeft) > 0:
            cb=self._grid.Grid.SelectionBlockBottomRight[0].Col
            rb=self._grid.Grid.SelectionBlockBottomRight[0].Row
            ct=self._grid.Grid.SelectionBlockTopLeft[0].Col
            rt=self._grid.Grid.SelectionBlockTopLeft[0].Row
            if cb >= ct and rb >= rt and rb >= 0 and cb < self.Datasource.NumCols:
                for icol in range(ct, cb+1):
                    if self.Datasource.ColDefs[icol].IsEditable == IsEditable.Maybe:
                        for irow in range(rt, rb+1):
                            self._grid.AllowCellEdit(irow, icol)
        # RMBed on a single cell?
        elif icol < len(self.Datasource.ColDefs) and self.Datasource.ColDefs[icol].IsEditable == IsEditable.Maybe:
            self._grid.AllowCellEdit(irow, icol)
        self.RefreshWindow()

    # ------------------
    def OnPopupUnlink(self, event):     
        self.Datasource.Rows[self._grid.clickedRow].URL=""
        self.RefreshWindow()

    # ------------------
    def OnGridEditorShown(self, event):     
        self._grid.OnGridEditorShown(event)

    #------------------
    def EditConInstancePage(self, irow: int, Create: bool=False) -> None:

        # We have three cases:
        # Case 1: edit a con that is on the list and that has an existing page. The URL is filled
        # Case 2: edit a con that is on the list but with no existing page. The URL is blank
        # Case 3: edit a blank line. No name, no URL

        if irow >= self.Datasource.NumRows:
            case=3
        else:
            row=self.Datasource.Rows[irow]
            if row.URL == "":
                case=2
            else:
                assert len(row.Name) > 0
                case=1

        # We need the names of the previous and next con instance to edit or create the next and prev buttons.
        conname=self.Datasource[irow].Name
        prevconname, nextconname=self.GetPrevNext(conname)
        with ModalDialogManager(ConInstanceDialogClass, self._basedirectoryFTP+"/"+self.Seriesname, self.Seriesname, conname, prevconname, nextconname, Create=Create) as dlg:

            if case == 1 and len(dlg.ReturnMessage) > 0:
                wx.MessageBox(dlg.ReturnMessage)
                dlg.Destroy()
                return

            # Log("ModalDialogManager(ConInstanceDialogClass()) started")
            # Construct a description of the convention from the information in the con series entry, if any.
            if irow < self.Datasource.NumRows and len(dlg.ConInstanceTopText.strip()) == 0:
                row=self.Datasource.Rows[irow]
                dates=None
                if row.Dates is not None and type(row.Dates) is not str and not row.Dates.IsEmpty():
                    dates=str(row.Dates)
                locale=None
                if row.Locale is not None and len(row.Locale) > 0:
                    locale=row.Locale
                description=conname
                if dates is not None and locale is not None:
                    description+=" was held "+dates+" in "+locale+"."
                elif dates is not None:
                    description+=" was held "+dates+"."
                elif locale is not None:
                    description+=" was held in " +locale+"."
                if row.GoHs is not None and len(row.GoHs) > 0:
                    gohs=row.GoHs.replace("&amp;", "&")
                    if ("," in gohs and not ", jr" in gohs) or "&" in gohs or " and " in gohs:
                        # Assume that the GoHs are comma-separated. We want to add an and (w/o a comma) between the last two
                        gohs=[x.strip() for x in gohs.split(",")]
                        gohs=", ".join(gohs[:-1])+" and "+gohs[-1]
                        description+="  The GoHs were "+gohs+"."
                    else:
                        description+="  The GoH was "+gohs+"."
                dlg.ConInstanceTopText=description

            dlg.ConInstanceName=conname
            dlg.ConInstanceFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(conname)

            dlg.MarkAsSaved()
            dlg.RefreshWindow()
            dlg.ShowModal() # We don't care about the return value because you can't cancel out of this dialog; all you can do is change nothing
            if self.Datasource.NumRows <= irow:
                for i in range(irow-self.Datasource.NumRows+1):
                    self.Datasource.Rows.append(Con())
            self.Datasource.Rows[irow].Name=dlg.ConInstanceName.strip()
            self.Datasource.Rows[irow].URL="index.html"

        # Log("ModalDialogManager(ConInstanceDialogClass() done")


    #------------------
    def OnPopupDeleteConPage(self, event):     
        irow=self._grid.clickedRow
        if irow >= 0 and irow < self.Datasource.NumRows:
            ret=wx.MessageBox(f"This will delete {self.Datasource.Rows[irow].Name} from the list of conventions on this page, but will not delete "+
                              "its directory or files from fanac.org. You must use FTP to do that.", 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
            if ret == wx.OK:
                self._grid.DeleteRows(irow, 1)
                self.RefreshWindow()


    #------------------
    # This can only deal wityh a simple name: To popup menu item should not be enabled for cons with different links or extras
    def OnPopupRenameConInstancePage(self, event):
        irow=self._grid.clickedRow

        # We know from the RMB popup item activation rules that cols 0 and 1 are identical and this is a real row.
        newname=wxMessageDialogInput("Enter the new convention instance name.  Note that this will also rename the convention instance's folder on the server.", title="Renaming Convention Instance", initialValue=self.Datasource.Rows[irow].Name, parent=self)
        newname=newname.strip()
        if newname is None or newname == "":
            return  # Bail out if no input  provided

        Log(f"OnPopupRenameConInstancePage(row[{irow}] to '{newname}')")
        self.RenameConInstancePage(irow, newname)
        self.Datasource.Rows[irow].Name=newname
        self._grid.RefreshWxGridFromDatasource()
        self.RefreshWindow()

        self.RegenerateAdjacentConInstancePages(irow)

        event.Skip()


    # Scan the series for the next and prev instance names
    def GetPrevNext(self, thisrow: str|int) -> tuple[str|None, str|None]:
        if isinstance(thisrow, str):
            # Find if thisrow is a string, find thisrow's index in the con series
            irow=-1
            for i, row in enumerate(self.Datasource.Rows):
                if row.Name == thisrow:
                    irow=i
                    break
            if irow == -1:
                return None, None
        else:
            irow=thisrow

        # Using that, find the previous and next names
        prev=next=""
        if irow > 0:
            for i in range(irow-1, -1, -1):
                if self.Datasource[i].URL != "":  # If the previous con instance does not exist, the prev button will be nonfunctional
                    prev=self.Datasource.Rows[i].Name
                    break
        if irow+1 < self.Datasource.NumRows:
            for i in range(irow+1, self.Datasource.NumRows):
                if self.Datasource[i].URL != "":  # If the next con instance does not exist, the next button will be nonfunctional
                    next=self.Datasource.Rows[i].Name
                    break

        return prev, next




    def RenameConInstancePage(self, irow: int, newname: str) -> None:

        oldname=self.Datasource.Rows[irow].Name

        if len(oldname) > 0:
            if oldname[0:1] == ".." or oldname[0:2] == "/..":
                Log(f"UploadConSeries(): The old directory name '{oldname}' is not in this directory, so we will not attempt to rename it.")

        with ModalDialogManager(ProgressMessage2, f"Renaming Con instance '{oldname}' as '{newname}' on server", parent=self) as pm:
            FTP().Rename(oldname, newname)

            # Download and then Upload the Con instance page to update its new name.
            pm.Update(f"Refreshing '{newname}'")
            next, prev=self.GetPrevNext(irow)

            Log(f"RegenerateAdjacentConInstancePages '{prev}' and '{next}'")
            self.DownloadThenUploadConInstancePage(self._basedirectoryFTP, self.Seriesname, newname, prev, next, pm=pm)

            prev, next=self.GetPrevNext(oldname)
            if prev is None or next is None:
                Log(f"RenameConInstancePage() can't find {oldname} in Datasource.Rows")
                return

            # Now do the same for the previous and next pages to update the inter-page links.
            self.RegenerateAdjacentConInstancePages(irow)

    #------------------
    # Take an existing con instance and move it to a new con series.  This can either be a simple move or a move-and-link
    # We allow convention xxx in series XXX to be moved to aseries YYY with new name yyy, and the entry in XXX being deleted or renamed with a link to the new location
    def OnPopupChangeConSeries(self, event):      
        irowOld=self._grid.clickedRow
        if irowOld < 0 or irowOld >= self.Datasource.NumRows:
            Log("OnPopupChangeConSeries: bad irow="+str(irowOld))
            return

        ret=wxMessageBox("Is this a Move-(Maybe-Rename)-and-Link-Back? (No selects a simple Move.)", style=wx.YES_NO)
        IsMoveAndLink = ret == wx.ID_YES

        # Create a popup list dialog to select target con series.  Remove self to prevent user error
        # Do not allow selection of same series
        conseriesOld=self.Seriesname
        conserieslist=[x for x in self._conserieslist if x != conseriesOld]
        conseriesNew=""
        with wx.SingleChoiceDialog(None, "Pick a convention series to move it to", "Move a Convention", conserieslist) as dialog:
            if wx.ID_OK == dialog.ShowModal():
                conseriesNew=dialog.GetStringSelection()

        # Abort the operation if nothing is selected
        if conseriesNew == "":
            return

        connameOld=self.Datasource.Rows[irowOld].Name
        connameNew=connameOld
        connameNewOld=connameOld
        if IsMoveAndLink:
            # Ask for the new name of the convention instance
            connameNew=connameOld
            ret=MessageBoxInput("Name for Con Instance in new series", "New name for con instance", connameOld)
            if ret != "":
                connameNew=ret.strip()

            # Should a renamed link remain in the old convention series?  If no, newoldconname is ""
            # In the rare case that the old name is retained unchanged, it must still be entered
            ret=MessageBoxInput("Should a link remain in the old convention series?  If no, return the empty line", "Rename old con instance", connameOld)
            connameNewOld=ret.strip()

        # Ask for confirmation
        query=f"Move convention instance '{connameOld}' to new convention series '{conseriesNew}'"

        if IsMoveAndLink:
            if connameOld != connameNew:
                query+=f"   Rename as '{connameNew}' in new con series"
            if connameNewOld != connameOld:
                if connameNewOld != "":
                    query+=f"   and retain a link to it here as '{connameNewOld}'"
                else:
                    query+=f"   and remove it from '{conseriesOld}'"

        ret=wx.MessageBox(query, 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
        if ret != wx.OK:
            return

        # We have enough information to do the move and have determined that it is safe to do.
        # Get a list of con instances in the new con series
        newConSeriesFrame=ConSeriesFrame(self._basedirectoryFTP, conseriesNew, conserieslist, show=False)
        newSeriesInstanceNames=[x.Name for x in newConSeriesFrame.Datasource.Rows]

        # Find a location in the new con series where the new con instances will be placed.  Assume the new con series is in alphabetic order by con instance name
        irowNew=len(newSeriesInstanceNames)
        if len(newSeriesInstanceNames) == 0:
            irowNew=0
        elif connameNew < newSeriesInstanceNames[0]:
            irowNew=0
        else:
            for i in range(1, len(newSeriesInstanceNames)):
                if connameNew > newSeriesInstanceNames[i]:
                    irowNew=i
                    break

        # Insert an empty row there and then copy the old con series data to the new row.
        # (Note that this is just copying the entry in the con series table, not the data it points to.)
        # Note that we are editing Datasource and ignoring the grid.  This is OK as long as we don't later start playing with the grid or displaying the series.
        newConSeriesFrame.Datasource.InsertEmptyRows(irowNew, 1)
        for i in range(6):    # Copy the old row contents to the new row
            newConSeriesFrame.Datasource.Rows[irowNew][i]=self.Datasource.Rows[irowOld][i]

        oldDirPath = "/" + self.Seriesname + "/" + connameOld
        if self._basedirectoryFTP != "":
            oldDirPath=self._basedirectoryFTP+"/"+oldDirPath

        #------------- Now do the copying and renaming --------------
        # Copy the con instance directory from the old con series directory to the new con series directory, possibly doing some renaming.

        # Create the new con instance directory and move the files.
        dirpathNew="/"+conseriesNew+"/"+connameNew
        with ModalDialogManager(ProgressMessage2, f"Creating {dirpathNew} and copying '{connameOld}' to it.", parent=self) as pm:
            UpdateFTPLog.LogText(f"Moving '{connameOld}' from '{oldDirPath}' to '{dirpathNew}' and renaming it '{connameNew}'")

            # The new con instance *directory* must not already exist.
            if len(self._basedirectoryFTP) > 0:
                dirpathNew=self._basedirectoryFTP+"/"+dirpathNew
            if FTP().PathExists(dirpathNew):
                Log(f"OnPopupChangeConSeries: newDirPath '{dirpathNew}' already exists", isError=True)
                wx.MessageBox(f"OnPopupChangeConSeries: newDirPath '{dirpathNew}' already exists. Move can not proceed.", 'Warning', wx.OK|wx.ICON_WARNING)
                return

            FTP().MKD(dirpathNew)

            # Make a list of the files in the old con instance directory
            fileList=FTP().Nlst(oldDirPath)

            # Copy the contents of the old con instance directory to the new one
            for file in fileList:
                pm.Update(f"Copying {file}")
                if not FTP().CopyFile(oldDirPath, dirpathNew, file):
                    msg=f"OnPopupChangeConSeries: Failure copying {file} from {oldDirPath} to {dirpathNew}\nThis will require hand cleanup."
                    Log(msg, isError=True)
                    wx.MessageBox(msg, 'Warning', wx.OK|wx.CANCEL|wx.ICON_WARNING)
                    return

            # If appropriate, rename the convention in both the old and new con series.
            if not IsMoveAndLink:
                # All we do is move the entry to the new series (which is complete). It's not renamed, and it's not retained in the old con series list
                del self.Datasource.Rows[irowOld]

                # Save the old and new con series. Don't upload the modified old series if uploading the new one failed
                if newConSeriesFrame.UploadConSeries():
                    self.UploadConSeries()
                else:
                    return

                # Finally, delete the old directory
                FTP().DeleteDir(oldDirPath)

            # It's more complicated...
            # Is the copied directory's name in the new con series list being changed?
            if connameNew != connameOld:
                # The con is being renamed in the new conseries
                name, url, extra=ConSeriesFrame.ConNameInfoUnpack(connameNew)
                self.Datasource.Rows[irowNew].Name=name
                self.Datasource.Rows[irowNew].URL="index.html"      # The URL of a con instance local to the series is always this
                self.Datasource.Rows[irowNew].Extra=extra
# UnpackExtra()
            # Is the copied directory's name in the old con series being changed?
            if connameNewOld != connameOld:
                # A link to the convention is being retained in the old series and needs to be renamed.
                name, url, extra=ConSeriesFrame.ConNameInfoUnpack(connameNewOld)
                self.Datasource.Rows[irowOld].Name=name
                self.Datasource.Rows[irowOld].URL=f"../{conseriesNew}/{connameNew}/index.html"      # Reference to the new location
                self.Datasource.Rows[irowOld].Extra=extra


            # Save the old and new con series. Don't upload the modified old series if uploading the new one failed
            if newConSeriesFrame.UploadConSeries():
                self.UploadConSeries()
            else:
                return



    # ------------------
    def OnPopupLinkToAnotherConInstance(self, event):
        newcon=MessageBoxInput("Use a browser to copy the URL of the convention instance you want to link to from the convention series table and paste it here.", "Link an existing convention to this series.")
        m=re.match("https?://fanac.org/conpubs/(.*?/.*?).index.html$", newcon, re.IGNORECASE)
        if m is None:
            MessageBox(f"Could not interperet '{newcon} as a conpubs convention URL")
            event.skip()
            return

        series, con=unquote(m.groups()[0]).split("/")
        irow=self._grid.clickedRow
        #self.Datasource.Rows[irow][0]+=f' (->{series}/{con})'
        self.Datasource.Rows[irow].Name=f"{self.Datasource.Rows[irow].Name} (->{series}/{con})"
        self.Datasource.Rows[irow].URL=unquote(m.groups()[0])
        self.RefreshWindow()
        event.Skip()


    #------------------
    def OnTextFancyURL(self, event):      
        self.RefreshWindow()

    #------------------
    def OnTextConSeriesName( self, event ):     
        self.RefreshWindow()

    #-----------------
    # When the user edits the ConSeries name, we update the Fancy URL (but not vice-versa)
    def ConTextConSeriesKeyUp(self, event):     
        self.TextFancyURL="fancyclopedia.org/"+WikiPagenameToWikiUrlname(self.tConSeries.GetValue())

    #------------------
    def OnTextComments(self, event):      
        self.RefreshWindow()

    #------------------
    def OnGridCellRightClick(self, event):     
        self._grid.OnGridCellRightClick(event, self.m_GridPopup)  # Set enabled state of default items; set all others to False

        icol=self._grid.clickedColumn
        irow=self._grid.clickedRow

        if len(event.EventObject.SelectionBlockBottomRight) > 0 and len(event.EventObject.SelectionBlockTopLeft) > 0:
            cb=event.EventObject.SelectionBlockBottomRight[0].Col
            rb=event.EventObject.SelectionBlockBottomRight[0].Row
            ct=event.EventObject.SelectionBlockTopLeft[0].Col
            rt=event.EventObject.SelectionBlockTopLeft[0].Row
            if cb >= ct and rb >= rt and rb >= 0 and cb < self.Datasource.NumCols:
                self.m_popupAllowEditCell.Enabled=True
        elif icol < len(self.Datasource.ColDefs) and self.Datasource.ColDefs[icol].IsEditable == IsEditable.Maybe:
            self.m_popupAllowEditCell.Enabled=True

        if icol == 0:      # These popup options work on the 1st column only
            self.m_popupCreateNewConPage.Enabled=True
            if irow < self.Datasource.NumRows:
                self.m_popupDeleteConPage.Enabled=True

                if len(self.Datasource.Rows[irow].URL) > 0:   # Only if there's a link in the row
                    self.m_popupUnlink.Enabled=True
                if len(self.Datasource.Rows[irow].URL) == 0:   # Only if there's NO link in the row
                    self.m_popupLinkToOtherConventionInstance.Enabled=True

        if (icol == 0 or icol == 1) and irow < self.Datasource.NumRows:
            self.m_popupRenameConInstancePage.Enabled=True      # We only allow renaming if click is on cols 0 or 1

        if irow < self.Datasource.NumRows and self.Datasource.Rows[irow].URL is not None and self.Datasource.Rows[irow].URL != "":
            self.m_popupChangeConSeries.Enabled=True    # Enable only for rows that exist and point to a con instance

        self.PopupMenu(self.m_GridPopup)

    # ------------------
    def OnGridCellDoubleClick(self, event):     
        self._grid.OnGridCellDoubleClick(event)
        if self._grid.clickedRow >= self.Datasource.NumRows:
            return      # Double-clicking below the bottom means nothing

        # We go into edit mode on the con instance on a double-click to either the Name cell or the Link cell
        if self._grid.clickedColumn in (self.Datasource.ColDefs.index("Name"), self.Datasource.ColDefs.index("Link")):
            irow=event.GetRow()
            url=self.Datasource[irow].URL
            # Is this a link to a con instance in another series?
            if url.startswith("../"):
                url=url.removeprefix("../")
                name="???"
                if len(url.split("/")) > 1:
                    url, name=url.split("/")[0:2]
                wxMessageBox(f"The convention '{self.Datasource[irow].Name}' is not located in convention series '{self.Seriesname}'.\n"
                             f"Edit instance '{name}' in convention series '{unquote(url)}'.")
                return

            # If we double-click on a line that is not yet linked, allow the user to create one.
            if url == "":
                if wx.ID_YES != wxMessageBox(f"No page exists for this convention. Do you wish to create one?", style=wx.YES_NO):
                    return
                # EditConInstancePage() will create a new con instance and populate it from the row.

            self.EditConInstancePage(irow, Create=True)

            self.RefreshWindow()


    #-------------------
    def OnKeyDown(self, event):     
        self._grid.OnKeyDown(event)
        self.UpdateNeedsSavingFlag()

    #-------------------
    def OnKeyUp(self, event):     
        self._grid.OnKeyUp(event)

    #------------------
    def OnPopupCopy(self, event):      
        self._grid.OnPopupCopy(event)

    #------------------
    def OnPopupPaste(self, event):      
        self._grid.OnPopupPaste(event)
        self.UpdateNeedsSavingFlag()


    def OnGridCellChanged(self, event):                    

        # If we're editing the con instance name, we need to record this so that extra processing ca take place on save
        irow=event.GetRow()
        icol=event.GetCol()

        # An edit to the name causes a rename of the page if there is no independent link.  If there is an independent link,
        # then all that's changed is the display text for the link
        if icol == self.Datasource.ColDefs.index("Name"):
            iLinkCol=self.Datasource.ColDefs.index("Link")
            if iLinkCol != -1 and self.Datasource.Rows[iLinkCol].URL != "":
                if irow < self._Datasource.NumRows:
                    newVal=self._grid.Grid.GetCellValue(irow, icol)
                    oldVal=self._Datasource[irow][icol]
                    if newVal != oldVal:
                        self.RenameConInstancePage(irow, newVal)
                    self.UpdateNeedsSavingFlag()
                    return

        if icol == self.Datasource.ColDefs.index("Link"):
            # We need to convert the input into a URL relative to the current server directory
            # Is this a link to another conpubs file or is a link outside of conpubs?
            # Case 1, a relative link
            #       ../Boskone/Boskone 20/Prohgram Book.pdf
            #   Display as-is
            # Case 2, a link copied from a browser
            #       https://www.fanac.org/conpubs/Con*Stellation/Con*Stellation%20IV:%20Aquarius/Program%20Book.pdf#view=Fit
            #   Convert this to Case 1 format
            # Case 3, a link to somewhere else
            #       http://somewhere.com/dir/file.ext
            #       index.html
            #   Display as-is
            val=self._grid.Grid.GetCellValue(irow, icol)
            m=re.match("^https?://(.*)$", val)
            if m is not None:
                val=str(m.group(1))     # Remove leading http[s]
            m=re.match("^(www.)?fanac.org/conpubs/(.*)", val)
            if m is not None:
                val=f"../{m.groups()[1]}"    # Remove www.fanac.org/conpubs/

            self._grid.GridCellChangeProcessing(irow, icol, val)

            self.UpdateNeedsSavingFlag()
            return

        val=self._grid.Grid.GetCellValue(irow, icol)
        self._grid.GridCellChangeProcessing(irow, icol, val)
        self.UpdateNeedsSavingFlag()




    # ------------------
    def OnRegenerateConPages(self, event):
        ret=wx.MessageBox("Are you sure you want to regenerate this convention series's ConInstance pages?", "Are you sure?", wx.OK | wx.CANCEL)
        if ret == wx.CANCEL:
            return

        Log(f"OnRegenerateConPages() called")

        with ModalDialogManager(ProgressMessage2, f"Regenerating all con pages in this con series", parent=self) as pm:
            for irow in range(self.Datasource.NumRows):
                # Do nothing in cases with complex names (e.g., extras or differing links)
                if self.Datasource[irow].URL != "" and self.Datasource[irow].URL != "index.html":
                    Log(f"OnRegenerateConPages(): Skipping {self.Datasource[irow].Name} because of non-empty extra or URL, Name='{self.Datasource[irow].Name}'   Link='{self.Datasource[irow].URL}'  Extra='{self.Datasource[irow].Extra}'")
                    continue

                prevname, nextname=self.GetPrevNext(self.Datasource[irow].Name)
                # We download the page, but don't actually open the dialog.  Then we upload the page which regenerates it.
                self.DownloadThenUploadConInstancePage(f"{self._basedirectoryFTP}/{self.Seriesname}", self.Seriesname, self.Datasource[irow].Name, prevcon=prevname, nextcon=nextname, pm=pm)


    # ------------------
    # When a page gets added, deleted, or renamed, the adjacent pages need to be regenerated to update the next/prev buttons
    def RegenerateAdjacentConInstancePages(self, irow: int, pm=None):

        next, prev=self.GetPrevNext(irow)

        Log(f"RegenerateAdjacentConInstancePages '{prev}' and '{next}'")

        if pm is None:
            with ModalDialogManager(ProgressMessage2, "Regenerating adjacent con instance pages", parent=self) as pm:
                # Now do the same for the previous and next pages to update the inter-page links.
                self.DownloadThenUploadConInstancePage(self._basedirectoryFTP, self.Seriesname, self.Datasource[irow].Name, prev, pm=pm)
                self.DownloadThenUploadConInstancePage(self._basedirectoryFTP, self.Seriesname, self.Datasource[irow].Name, next, pm=pm)
                return

        # Now do the same for the previous and next pages to update the inter-page links.
        self.DownloadThenUploadConInstancePage(self._basedirectoryFTP, self.Seriesname, self.Datasource[irow].Name, prev, pm=pm)
        self.DownloadThenUploadConInstancePage(self._basedirectoryFTP, self.Seriesname, self.Datasource[irow].Name, next, pm=pm)




    # ------------------
    # Download a con instance and then immediately re-upload it.  This will regenerate the page using the latest template and processing.
    # It will also update the next/prev buttons at the bottom.
    def DownloadThenUploadConInstancePage(self, seriespath: str, seriesname: str, conname: str, prevcon: str="", nextcon: str="", pm=None) -> bool:

        # Download a con instance page
        ci=ConInstance(f"{self._basedirectoryFTP}/{seriesname}", seriesname, conname)
        if not ci.Download():
            LogError(f"DownloadThenUploadConInstancePage(): Download of '{conname}' failed.")
            return False

        # And upload it back
        # Override any value read from the server, since they will need to be updated.
        ci.PrevConInstanceName=prevcon
        ci.NextConInstanceName=nextcon

        if not ci.Upload():
            LogError(f"DownloadThenUploadConInstancePage(): Upload of '{conname}' failed.")
            return False

        return True


    # ------------------
    def OnClose(self, event):                             
        self.SetReturnCode(wx.OK)

        if self._fancydownloadfailed:
            self.SetReturnCode(wx.CANCEL)   # We tried a download from Fancy and it failed.
        if OnCloseHandling(event, self.NeedsSaving(), "The convention series has been updated and not yet saved. Exit anyway?"):
            return

        # If anything was uploaded to the website, then we return OK indicating something happened
        if self._uploaded:
            self.EndModal(wx.OK)
            return

        # Otherwise, we return Cancel
        self.EndModal(wx.CANCEL)


    def OnSetShowEmptyRadioBox(self, event):     
        Settings().Put("ConSeriesFramePage:Show empty", self.m_radioBoxShowEmpty.GetSelection())
