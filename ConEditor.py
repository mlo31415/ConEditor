from __future__ import annotations
from typing import Optional, List

import os
import wx
import wx.grid
import math
import sys
from bs4 import BeautifulSoup

from MainConSeriesFrame import MainConSeriesFrame

from HelpersPackage import Bailout, IsInt, StripExternalTags, SubstituteHTML, Color
from Log import LogOpen
from FanzineIssueSpecPackage import FanzineDateRange

from ConSeries import ConSeries, Con
from Grid import Grid

from dlgEnterFancyName import dlgEnterFancyName
from ConFramePage import MainConFrameClass

def ValidateData(a, b):
    return True

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
        self.clipboard=None         # The grid's clipboard
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
        self._grid.SetColTypes(ConSeries._coltypes)
        self._grid.RefreshWindowFromData()
        self.Show(True)

    @property
    def DGrid(self) -> Grid:
        return self._grid

    #------------------
    def OnLoadConSeries(self, event):
        self.ReadConSeries()
        pass

    #------------------
    # Download a ConSeries
    def ReadConSeries(self):

        # Clear out any old information
        self._datasource=ConSeries()
        # for i in range(0, self.DGrid.NumrowsR):
        #     for j in range(0, self.DGrid.NumcolsR):
        #         self.DGrid.Set(i, j, "")

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
        self._datasource.Name=soup.find("abc").text
        self._datasource.Stuff=soup.find("xyz").text
        header=[l.text for l in soup.table.tr.contents if l != "\n"]
        rows=[[m for m in l if m != "\n"] for l in soup.table.tbody if l != "\n"]
        for r in rows:
            r=[StripExternalTags(str(l)) for l in r]
            con=Con()
            con.Seq=int(r[0])
            con.Name=r[1]
            con.Dates=FanzineDateRange().Match(r[2])
            con.Locale=r[3]
            con.GoHs=r[4]
            self._datasource.Rows.append(con)

        # Insert the row data into the grid
        self._grid.RefreshWindowFromData()


    def SaveConSeries(self, filename: str) -> None:
        # First read in the template
        file=None
        with open(os.path.join(self.dirname, "Template")) as f:
            file=f.read()

        # We want to do substitutions, replacing whatever is there now with the new data
        # The con's name is tagged with <abc>, the random text with "xyz"
        file=SubstituteHTML(file, "abc", self._datasource.Name)
        file=SubstituteHTML(file, "xyz", self._datasource.Stuff)

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
        for row in self._datasource.Rows:
            newtable+="    <tr>\n"
            newtable+='      <th scope="row">'+str(row.Seq)+'</th>/n'
            newtable+='      <td>'+row.Name+'<td>\n'
            newtable+='      <td>'+str(row.Dates)+'<td>\n'
            newtable+='      <td>'+row.Locale+'<td>\n'
            newtable+='      <td>'+row.GoHs+'<td>\n'
            newtable+="    </tr>\n"
        newtable+="    </tbody>\n"
        newtable+="  </table>\n"

        file=SubstituteHTML(file, "pdq", newtable)
        with open(filename, "w+") as f:
            f.write(file)


    # #------------------
    # # The ConSeries object has the official information. This function refreshes the display from it.
    # def RefreshWindowFromData(self):
    #     self.DGrid.EvtHandlerEnabled=False
    #     self.DGrid.Grid.ClearGrid()
    #
    #     self.DGrid.SetColHeaders(self.conSeriesData.Colheaders)
    #     self.DGrid.FillInRowNumbers(self.DGrid.NumrowsR)
    #
    #     # Fill in the cells
    #     for i in range(self.conSeriesData.NumRows):
    #         for j in range(len(self.conSeriesData.Colheaders)):
    #             self.DGrid.Set(i, j, self.conSeriesData.Rows[i].GetVal(self.conSeriesData.Colheaders[j]))
    #
    #     self.DGrid.ColorCellsByValue()
    #     #self.DGrid.Grid.ForceRefresh()
    #     self.DGrid.AutoSizeColumns()
    #
    #     self.tTopMatter.Value=self.conSeriesData.Name


    #------------------
    # Save a con series object to disk.
    def OnSaveConSeries(self, event):
        # Rename the old file
        oldname=os.path.join(self.dirname, self.filename)
        newname=os.path.join(self.dirname, os.path.splitext(self.filename)[0]+"-old.html")
        try:
            i=0
            while os.path.exists(newname):
                i+=1
                newname=os.path.join(self.dirname, os.path.splitext(self.filename)[0]+"-old-"+str(i)+".html")

            os.rename(oldname, newname)
        except:
            Bailout(PermissionError, "OnSaveConseries fails when trying to rename "+oldname+" to "+newname, "LSTError")

        try:
            self.SaveConSeries(oldname)
        except:
            Bailout(PermissionError, "OnSaveConseries fails when trying to write file "+oldname, "LSTError")

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
    def OnGridCellDoubleclick(self, event):
        if event.GetRow() == 0 and event.GetCol() == 0:
            self.DGrid.Grid.AutoSize()
            return
        if event.GetRow() == 0 and event.GetCol() > 0:
            self.DGrid.Grid.AutoSizeColumn(event.GetCol())

    #------------------
    def OnGridCellRightClick(self, event):
        self.rightClickedColumn=event.GetCol()

        # Set everything to disabled.
        for mi in self.m_menuPopup.GetMenuItems():
            mi.Enable(False)

        # Everything remains disabled when we're outside the defined columns
        if self.rightClickedColumn > len(self._grid._datasource.ColHeaders)+1 or self.rightClickedColumn == 0:
            return

        # We enable the Copy item if have a selection
        sel=self.LocateSelection()
        if sel[0] != 0 or sel[1] != 0 or sel[2] != 0 or sel[3] != 0:
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Copy"))
            mi.Enable(True)

        # We enable the Paste popup menu item if there is something to paste
        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Paste"))
        mi.Enabled=self.clipboard is not None and len(self.clipboard) > 0 and len(self.clipboard[0]) > 0  # Enable only if the clipboard contains actual content

        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Create New Con Page"))
        mi.Enabled=True

        # Pop the menu up.
        self.PopupMenu(self.m_menuPopup)


    #-------------------
    # Locate the selection, real or implied
    # There are three cases, in descending order of preference:
    #   There is a selection block defined
    #   There is a SelectedCells defined
    #   There is a GridCursor location
    def LocateSelection(self):
        if len(self.DGrid.Grid.SelectionBlockTopLeft) > 0 and len(self.DGrid.Grid.SelectionBlockBottomRight) > 0:
            top, left=self.DGrid.Grid.SelectionBlockTopLeft[0]
            bottom, right=self.DGrid.Grid.SelectionBlockBottomRight[0]
        elif len(self.DGrid.Grid.SelectedCells) > 0:
            top, left=self.DGrid.Grid.SelectedCells[0]
            bottom, right=top, left
        else:
            left=right=self.DGrid.Grid.GridCursorCol
            top=bottom=self.DGrid.Grid.GridCursorRow
        return top, left, bottom, right

    def HasSelection(self):
        if len(self.DGrid.Grid.SelectionBlockTopLeft) > 0 and len(self.DGrid.Grid.SelectionBlockBottomRight) > 0:
            return True
        if len(self.DGrid.Grid.SelectedCells) > 0:
            return True

        return False

    #-------------------
    def OnKeyDown(self, event):
        top, left, bottom, right=self.LocateSelection()

        if event.KeyCode == 67 and self.cntlDown:   # cntl-C
            self.CopyCells(top, left, bottom, right)
        elif event.KeyCode == 86 and self.cntlDown and self.clipboard is not None and len(self.clipboard) > 0: # cntl-V
            self.PasteCells(top, left)
        elif event.KeyCode == 308:                  # cntl
            self.cntlDown=True
        elif event.KeyCode == 68:                   # Kludge to be able to force a refresh (press "d")
            self._grid.RefreshWindowFromData()
        event.Skip()

    #-------------------
    def OnKeyUp(self, event):
        if event.KeyCode == 308:                    # cntl
            self.cntlDown=False
        event.Skip()

    #------------------
    def OnPopupCopy(self, event):
        # We need to copy the selected cells into the clipboard object.
        # (We can't simply store the coordinates because the user might edit the cells before pasting.)
        top, left, bottom, right=self.LocateSelection()
        self.CopyCells(top, left, bottom, right)
        event.Skip()

    #------------------
    def OnPopupPaste(self, event):
        top, left, bottom, right=self.LocateSelection()
        self.PasteCells(top, left)
        event.Skip()

    #------------------
    def CopyCells(self, top, left, bottom, right):
        self.clipboard=[]
        # We must remember that the first two data columns map to a single LST column.
        for row in self._datasource.Rows[top-1: bottom]:
            self.clipboard.append(row[left-1: right])

    #------------------
    def PasteCells(self, top, left):
        # We paste the clipboard data into the block of the same size with the upper-left at the mouse's position
        # Might some of the new material be outside the current bounds?  If so, add some blank rows and/or columns

        # Define the bounds of the paste-to box
        pasteTop=top
        pasteBottom=top+len(self.clipboard)
        pasteLeft=left
        pasteRight=left+len(self.clipboard[0])

        # Does the paste-to box extend beyond the end of the available rows?  If so, extend the available rows.
        num=pasteBottom-len(self._datasource.Rows)-1
        if num > 0:
            for i in range(num):
                self._datasource.Rows.append(["" for x in range(self._datasource.NumRows)])  # The strange contortion is to append a list of distinct empty strings

        # Copy the cells from the clipboard to the grid in lstData.
        i=pasteTop
        for row in self.clipboard:
            j=pasteLeft
            for cell in row:
                self._datasource.Rows[i-1][j-1]=cell  # The -1 is to deal with the 1-indexing
                j+=1
            i+=1
        self._grid.RefreshWindowFromData()

    #------------------
    def OnGridCellChanged(self, event):
        rowR=event.GetRow()
        colR=event.GetCol()
        newVal=self.DGrid.Get(rowR, colR)

        # The first row is the column headers
        if rowR == 0:
            event.Veto()  # This is a bit of magic to prevent the event from making later changes to the grid.
            # Note that the Column Colheaders is offset by *2*. (The first column is the row number column and is blank; the second is the weird filename thingie and is untitled.)
            #TODO: Fix this
            if len(self._datasource.ColHeaders)+1 < colR:
                self._datasource.ColHeaders.extend(["" for x in range(colR-len(self._datasource.ColHeaders)-1)])
            self._datasource.ColHeaders[colR-2]=newVal
            self._grid.RefreshWindowFromData()
            return

        # If we're entering data in a new row or a new column, append the necessary number of new rows of columns to lstData
        while rowR > len(self._grid._datasource.Rows):
            self._grid._datasource.Rows.append(Con())

        while colR > len(self._grid._datasource.ColHeaders):
            self._grid._datasource.Rows[rowR-1].append("")

        # Ordinary columns
        if colR > 0:
            self.DGrid.EvtHandlerEnabled=False
            self._grid._datasource.Rows[rowR-1].SetVal(colR-1, newVal)
            self.DGrid.ColorCellByValue(rowR-1, colR-1)
            self.DGrid.AutoSizeColumns()
            #self.DGrid.Grid.ForceRefresh()
            self.DGrid.EvtHandlerEnabled=True
            return

        # What's left is column zero and thus the user is editing a row number
        # If it's an "X", the row has been deleted.
        if newVal.lower() == "x":
            del self._grid._datasource.Rows[rowR-1]
            event.Veto()                # This is a bit of magic to prevent the event from making later changes to the grid.
            self._grid.RefreshWindowFromData()
            return

        # If it's a number, it is tricky. We need to confirm that the user entered a new number.  (If not, we restore the old one and we're done.)
        # If there is a new number, we re-arrange the rows and then renumber them.
        try:
            newnumf=float(newVal)
        except:
            self.DGrid.Set(rowR, 0, rowR)    # Restore the old value
            return
        newnumf-=0.00001    # When the user supplies an integer, we drop the row *just* before that integer. No overwriting!

        # The indexes the user sees start with 1, but the rows list is 0-based.  Adjust accordingly.
        oldrow=rowR-1

        # We *should* have a fractional value or an integer value out of range. Check for this.
        self.MoveRow(oldrow, newnumf)
        event.Veto()  # This is a bit of magic to prevent the event from making later changed to the grid.
        self._grid.RefreshWindowFromData()
        return


    #------------------
    def MoveRow(self, oldrow, newnumf):
        newrows=[]
        if newnumf < 0:
            # Ok, it's being moved to the beginning
            newrows.append(self._grid._datasource.Rows[oldrow])
            newrows.extend(self._grid._datasource.Rows[0:oldrow])
            newrows.extend(self._grid._datasource.Rows[oldrow+1:])
        elif newnumf > len(self._grid._datasource.Rows):
            # OK, it's being moved to the end
            newrows.extend(self._grid._datasource.Rows[0:oldrow])
            newrows.extend(self._grid._datasource.Rows[oldrow+1:])
            newrows.append(self._grid._datasource.Rows[oldrow])
        else:
            # OK, it've being moved internally
            newrow=math.ceil(newnumf)-1
            if oldrow < newrow:
                # Moving later
                newrows.extend(self._grid._datasource.Rows[0:oldrow])
                newrows.extend(self._grid._datasource.Rows[oldrow+1:newrow])
                newrows.append(self._grid._datasource.Rows[oldrow])
                newrows.extend(self._grid._datasource.Rows[newrow:])
            else:
                # Moving earlier
                newrows.extend(self._grid._datasource.Rows[0:newrow])
                newrows.append(self._grid._datasource.Rows[oldrow])
                newrows.extend(self._grid._datasource.Rows[newrow:oldrow])
                newrows.extend(self._grid._datasource.Rows[oldrow+1:])
        self._grid._datasource.Rows=newrows





# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")
app = wx.App(False)
frame = MainWindow(None, "Convention series editor")
app.MainLoop()

