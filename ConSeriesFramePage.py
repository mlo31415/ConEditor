from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup

from GeneratedConSeriesFrame import MainConSeriesFrame

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML
from Log import LogOpen
from FanzineIssueSpecPackage import FanzineDateRange

from ConSeries import ConSeries, Con
from Grid import Grid

from dlgEnterFancyName import dlgEnterFancyName
from ConInstanceFramePage import MainConFrameClass


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

        self.highlightRows=[]       # A List of the names of fanzines in highlighted rows
        self.userSelection=None
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None
        self.filename: str=""
        self.dirname: str=""

        if len(sys.argv) > 1:
            self.dirname=os.getcwd()

        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConSeries()
        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(ConSeries._coldatatypes)
        self._grid.RefreshWindowFromData()
        self.Show(True)

    #------------------
    def OnLoadConSeries(self, event):
        self.ReadConSeries()
        pass

    #------------------
    # Download a ConSeries
    def ReadConSeries(self):

        # Clear out any old information
        self._grid._datasource=ConSeries()

        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select con series file to load", self.dirname, "", "*.html", wx.FD_OPEN)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        self.filename=dlg.GetFilename()
        self.dirname=dlg.GetDirectory()
        dlg.Destroy()

        with open(os.path.join(self.dirname, self.filename)) as f:
            file=f.read()

        soup=BeautifulSoup(file, 'html.parser')

        # We need to extract three things:
        #   The convention series name
        #   The convention series text
        #   The convention series table
        self._grid._datasource.Name=soup.find("abc").text
        self._grid._datasource.Stuff=soup.find("xyz").text
        header=[l.text for l in soup.table.tr.contents if l != "\n"]
        rows=[[m for m in l if m != "\n"] for l in soup.table.tbody if l != "\n"]
        for row in rows:
            r=[StripExternalTags(str(l)) for l in row]+([None, None, None, None, None])
            con=Con()
            con.Seq=int(r[0]) if r[0] is not None else 0
            con.Name=r[1] if r[1] is not None else ""
            fd=FanzineDateRange().Match(r[2])
            con.Date= fd if r[2] is not None else str(r[2])
            con.Locale=r[3]  if r[3] is not None else ""
            con.GoHs=r[4] if r[4] is not None else ""
            self._grid._datasource.Rows.append(con)

        # Insert the row data into the grid
        self._grid.RefreshWindowFromData()


    def SaveConSeries(self, filename: str) -> None:
        # First read in the template
        file=None
        with open(os.path.join(self.dirname, "Template-ConSeries")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        file=SubstituteHTML(file, "abc", self._grid._datasource.Name)
        file=SubstituteHTML(file, "xyz", self._grid._datasource.Stuff)

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
            newtable+="    <tr>\n"
            newtable+='      <th scope="row">'+str(row.Seq)+'</th>\n'
            newtable+='      <td>'+row.Name+'</td>\n'
            newtable+='      <td>'+str(row.Dates)+'</td>\n'
            newtable+='      <td>'+row.Locale+'</td>\n'
            newtable+='      <td>'+row.GoHs+'</td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "pdq", newtable)
        with open(filename, "w+") as f:
            f.write(file)

    #------------------
    # Save a con series object to disk.
    def OnSaveConSeries(self, event):
        # Rename the old file
        oldname=os.path.join(self.dirname, self.filename)
        newname=os.path.join(self.dirname, os.path.splitext(self.filename)[0]+"-old.html")
        if os.path.exists(oldname):
            try:
                i=0
                while os.path.exists(newname):
                    i+=1
                    newname=os.path.join(self.dirname, os.path.splitext(self.filename)[0]+"-old-"+str(i)+".html")

                os.rename(oldname, newname)
            except:
                Bailout(PermissionError, "OnSaveConseries fails when trying to rename "+oldname+" to "+newname, "ConEditorError")

        try:
            self.SaveConSeries(oldname)
        except:
            Bailout(PermissionError, "OnSaveConseries fails when trying to write file "+oldname, "ConEditorError")

    #------------------
    # Create a new, empty, con series
    def OnCreateConSeries(self, event):
        self._dlgEnterFancyName=dlgEnterFancyNameWindow(None)
        self._datasource=ConSeries()
        self._datasource.Name=self._dlgEnterFancyName._FancyName
        self._grid.RefreshWindowFromData()
        pass

    #------------------
    def OnCreateNewConPage(self, event):
        frame=MainConFrameClass(None)
        rowR=self._grid.rightClickedRow
        colR=self._grid.rightClickedColumn
        frame.tConInstanceName.Value=self._grid._datasource.GetData(rowR-1, colR-1)

        frame.Show()

    #------------------
    def OnTextFancyURL(self, event):
        self._datasource.FirstLine=self.tTopMatter.GetValue()

    #------------------
    def OnTextComments(self, event):
        if self._datasource.Stuff is not None and len(self._datasource.Stuff) > 0:
            self._datasource.Stuff=self.tPText.GetValue().split("\n")
        elif self._datasource.BottomTextLines is not None and len(self._datasource.BottomTextLines) > 0:
            self._datasource.BottomTextLines=self.tPText.GetValue().split("\n")
        else:
            self._datasource.Stuff=self.tPText.GetValue().split("\n")

    #------------------
    def OnGridCellRightClick(self, event):
        self._grid.OnGridCellRightClick(event, self.m_menuPopup)

        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Create New Con Page"))
        mi.Enabled=True

        self.PopupMenu(self.m_menuPopup)

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

