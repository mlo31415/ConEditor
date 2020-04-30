from __future__ import annotations
from typing import Optional, List

import os
import wx
import wx.grid
import math
import sys
from bs4 import BeautifulSoup

from GUIClass import MainFrame

from HelpersPackage import Bailout, CanonicizeColumnHeaders, StripExternalTags
from Log import LogOpen
from FanzineIssueSpecPackage import FanzineDateRange

from ConSeries import ConSeries, Con

# Define some RGB color constants
colorLabelGray=wx.Colour(230, 230, 230)
colorPink=wx.Colour(255, 230, 230)
colorLightGreen=wx.Colour(240, 255, 240)
colorLightBlue=wx.Colour(240, 230, 255)
colorWhite=wx.Colour(255, 255, 255)


def ValidateData(a, b):
    return True


# The class hides the machinations needed to handle the row and column headers
class Grid():

    def __init__(self, grid: wx.grid.Grid):
        self._grid: wx.grid.Grid=grid

    def Refresh(self, cs: ConSeries):
        assert(False)

    # Set using raw row and column numbers (raw includes the row and column headers as index 0)
    def RawSet(self, row: int, col: int, val: str) ->None:
        if row >= self.Numrows:
            self.AppendEmptyRows(self.Numrows-row+1)
        if col >= self.Numcols:
            self.AppendEmptyCols((self.Numcols-col+1))
        self._grid.SetCellValue(row, col, val)

    # This only gives access to the actual cells
    def Set(self, row: int, col: int, val: str) -> None:
        self.RawSet(row+1, col+1, val)

    def Get(self, row: int, col: int) -> str:
        return self._grid.GetCellValue(row, col)

    @property
    def Numcols(self) -> int:
        return self._grid.NumberCols

    @property
    def Numrows(self) -> int:
        return self._grid.NumberRows
    
    @property
    def Grid(self):
        return self._grid

    def AppendRows(self, rows):
        assert(False)

    def AppendEmptyRows(self, nrows: int) ->None:
        self._grid.AppendRows(nrows)

    def AppendEmptyCols(self, ncols: int) -> None:
        self._grid.AppendCols(ncols)

    def SetColHeaders(self, headers: List[str]) -> None:
        # Color all the column headers white before coloring the ones that actually exist gray.  (This handles cases where a column has been deleted.)
        for i in range(0, self.Numcols-1):
            self.Grid.SetCellBackgroundColour(0, i, colorWhite)

        # Add the column headers
        self.Grid.SetCellValue(0, 0, "")
        i=1
        for colhead in headers:
            self.RawSet(0, i, colhead)               # Set the column header number
            self.Grid.SetCellBackgroundColour(0, i, colorLabelGray)  # Set the column header background
            i+=1
        self.Grid.SetCellBackgroundColour(0, 0, colorLabelGray)
        self.Grid.SetCellBackgroundColour(0, 1, colorLabelGray)

    def SetRowNumbers(self, num: int) -> None:
        # Make the first grid column contain editable row numbers
        for i in range(1, self.Numrows):    # The 0,0 cell is left blank
            self.RawSet(i, 0, str(i))
            self.Grid.SetCellBackgroundColour(i, 0, colorLabelGray)
        self.Grid.SetCellBackgroundColour(0, 0, colorLabelGray)


#####################################################################################
class MainWindow(MainFrame):
    def __init__(self, parent, title):
        MainFrame.__init__(self, parent)

        self.highlightRows=[]       # A List of the names of fanzines in highlighted rows
        self.clipboard=None         # The grid's clipboard
        self.userSelection=None
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None
        self.conSeriesData: ConSeries=ConSeries()
        self.filename: str=""
        self.dirname: str=""

        if len(sys.argv) > 1:
            self.dirname=os.getcwd()

        self._grid: Grid=Grid(self.gRowGrid)
        self.Show(True)

    @property
    def DGrid(self) -> Grid:
        return self._grid

    #------------------
    # Download a ConSeries
    def ReadConSeries(self):

        # Clear out any old information
        self.conSeriesData=ConSeries()
        for i in range(0, self.DGrid.Numrows):
            for j in range(0, self.DGrid.Numcols):
                self.DGrid.Set(i, j, "")

        # Call the File Open dialog to get an LST file
        dlg=wx.FileDialog(self, "Select con series file to load", self.dirname, "", "*.html", wx.FD_OPEN)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        self.filename=dlg.GetFilename()
        self.dirname=dlg.GetDirectory()
        dlg.Destroy()

        file=None
        with open(os.path.join(self.dirname, self.filename)) as f:
            file=f.read()

        soup=BeautifulSoup(file, 'html.parser')

        # We need to extract three things:
        #   The convention series name
        #   The convention series text
        #   The convention series table
        self.conSeriesData.Name=soup.find("abc").text
        self.conSeriesData.Text=soup.find("xyz").text
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
            self.conSeriesData.Rows.append(con)

        # Insert the row data into the grid
        self.RefreshGridFromData()


    #------------------
    def OnLoadConSeries(self, event):
        self.ReadConSeries()
        pass


    #------------------
    # The LSTFile object has the official information. This function refreshes the display from it.
    def RefreshGridFromData(self):
        self.DGrid.EvtHandlerEnabled=False
        self.DGrid.Grid.ClearGrid()

        # The grid is a bit non-standard, since I want to be able to edit row numbers and column headers
        # The row and column labels are actually the (editable) 1st column and 1st row of the spreadsheet (they're colored gray)
        # and the "real" row and column labels are hidden.
        self.gRowGrid.HideRowLabels()
        self.gRowGrid.HideColLabels()

        self.DGrid.SetColHeaders(self.conSeriesData.Colheaders)
        self.DGrid.SetRowNumbers(self.DGrid.Numrows)

        # Fill in the cells
        for i in range(self.conSeriesData.NumRows):
            for j in range(len(self.conSeriesData.Colheaders)):
                self.DGrid.Set(i, j, self.conSeriesData.Rows[i].Val(self.conSeriesData.Colheaders[j]))

        self.ColorCellByValue()
        self.DGrid.Grid.ForceRefresh()
        self.DGrid.Grid.AutoSizeColumns()


    def ColorCellByValue(self):
        # Analyze the data and highlight cells where the data type doesn't match the header.  (E.g., Volume='August', Month='17', year='20')
        # We walk the columns.  For each column we decide on the proper type. Then we ewalk the rows checking the type of data in that column.
        return  # Temporarily hide the rest of the function
        for iCol in range(0, len(self.conSeriesData.Colheaders)):
            colhead=self.conSeriesData.Colheaders[iCol]
            coltype=CanonicizeColumnHeaders(colhead)
            for iRow in range(0, len(self.conSeriesData.Rows)):
                val=self.conSeriesData.DataByIndex(iRow, iCol)
#                self.conSeriesData.Rows[iRow]=val
                color=colorWhite
                if len(val) > 0 and not ValidateData(val, coltype):
                    color=colorPink
                self.DGrid.Grid.SetCellBackgroundColour(iRow, iCol, color)

    #------------------
    # Save an LSTFile object to disk.
    def OnSaveLSTFile(self, event):
        # Rename the old file
        oldname=os.path.join(self.dirname, self.filename)
        newname=os.path.join(self.dirname, os.path.splitext(self.filename)[0]+"-old.LST")
        try:
            i=0
            while os.path.exists(newname):
                i+=1
                newname=os.path.join(self.dirname, os.path.splitext(self.filename)[0]+"-old-"+str(i)+".LST")

            os.rename(oldname, newname)
        except:
            Bailout(PermissionError, "OnSaveLSTFile fails when trying to rename "+oldname+" to "+newname, "LSTError")

        try:
            self.conSeriesData.Save(oldname)
        except:
            Bailout(PermissionError, "OnSaveLSTFile fails when trying to write file "+newname, "LSTError")


    #------------------
    # Create a new, empty, con series
    def OnCreateConSeries(self, event):
        self.conSeriesData=ConSeries()
        self.RefreshGridFromData()
        pass

    #------------------
    def OnTextTopMatter(self, event):
        self.conSeriesData.FirstLine=self.tTopMatter.GetValue()

    #------------------
    def OnTextComments(self, event):
        if self.conSeriesData.TopTextLines is not None and len(self.conSeriesData.TopTextLines) > 0:
            self.conSeriesData.TopTextLines=self.tPText.GetValue().split("\n")
        elif self.conSeriesData.BottomTextLines is not None and len(self.conSeriesData.BottomTextLines) > 0:
            self.conSeriesData.BottomTextLines=self.tPText.GetValue().split("\n")
        else:
            self.conSeriesData.TopTextLines=self.tPText.GetValue().split("\n")

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
        if self.rightClickedColumn > len(self.conSeriesData.Colheaders)+1 or self.rightClickedColumn == 0:
            return

        # We enable the Delete Column item if we're on a deletable column
        if self.rightClickedColumn > 1 and self.rightClickedColumn < len(self.conSeriesData.Colheaders)+1:
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Delete Column"))
            mi.Enable(True)

        # Enable the MoveColRight item if we're in the 2nd data column or later
        if self.rightClickedColumn > 2:
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Move Column Right"))
            mi.Enable(True)

        # Enable the MoveColLeft item if we're in the 2nd data column or later
        if self.rightClickedColumn > 2:
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Move Column Left"))
            mi.Enable(True)

        # We enable the Copy item if have a selection
        sel=self.LocateSelection()
        if sel[0] != 0 or sel[1] != 0 or sel[2] != 0 or sel[3] != 0:
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Copy"))
            mi.Enable(True)

        # We enable the Add Column to Left item if we're on a column to the left of the first -- it can be off the right and a column will be added to the right
        if self.rightClickedColumn > 1:
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Insert Column to Left"))
            mi.Enable(True)

        # We enable the Paste popup menu item if there is something to paste
        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Paste"))
        mi.Enabled=self.clipboard is not None and len(self.clipboard) > 0 and len(self.clipboard[0]) > 0  # Enable only if the clipboard contains actual content

        # We enable the move selection right and left commands only if there is a selection that begins in col 2 or later
        # Enable the MoveColRight item if we're in the 2nd data column or later
        top, left, bottom, right=self.LocateSelection()
        if self.HasSelection():
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Move Selection Right"))
            mi.Enable(True)

        # Enable the MoveColLeft item if we're in the 2nd data column or later
        if left > 1 and self.HasSelection():
            mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Move Selection Left"))
            mi.Enable(True)

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
        elif event.KeyCode == 68:                   # Kludge to be able to force a refresh
            self.RefreshGridFromData()
        event.Skip()

    #-------------------
    def OnKeyUp(self, event):
        if event.KeyCode == 308:                    # cntl
            self.cntlDown=False

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
    def OnPopupDeleteColumn(self, event):
        self.DeleteColumn(self.rightClickedColumn)
        event.Skip()

    #------------------
    def OnPopupAddColumnToLeft(self, event):
        self.AddColumnToLeft(self.rightClickedColumn)
        event.Skip()

    #------------------
    def OnPopupExtractScanner(self, event):
        self.ExtractScanner(self.rightClickedColumn)
        event.Skip()

    #------------------
    def OnPopupMoveColRight(self, event):
        self.MoveColRight(self.rightClickedColumn)

    #------------------
    def OnPopupMoveColLeft(self, event):
        self.MoveColLeft(self.rightClickedColumn)

    # ------------------
    def OnPopupMoveSelectionRight(self, event):
        self.MoveSelectionRight(self.rightClickedColumn)

    # ------------------
    def OnPopupMoveSelectionLeft(self, event):
        self.MoveSelectionLeft(self.rightClickedColumn)

    #------------------
    def CopyCells(self, top, left, bottom, right):
        self.clipboard=[]
        # We must remember that the first two data columns map to a single LST column.
        for row in self.conSeriesData.Rows[top-1: bottom]:
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
        num=pasteBottom-len(self.conSeriesData.Rows)-1
        if num > 0:
            for i in range(num):
                self.conSeriesData.Rows.append(["" for x in range(self.conSeriesData.NumRows)])  # The strange contortion is to append a list of distinct empty strings

        # Does the paste-to box extend beyond the right side of the availables? If so, extend the rows with more columns.
        num=pasteRight-self.conSeriesData.NumRows-1
        if num > 0:
            for row in self.conSeriesData.Rows:
                row.extend([""]*num)

        # Copy the cells from the clipboard to the grid in lstData.
        i=pasteTop
        for row in self.clipboard:
            j=pasteLeft
            for cell in row:
                self.conSeriesData.Rows[i-1][j-1]=cell  # The -1 is to deal with the 1-indexing
                j+=1
            i+=1
        self.RefreshGridFromData()

    #------------------
    def DeleteColumn(self, col):
        col=col-2
        if col >= self.conSeriesData.NumRows or col < 0:
            return

        # For each row, delete the specified column
        # Note that the computed "first page" column *is* in lastData.Rows as it is editable
        for i in range(0, len(self.conSeriesData.Rows)):
            row=self.conSeriesData.Rows[i]
            newrow=[]
            if col > 0:
                newrow.extend(row[:col+1])
            if col < len(row)-3:
                newrow.extend(row[col+2:])
            self.conSeriesData.Rows[i]=newrow

        # Now delete the column header
        del self.conSeriesData.Colheaders[col]

        # And redisplay
        self.RefreshGridFromData()

    # ------------------
    def AddColumnToLeft(self, col):
        col=col-2
        self.conSeriesData.ColHeaders=self.conSeriesData.ColHeaders[:col]+[""]+self.conSeriesData.ColHeaders[col:]
        for i in range(0, len(self.conSeriesData.Rows)):
            row=self.conSeriesData.Rows[i]
            row=row[:col+1]+[""]+row[col+1:]
            self.conSeriesData.Rows[i]=row

        # And redisplay
        self.RefreshGridFromData()

    #------------------
    def MoveColRight(self, rightClickedColumn):
        col=rightClickedColumn-2
        for i in range(0, len(self.conSeriesData.Rows)):
            row=self.conSeriesData.Rows[i]
            if rightClickedColumn > len(row):
                row.append([""])
            row=row[:col+1]+row[col+2:col+3]+row[col+1:col+2]+row[col+3:]
            self.conSeriesData.Rows[i]=row
        ch=self.conSeriesData.ColHeaders
        self.conSeriesData.ColHeaders=ch[:col]+ch[col+1:col+2]+ch[col:col+1]+ch[col+2:]
        # And redisplay
        self.RefreshGridFromData()

    #------------------
    def MoveColLeft(self, rightClickedColumn):
        col=rightClickedColumn-2
        for i in range(0, len(self.conSeriesData.Rows)):
            row=self.conSeriesData.Rows[i]
            if rightClickedColumn > len(row):
                row.append([""])
            row=row[:col]+row[col+1:col+2]+row[col:col+1]+row[col+2:]
            self.conSeriesData.Rows[i]=row
        ch=self.conSeriesData.ColHeaders
        self.conSeriesData.ColHeaders=ch[:col-1]+ch[col:col+1]+ch[col-1:col]+ch[col+1:]
        # And redisplay
        self.RefreshGridFromData()

    #------------------
    def MoveSelectionRight(self, rightClickedColumn):
        top, left, bottom, right=self.LocateSelection()

        for i in range(top-1, bottom):
            row=self.conSeriesData.Rows[i]
            row=row[:left-1]+[""]+row[left-1:right]+row[right+1:]
            self.conSeriesData.Rows[i]=row

        # Move the selection along with it
        self.DGrid.Grid.SelectBlock(top, left+1, bottom, right+1)

        # And redisplay
        self.RefreshGridFromData()

    #------------------
    # Move the selection one column to the left.  The vacated cells to the right are filled with blanks
    def MoveSelectionLeft(self, rightClickedColumn):
        top, left, bottom, right=self.LocateSelection()

        for i in range(top-1, bottom):
            row=self.conSeriesData.Rows[i]
            row=row[:left-2]+row[left-1:right]+[""]+row[right:]
            self.conSeriesData.Rows[i]=row

        # Move the selection along with it
        self.DGrid.Grid.SelectBlock(top, left-1, bottom, right-1)

        # And redisplay
        self.RefreshGridFromData()

    #------------------
    def OnGridCellChanged(self, event):
        row=event.GetRow()
        col=event.GetCol()
        newVal=self.DGrid.Get(row, col)

        # The first row is the column headers
        if row == 0:
            event.Veto()  # This is a bit of magic to prevent the event from making later changes to the grid.
            # Note that the Column Colheaders is offset by *2*. (The first column is the row number column and is blank; the second is the weird filename thingie and is untitled.)
            if len(self.conSeriesData.Colheaders)+1 < col:
                self.conSeriesData.Colheaders.extend(["" for x in range(col-len(self.conSeriesData.Colheaders)-1)])
            self.conSeriesData.Colheaders[col-2]=newVal
            if len(self.conSeriesData.ColumnHeaderTypes)+1 < col:
                self.conSeriesData.ColumnHeaderTypes.extend(["" for x in range(col-len(self.conSeriesData.ColumnHeaderTypes)-1)])
            self.conSeriesData.ColumnHeaderTypes[col-2]=CanonicizeColumnHeaders(newVal)
            self.RefreshGridFromData()
            return

        # If we're entering data in a new row or a new column, append the necessary number of new rows of columns to lstData
        while row > len(self.conSeriesData.Rows):
            self.conSeriesData.Rows.append([""])

        while col > len(self.conSeriesData.Rows[row-1]):
            self.conSeriesData.Rows[row-1].append("")

        # Ordinary columns
        if col > 0:
            self.DGrid.EvtHandlerEnabled=False
            self.conSeriesData.Rows[row-1][col-1]=newVal
            self.ColorCellByValue()
            self.DGrid.Grid.AutoSizeColumns()
            self.DGrid.EvtHandlerEnabled=True
            return

        # What's left is column zero and thus the user is editing a row number
        # If it's an "X", the row has been deleted.
        if newVal.lower() == "x":
            del self.conSeriesData.Rows[row-1]
            event.Veto()                # This is a bit of magic to prevent the event from making later changes to the grid.
            self.RefreshGridFromData()
            return

        # If it's a number, it is tricky. We need to confirm that the user entered a new number.  (If not, we restore the old one and we're done.)
        # If there is a new number, we re-arrange the rows and then renumber them.
        try:
            newnumf=float(newVal)
        except:
            self.DGrid.Set(row, 0, str(row))    # Restore the old value
            return
        newnumf-=0.00001    # When the user supplies an integer, we drop the row *just* before that integer. No overwriting!

        # The indexes the user sees start with 1, but the rows list is 0-based.  Adjust accordingly.
        oldrow=row-1

        # We *should* have a fractional value or an integer value out of range. Check for this.
        self.MoveRow(oldrow, newnumf)
        event.Veto()  # This is a bit of magic to prevent the event from making later changed to the grid.
        self.RefreshGridFromData()
        return


    #------------------
    def MoveRow(self, oldrow, newnumf):
        newrows=[]
        if newnumf < 0:
            # Ok, it's being moved to the beginning
            newrows.append(self.conSeriesData.Rows[oldrow])
            newrows.extend(self.conSeriesData.Rows[0:oldrow])
            newrows.extend(self.conSeriesData.Rows[oldrow+1:])
        elif newnumf > len(self.conSeriesData.Rows):
            # OK, it's being moved to the end
            newrows.extend(self.conSeriesData.Rows[0:oldrow])
            newrows.extend(self.conSeriesData.Rows[oldrow+1:])
            newrows.append(self.conSeriesData.Rows[oldrow])
        else:
            # OK, it've being moved internally
            newrow=math.ceil(newnumf)-1
            if oldrow < newrow:
                # Moving later
                newrows.extend(self.conSeriesData.Rows[0:oldrow])
                newrows.extend(self.conSeriesData.Rows[oldrow+1:newrow])
                newrows.append(self.conSeriesData.Rows[oldrow])
                newrows.extend(self.conSeriesData.Rows[newrow:])
            else:
                # Moving earlier
                newrows.extend(self.conSeriesData.Rows[0:newrow])
                newrows.append(self.conSeriesData.Rows[oldrow])
                newrows.extend(self.conSeriesData.Rows[newrow:oldrow])
                newrows.extend(self.conSeriesData.Rows[oldrow+1:])
        self.conSeriesData.Rows=newrows


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")
app = wx.App(False)
frame = MainWindow(None, "Convention series editor")
app.MainLoop()
