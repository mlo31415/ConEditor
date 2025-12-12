from __future__ import annotations

from bs4 import BeautifulSoup
import wx, wx.grid
import requests

from ConSeries import Con

from HelpersPackage import WikiPagenameToWikiUrlname, FindIndexOfStringInList, RemoveAllHTMLTags, UnformatLinks
from FanzineDateTime import FanzineDateRange
from Log import Log

# --------------------------------------------
# Given the name of the ConSeries, go to fancy 3 and fetch the con series information and fill in a con series from it.
def FetchConSeriesFromFancy(name, retry: bool = False) -> tuple[None|str, None|list[Con]]:
    if name is None or name == "":
        return None, None

    wait=wx.BusyCursor()  # The busy cursor will show until wait is destroyed
    pageurl="https://fancyclopedia.org/"+WikiPagenameToWikiUrlname(name)        # 162.246.254.57
    try:
        response=requests.get(pageurl)
        #response=urlopen(pageurl)
    except Exception as e:
        del wait  # End the wait cursor
        Log("FetchConSeriesFromFancy: Got exception when trying to open "+pageurl)
        if not retry:
            dlg=wx.TextEntryDialog(None, "Load failed. Enter a different name and press OK to retry.", "Try a different name?", value=name)
            if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
                return None, None
            response=dlg.GetValue()
            return FetchConSeriesFromFancy(response)
        return None, None

    html=response.text
    soup=BeautifulSoup(html, 'html.parser')
    del wait  # End the wait cursor

    tables=soup.find_all("table", class_="wikitable mw-collapsible")
    if tables is None or len(tables) == 0:
        msg="fCan't find a table in Fancy 3 page {pageurl}.  Is it possible that its name on Fancy 3 is different?"
        Log(msg)
        wx.MessageBox(msg)
        return None, None

    bsrows=tables[0].find_all("tr")
    headers=[]
    rows=[]
    for bsrow in bsrows:
        if len(headers) == 0:  # Save the header row separately
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
        wx.MessageBox(f"Can't interpret Fancy 3 page '{pageurl}'")
        return None, None

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

    cons: list[Con]=[]
    for row in rows:
        if len(row) != len(headers):  # Merged cells which usually signal a skipped convention.  Ignore them.
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
        cons.append(con)

    return name, cons
