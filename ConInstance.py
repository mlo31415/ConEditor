from __future__ import annotations

import os
import re
import sys

from datetime import datetime

from HelpersPackage import Int0, Float0, RemoveAccents, PyiResourcePath, MessageBox
from HelpersPackage import FindBracketedText2, FindNextBracketedText, FindLinkInString, FormatLink, SubstituteHTML, WikiPagenameToWikiUrlname
from WxDataGrid import GridDataSource, Color, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable
from FTP import FTP
from Log import Log, LogError

# An individual file to be listed under a convention
# This is a single row
class ConInstanceRow(GridDataRowClass):

    def __init__(self):
        self._displayTitle: str=""      # The name as shown to the world on the website
        self._notes: str=""             # The free-format description
        self._localfilename: str=""     # The filename of the source file
        self._localpathname: str="."    # The local pathname of the source file (path+filename)
        self._sitefilename: str=""      # The name to be used for this file on the website (It will be (part of) the URL and holds the URL for link rows.)
        self._size: int=0               # The file's size in bytes
        self._isText: bool=False        # Is this a piece of text rather than a convention?
        self._isLink: bool=False        # Is this a link?
        self._pages: int=0              # Page count


    def __str__(self):      
        s=""
        if len(self.SourceFilename) > 0:
            s+="Source="+self.SourceFilename+"; "
        if len(self.SiteFilename) > 0:
            s+="Sitename="+self.SiteFilename+"; "
        if len(self.DisplayTitle) > 0:
            s+="Display="+self.DisplayTitle+"; "
        if len(self.Notes) > 0:
            s+="Notes="+self.Notes+"; "
        if Float0(self.Size) > 0:
            s+="Size="+str(self.Size)+"; "
        if Int0(self.Pages) > 0:
            s+="Pages="+str(self.Pages)+"; "
        if self.IsTextRow:
            s+="IsTextRow; "
        if self.IsLinkRow:
            s+="IsLinkRow; "

        return s

    # Make a deep copy of a ConInstanceRow
    def Copy(self) -> ConInstanceRow:
        cf=ConInstanceRow()
        cf._displayTitle=self._displayTitle
        cf._notes=self._notes
        cf._localfilename=self._localfilename
        cf._localpathname=self._localpathname
        cf._sitefilename=self._sitefilename
        cf._size=self._size
        cf._isText=self._isText
        cf._isLink=self._isLink
        cf._pages=self._pages
        return cf

    def __hash__(self) -> int:
        tot=hash(self._displayTitle.strip()+self._notes.strip()+self._localfilename.strip()+self._localpathname.strip()+self._sitefilename.strip())
        return tot+hash(self._size)+hash(self._isText)+Int0(self.Pages)


    def append(self, val):
        LogError("Call to ConInstanceRow().append which should never happen.")
        assert False
    def DelCol(self, icol) -> None:
        LogError("Call to ConInstanceRow().DelCol which should never happen.")
        assert False

    @property
    def DisplayTitle(self) -> str:      
        return self._displayTitle
    @DisplayTitle.setter
    def DisplayTitle(self, val: str) -> None:      
        self._displayTitle=val

    @property
    def Notes(self) -> str:      
        return self._notes
    @Notes.setter
    def Notes(self, val: str) -> None:      
        self._notes=val

    @property
    def SourcePathname(self) -> str:      
        return self._localpathname
    @SourcePathname.setter
    def SourcePathname(self, val: str) -> None:      
        self._localpathname=val
        self._localfilename=os.path.basename(val)


    @property
    def SourceFilename(self) -> str:      
        return self._localfilename
    @SourceFilename.setter
    def SourceFilename(self, val: str) -> None:      
        self._localfilename=val
        self._localpathname="invalidated"

    # When a line is a text line, it stores the text in DisplayTitle.  This is just an alias to make the code a bit more comprehensible.
    @property
    def TextLineText(self) -> str:
        return self.DisplayTitle
    @TextLineText.setter
    def TextLineText(self, val: str) -> None:
        self.DisplayTitle=val


    @property
    def SiteFilename(self) -> str:      
        return self._sitefilename
    @SiteFilename.setter
    def SiteFilename(self, val: str) -> None:      
        self._sitefilename=RemoveAccents(val)


    # Size is in MB
    @property
    def Size(self) -> float:
        return self._size
    @Size.setter
    def Size(self, val: int|float|str) -> None:
        if isinstance(val, str):
            val=Float0(val)
        if val > 500:  # We're looking for a value in MB, but if we get a value in bytes, convert it
            val=val/(1024**2)
        self._size=val

    @property
    def Pages(self) -> int:      
        if self._pages is None:
            return 0
        return self._pages
    @Pages.setter
    def Pages(self, val: int|str) -> None:      
        if type(val) is str:
            val=Int0(val)
        self._pages=val

    @property
    def IsTextRow(self) -> bool:      
        return self._isText
    @IsTextRow.setter
    def IsTextRow(self, val: bool) -> None:
        self._isText=val

    @property
    def IsLinkRow(self) -> bool:      
        return self._isLink
    @IsLinkRow.setter
    def IsLinkRow(self, val: bool) -> None:
        self._isLink=val


    # Get or set a value by name or column number in the grid
    def __getitem__(self, index: int|slice) -> str|int|float:
        # (Could use return eval("self."+name))
        if index == 0:
            return self.DisplayTitle
        if index == 1:
            return self.SourceFilename
        if index == 2:
            return self.SiteFilename
        if index == 3:
            if self.Pages == 0:
                return ""
            return self.Pages
        if index == 4:
            return f"{self.Size:.1f}"
        if index == 5:
            return self.Notes
        return "Val can't interpret '"+str(index)+"'"

    def __setitem__(self, index: int|slice, value: str) -> None:      
        # (Could use return eval("self."+name))
        if index == 0:
            self.DisplayTitle=value
            return
        if index == 1:
            self.SourceFilename=value
            return
        if index == 2:
            self.SiteFilename=value
            return
        if index == 3:
            if isinstance(value, int):
                self.Pages=value
            else:
                self.Pages=Int0(value.strip())
            return
        if index == 4:
            self.Size=Float0(value)
            return
        if index == 5:
            self.Notes=value
            return
        print("SetVal can't interpret '"+str(index)+"'")
        raise KeyError


    @property
    def IsEmptyRow(self) -> bool:      
        return self.SourceFilename == "" and self.SiteFilename == "" and self.DisplayTitle == "" and Int0(self.Pages) == 0 and self.Notes != ""



#####################################################################################################
#####################################################################################################
# A class to hold a con instance for uploading and downloading
class ConInstance:

    def __init__(self, basedir: str, seriesname: str, conname: str):
        self._seriesname: str=seriesname
        self._conname: str=conname

        self.FTPSeriesRootPath: str=basedir

        self.PrevConInstanceName: str=""
        self.NextConInstanceName: str=""

        self.Credits: str=""
        self.Toptext: str=""
        self.ConInstanceRows: list[ConInstanceRow]=[]


 # ----------------------------------------------
    def Download(self) -> bool:

        def ValidLocalLink(link: str) -> bool:    # Made a method because it might be reused
            if link is None or link == "":
                return False
            if link[0] == ".":
                return False
            if "/" in link:
                return False
            return True

        if not ValidLocalLink(self._conname):
            return False

        file=FTP().GetFileAsString(f"{self.FTPSeriesRootPath}/{self._conname}", "index.html")
        if file is None:
            LogError(f"DownloadConInstancePage: '{self.FTPSeriesRootPath}/{self._conname}/index.html' does not exist -- create a new file and upload it")
            # wx.MessageBox(self.FTPSeriesRootPath+"/"+self._coninstancename+"/index.html does not exist -- create a new file and upload it")
            return False  # Just return with the ConInstance page empty

        file=file.replace("/n", "")  # I don't know where these are coming from, but they don't belong there!

        body, _=FindBracketedText2(file, "body", caseInsensitive=True)
        if body is None:
            LogError("DownloadConInstancePage(): Can't find <body> tag")
            return False

        fanacInstance, _=FindBracketedText2(body, "fanac-instance", caseInsensitive=True)
        if fanacInstance is None:
            LogError("DownloadConInstancePage(): Can't find <fanac-instance> tag")
            return False

        topButtons, _=FindBracketedText2(body, "fanac-topButtons", caseInsensitive=True)
        if topButtons is None:
            LogError("DownloadConInstancePage(): Can't find <fanac-topButtons> tag")
            return False

        fanacstuff, _=FindBracketedText2(body, "fanac-stuff", caseInsensitive=True)
        if fanacstuff is None:
            LogError("DownloadConInstancePage(): Can't find <fanac-stuff> tag")
            return False
        self.Toptext=fanacstuff

        fanaccredits, _=FindBracketedText2(body, "fanac-credits", caseInsensitive=True)
        if fanaccredits is None:
            LogError("DownloadConInstancePage(): Can't find <fanac-credits> tag")
            return False
        m=re.match(r"^\s*Credits?:?\s*(?:Publications provided by )?(.*?)\s*(<br>)?\s*$", fanaccredits)  # Remove some debris that shows up on older pages.
        if m is not None:
            fanaccredits=m.group(1)
        self.Credits=fanaccredits

        rows: list[tuple[str, str]]=[]
        ulists, _=FindBracketedText2(body, "fanac-table", caseInsensitive=True)

        # The ulists are a series of ulist items, each ulist is a series of <li></li> items
        # The tags usually have ' id="conpagetable"' which can be ignored
        remainder=ulists.replace(' id="conpagetable"', "")
        while True:
            lead, tag, contents, remainder=FindNextBracketedText(remainder)
            if tag == "":
                break
            #Log(f"*** {tag=}  {contents=}")
            if tag == "ul":
                remainder=lead+contents+remainder  # If we encounter a <ul>...</ul> tag, we edit it out, keeping what's outside it and what's inside it
                continue
            rows.append((tag, contents))

        # Get the next and previous conventions from the buttons at the bottom
        pbutton, _=FindBracketedText2(body, "fanac-prevCon")
        if pbutton != "":
            pbutton,_=FindBracketedText2(pbutton, "button")
            if pbutton != "" and pbutton != "(first)":
                self.PrevConInstanceName=pbutton
        nbutton, _=FindBracketedText2(body, "fanac-nextCon")
        if nbutton != "":
            nbutton,_=FindBracketedText2(nbutton, "button")
            if nbutton != "" and nbutton != "(last)":
                self.NextConInstanceName=nbutton

        # Now decode the lines
        for row in rows:
            if row[0] == "li":
                #Log(f"\n{row[1]=}")
                conf=ConInstanceRow()
                # We're looking for an <a></a> followed by <small>/</small>
                a, rest=FindBracketedText2(row[1], "a", includeBrackets=True)
                #Log(f"{a=}   {rest=}")
                if a == "":
                    LogError(f"DownloadConInstancePage(): Can't find <a> tag in {row}")
                    return False
                _, href, text, _=FindLinkInString(a)
                if href == "":
                    LogError(f"DownloadConInstancePage(): Can't find href= in <a> tag in {row}")
                    return False
                # if href is a foreign link, then this is a link line
                if "/" in href:
                    conf.DisplayTitle=text
                    conf.SiteFilename=href
                    conf.IsLinkRow=True
                    self.ConInstanceRows.append(conf)
                    continue
                # Strip any view-Fit specs from the end of the URL.  There may be more than one.
                # They may be of the form
                #       #view=Fit
                #       #xxx=yyy&view-Fit
                # Strategy is to first remove all view=Fit&, then any #view=Fit
                while "view=fit" in href.lower():
                    href=re.sub("view=fit&", "", href, count=99, flags=re.IGNORECASE)
                    href=re.sub("#view=fit", "", href, count=1, flags=re.IGNORECASE)    # Note that if the view=Fit was followed by &anything, it would have been deleted in the previous line

                # It appears to be an ordinary file like
                conf.DisplayTitle=text
                # There are some cases of ugliness -- old errors -- which need to be detected and removed
                # The only one known so far as &%23x27;  The x23 needs to be turned into a # and the resulting &#27x; to a quote
                # It may make sense to generalize on the pattern...or it may not.
                m=re.match(r"(.*)&%([0-9]+)x([0-9]+);(.*)", href)
                if m is not None:
                    if m.groups()[1] == "23" and m.groups()[2] == "27":
                        href=m.groups()[0]+"'"+m.groups()[3]

                conf.SiteFilename=href

                if len(rest.strip()) > 0:
                    small, _=FindBracketedText2(rest, "small")
                    if small == "":
                        LogError(f"DownloadConInstancePage(): Can't find <small> tag in {rest}")
                        return False
                    small=small.replace("&nbsp;", " ")
                    m=re.match(".*?([0-9.]+) MB", small, re.IGNORECASE)
                    if m is not None:
                        conf.Size=Float0(m.group(1))
                    m=re.match(".*?([0-9]+) pp", small, re.IGNORECASE)
                    if m is not None:
                        conf.Pages=Int0(m.group(1))

                self.ConInstanceRows.append(conf)

            elif row[0] == "b":
                conf=ConInstanceRow()
                conf.IsTextRow=True
                conf.TextLineText=row[1]
                self.ConInstanceRows.append(conf)

        return True


    def Upload(self) -> bool:

        # Read in the template
        try:
            Log(f"sys.path[0]=  {sys.path[0]}")
            Log(f"sys.argv[0]=  {sys.argv[0]}")
            Log(f"{os.path.join(sys.path[0], 'Template-ConPage.html')=}")
            with open(PyiResourcePath("Template-ConPage.html")) as f:
                file=f.read()
        except:
            MessageBox("Can't read 'Template-ConPage.html'")
            Log("Can't read 'Template-ConPage.html'")
            return False

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <fanac-instance>, the random text with "fanac-headertext"
        fancylink=FormatLink(f"https://fancyclopedia.org/{WikiPagenameToWikiUrlname(self._conname)}", self._conname)
        file=SubstituteHTML(file, "title", self._conname)
        file=file.replace("fanac-meta-description", f"{self._conname} {self._seriesname} {self.Toptext}")
        file=file.replace("fanac-meta-keywords", f"{self._conname} {self._seriesname} {self.Toptext}")
        file=SubstituteHTML(file, "fanac-instance", fancylink)
        file=SubstituteHTML(file, "fanac-stuff", self.Toptext)

        # Fill in the top buttons
        s=f"<button onclick=\"window.location.href='https://fancyclopedia.org/{WikiPagenameToWikiUrlname(self._conname)}'\"> Fancyclopedia 3 </button>&nbsp;&nbsp;"
        s+=f"<button onclick=\"window.location.href='../index.html'\">All {self._seriesname}s</button>"
        file=SubstituteHTML(file, "fanac-topbuttons", s)


        file=SubstituteHTML(file, "fanac-date", datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST")
        if len(self.Credits.strip()) > 0:
            file=SubstituteHTML(file, "fanac-credits", self.Credits.strip())

        def FormatSizes(row: ConInstanceRow) -> str:
            info=""
            if row.Size > 0 or row.Pages > 0:
                info="<small>("
                if row.Size > 0:
                    info+="{:,.1f}".format(row.Size)+'&nbsp;MB'
                if row.Pages > 0:
                    if row.Size > 0:
                        info+="; "
                    info+=str(row.Pages)+" pp"
                info+=")</small>"
            return info

        # Now construct the table which we'll then substitute.
        newtable='<ul id="conpagetable">\n'
        for i, row in enumerate(self.ConInstanceRows):
            if row.IsTextRow:
                text=f"{row.SourceFilename} {row.SiteFilename} {row.DisplayTitle} {row.Notes}"
                newtable+=f'    </ul><b>{text.strip()}</b><ul id="conpagetable">\n'
            elif row.IsLinkRow:
                newtable+=f'    <li id="conpagetable">{FormatLink(row.SiteFilename, row.DisplayTitle)}</li>\n'
            else:
                s=row.DisplayTitle
                parts=os.path.splitext(row.DisplayTitle)
                if parts[1].lower() in [".pdf", ".jpg", ".png", ".doc", ".docx"]:
                    s=parts[0]
                newtable+='    <li id="conpagetable">'+FormatLink(row.SiteFilename, s)

                val=FormatSizes(row)
                if len(val) > 0:
                    newtable+='&nbsp;&nbsp;'+val
                newtable+='\n'

                # Notes
                if len(row.Notes) > 0:
                    newtable+=f"&nbsp;&nbsp;({row.Notes})"
                newtable+="</li>\n"
        newtable+="</ul>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "fanac-table", newtable)

        def UpdateButton(file: str, target: str, series: str, URLname: str) -> str:
            if URLname == "first" or URLname == "last" or URLname == "":
                if URLname == "":
                    URLname="first" if "prev" in target else "last"
                html=f"<button>{URLname}</button>"
            else:
                url=f"https://www.fanac.org/conpubs/{series}/{URLname}/index.html"
                url=url.replace(" ", "%20")
                html=f"<button onclick=window.location.href='{url}'>{URLname}</button>"

            return SubstituteHTML(file, target, html)

        # Update the prev- and next-con nav buttons
        file=UpdateButton(file, "fanac-prevCon", self._seriesname, self.PrevConInstanceName)
        file=UpdateButton(file, "fanac-nextCon", self._seriesname, self.NextConInstanceName)

        # Make a backup of the existing index file
        if not FTP().BackupServerFile(f"/{self._seriesname}/{self._conname}/index.html"):
            Log(f"DownloadThenUploadConInstancePage(): Could not back up server file {self._seriesname}/{self._conname}/index.html")
            return False

        if not FTP().PutFileAsString(f"/{self._seriesname}/{self._conname}", "index.html", file, create=True):
            Log(f"Upload failed: /{self._seriesname}/{self._conname}/index.html")
            MessageBox(f"OnUploadConInstancePage: Upload failed: /{self._seriesname}/{self._conname}/index.html")
            return False

        return True



#####################################################################################################
#####################################################################################################
# The Datasource for a ConInstanceDialogClass
class ConInstanceDatasource(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList=ColDefinitionsList([
            ColDefinition("Display Name", Width=75),
            ColDefinition("Source File Name", Width=100, IsEditable=IsEditable.Maybe),
            ColDefinition("Site Name", Type="url", Width=75),
            ColDefinition("Pages", Type="int", IsEditable=IsEditable.Maybe),
            ColDefinition("Size (MB)", Type="float", IsEditable=IsEditable.Maybe),
            ColDefinition("Notes", Width=150)
        ])
        self._element=ConInstanceRow
        self._coninstanceRows: list[ConInstanceRow]=[]  # This supplies the Rows property that GridDataSource needs
        self._name: str=""
        self._specialTextColor: Color|None=None



    def __hash__(self) -> int:
        s=self._colDefs.Signature()+hash(self._name.strip())+hash(self._specialTextColor)
        return s+sum([x.Signature()*(i+1) for i, x in enumerate(self._coninstanceRows)])
    def Signature(self) -> int:
        return self.__hash__()


    @property
    def CanMoveColumns(self) -> bool:
        return False    # We don't allow moving columns

    @property        
    def Rows(self) -> list:
        return self._coninstanceRows
    @Rows.setter
    def Rows(self, rows: list) -> None:        
        self._coninstanceRows=rows

    @property        
    def ColDefs(self) -> ColDefinitionsList:
        return self._colDefs

    @property
    def TextAndHrefCols(self) -> (int, int):
        return self.ColHeaderIndex("Display Name"), self.ColHeaderIndex("Site Name")    # These are the cols to be used for link text and href

    @property        
    def Name(self) -> str:
        return self._name
    @Name.setter
    def Name(self, val: str) -> None:        
        self._name=val

    @property        
    def NumRows(self) -> int:
        return len(self._coninstanceRows)

    def __getitem__(self, index) -> ConInstanceRow:
        return self._coninstanceRows[index]

    def __setitem__(self, index, value: ConInstanceRow) -> None:
        self._coninstanceRows[index]=value

    @property        
    def SpecialTextColor(self) -> Color|None:
        return self._specialTextColor
    @SpecialTextColor.setter
    def SpecialTextColor(self, val: Color|None) -> None:        
        self._specialTextColor=val

    def InsertEmptyRows(self, index: int, num: int=1) -> None:        
        if num <= 0:
            return
        if index > len(self.Rows):
            index=len(self.Rows)
        self.Rows=self.Rows[:index]+[ConInstanceRow() for _ in range(num)]+self.Rows[index:]


