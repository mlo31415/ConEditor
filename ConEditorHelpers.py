from __future__ import annotations

import html
from bs4 import BeautifulSoup
import wx, wx.grid
import requests

from ConSeries import Con

from HelpersPackage import WikiPagenameToWikiUrlname, FindIndexOfStringInList, RemoveAllHTMLTags, UnformatLinks
from FanzineDateTime import FanzineDateRange
from Log import Log, LogError

# --------------------------------------------
# Given the name of the ConSeries, go to fancy 3 and fetch the con series information and fill in a con series from it.
def FetchConSeriesFromFancy(name, retry: bool = False, silent: bool = False) -> tuple[None|str, None|list[Con]]:
    """Fetch convention series data from Fancyclopedia 3.
    silent=True suppresses all user-facing popups (use when the lookup is optional/best-effort)."""
    if name is None or name == "":
        return None, None

    wait=wx.BusyCursor()  # The busy cursor will show until wait is destroyed
    pageurl="https://fancyclopedia.org/"+WikiPagenameToWikiUrlname(name)        # 162.246.254.57
    try:
        response=requests.get(pageurl)
    except Exception:
        del wait  # End the wait cursor
        Log("FetchConSeriesFromFancy: Got exception when trying to open "+pageurl)
        if not retry and not silent:
            dlg=wx.TextEntryDialog(None, "Load failed. Enter a different name and press OK to retry.", "Try a different name?", value=name)
            if dlg.ShowModal() == wx.CANCEL or len(dlg.GetValue().strip()) == 0:
                return None, None
            response=dlg.GetValue()
            return FetchConSeriesFromFancy(response)
        return None, None

    soup=BeautifulSoup(response.text, 'html.parser')
    del wait  # End the wait cursor

    tables=soup.find_all("table", class_="wikitable mw-collapsible")
    if tables is None or len(tables) == 0:
        msg=f"Can't find a table in Fancy 3 page {pageurl}.  Is it possible that its name on Fancy 3 is different?"
        Log(msg)
        if not silent:
            wx.MessageBox(msg)
        return None, None

    for table in tables:
        bsrows=table.find_all("tr")
        headers=[]
        rows=[]
        for bsrow in bsrows:
            if len(headers) == 0:  # Save the header row separately
                heads=bsrow.find_all("th")
                if len(heads) > 0:
                    for head in heads:
                        headers.append(head.contents[0])
                    headers=[html.unescape(RemoveAllHTMLTags(UnformatLinks(str(h))).strip()) for h in headers]
                    continue

            # Ordinary row
            cols=bsrow.find_all("td")
            if len(cols) == 0:
                continue
            # A cell that spans columns marks an intentional section/divider row
            # (e.g. "First Series of Boskones"), not a malformed convention row.
            merged=any(col.has_attr("colspan") for col in cols)
            row=[html.unescape(RemoveAllHTMLTags(UnformatLinks(str(col))).strip()) for col in cols]
            rows.append((row, merged))

        # Skip tables that aren't the convention list (e.g. the "Blizzard" trivia table on the
        # Boskone page): no rows, or no recognizable name column.
        if len(headers) == 0 or len(rows) == 0:
            continue
        nname=FindIndexOfStringInList(headers, "Convention")
        if nname is None:
            nname=FindIndexOfStringInList(headers, "Name")
        if nname is None:
            continue

        # This is the convention table.  Identify the remaining columns.
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
        badrows=[]
        for row, merged in rows:
            if merged:
                continue  # Intentional section-divider/spanning row: skip silently.
            if len(row) != len(headers):
                # A real data row with the wrong number of columns (e.g. a con missing its trailing,
                # not-yet-known "Size" cell). It can't be parsed reliably, so skip it -- but record it
                # so we can warn the user and the source page can be fixed.
                badrows.append(row)
                continue
            con=Con()
            con.Name=row[nname]
            if ndate is not None:
                con.Dates=FanzineDateRange().Match(row[ndate])
            if nloc is not None:
                con.Locale=row[nloc]
            if ngoh is not None:
                con.GoHs=row[ngoh]
            cons.append(con)

        # Log every malformed row, and warn the user once, so the Fancyclopedia page gets fixed.
        if len(badrows) > 0:
            for r in badrows:
                LogError(f"FetchConSeriesFromFancy: wrong-length row in Fancy 3 page '{name}' (convention skipped): {r}")
            wx.MessageBox(f"The Fancyclopedia 3 page '{name}' has {len(badrows)} row(s) with the wrong number of "
                          f"columns. Those conventions were skipped and won't appear here -- please fix the page so "
                          f"they aren't lost:\n{pageurl}",
                          "Malformed rows on a Fancyclopedia page")

        return name, cons

    # No convention table found on the page.
    Log(f"FetchConSeriesFromFancy: No convention table found on Fancy 3 page '{pageurl}'")
    if not silent:
        wx.MessageBox(f"Can't interpret Fancy 3 page '{pageurl}'")
    return None, None
