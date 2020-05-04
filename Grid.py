from __future__ import annotations
from typing import List

import wx
import wx.grid
import math

from HelpersPackage import Color, IsInt
from FanzineIssueSpecPackage import FanzineDateRange, FanzineDate

class GridDataSource():

    @property
    def Element(self):
        return self._element

    @property
    def ColHeaders(self) -> List[str]:
        return []

    @property
    def ColDataTypes(self) -> List[str]:
        return []

    @property
    def ColMinWidths(self) -> List[int]:
        return []

    @property
    def NumRows(self) -> int:
        return -1

    def Data(self, iRow: int, iCol: int) -> str:
        pass

    @property
    def Rows(self) -> List:     # Types of list elements needs to be undefined since we don't know what they will be.
        return []

    @Rows.setter
    def Rows(self, rows: List) -> None:
        pass


# The class hides the machinations needed to handle the row and column headers
class Grid():

    def __init__(self, grid: wx.grid.Grid):
        self._grid: wx.grid.Grid=grid

        self._datasource: GridDataSource=GridDataSource()
        self.clipboard=None         # The grid's clipboard

        # The grid is a bit non-standard, since I want to be able to edit row numbers and column headers
        # The row and column labels are actually the (editable) 1st column and 1st row of the spreadsheet (they're colored gray)
        # and the "real" row and column labels are hidden.
        self._grid.HideRowLabels()
        self._grid.HideColLabels()


    # Set a value in the source data using logical coordinates
    def SetSourceValue(self, iRow: int, iCol: int, val) -> None:
        nrows=len(self._datasource.Rows)
        if iRow >= nrows:
            self._datasource.Rows.extend([self._datasource.Element]*(iRow-nrows+1))
        ncols=len(self._datasource.ColHeaders)
        assert(ncols > iCol)   # Can't extend columns this way.

        c=self._datasource.Rows[iRow]
        try:
            c.SetVal(c, iCol, val)
        except:
            pass

    # Set a grid cell value using raw coordinates
    def SetCellValueR(self, iRowR: int, iColR: int, val) -> None:
        # Extend the grid if needed
        nrows=self._grid.GetNumberRows()
        if iRowR >= nrows:
            self._grid.AppendRows(iRowR-nrows+1)
        ncols=self._grid.GetNumberCols()
        if iColR >= ncols:
            self._grid.AppendCols(iColR-ncols+1)

        # None values are replaced by empty strings
        if val is None:
            val=""
        if type(val) is not str:
            val=str(val)

        self._grid.SetCellValue(iRowR, iColR, val)

    # Set a grid cell value using logical coordinates
    def SetCellValue(self, iRow: int, iCol: int, val) -> None:
        g=self.SetCellValueR(iRow+1, iCol+1, val)

    # Get a cell value using raw indexing
    def Get(self, rowR: int, colR: int) -> str:
        return self._grid.GetCellValue(rowR, colR)

    @property
    # Get the number of raw columns
    def NumcolsR(self) -> int:
        return self._grid.NumberCols

    @NumcolsR.setter
    # Get or set the number of raw columns
    def NumcolsR(self, nColsR: int) -> None:
        if self._grid.NumberCols == nColsR:
            return
        if self._grid.NumberCols > nColsR:
            self._grid.DeleteCols(nColsR, self._grid.NumberCols-nColsR)
        else:
            self._grid.AppendCols(nColsR, self._grid.NumberCols-nColsR)

    @property
    # Get the number of logical columns
    def Numcols(self) -> int:
        return self.NumcolsR-1

    @Numcols.setter
    # Set the number of logical columns
    def Numcols(self, ncols: int) -> None:
        self.NumcolsR=ncols+1

    @property
    def NumrowsR(self) -> int:
        return self._grid.NumberRows

    @property
    def Grid(self):
        return self._grid

    def AppendRows(self, rows):
        assert (False)

    def AppendEmptyRows(self, nrows: int) -> None:
        self._grid.AppendRows(nrows)

    def AppendEmptyCols(self, ncols: int) -> None:
        self._grid.AppendCols(ncols)

    def SetColHeaders(self, headers: List[str]) -> None:
        self._colheaders=headers
        self.Numcols=len(headers)
        if len(headers) == self.Numcols:

            # Color all the column headers white before coloring the ones that actually exist gray.  (This handles cases where a column has been deleted.)
            for iRowR in range(0, self.NumcolsR-1):
                self.Grid.SetCellBackgroundColour(0, iRowR, Color.White)

            # Add the column headers
            self.Grid.SetCellValue(0, 0, "")
            iColR=1
            for colhead in headers:
                self.SetCellValueR(0, iColR, colhead)  # Set the column header number
                self.Grid.SetCellBackgroundColour(0, iColR, Color.LabelGray)  # Set the column header background
                iColR+=1
            self.Grid.SetCellBackgroundColour(0, 0, Color.LabelGray)


    def SetColTypes(self, coldatatypes: List[str]) -> None:
        self._coldatatypes=coldatatypes

    def SetColMinWidths(self, defaultwidths: List[int]) -> None:
        self._colminwidths=defaultwidths

    def AutoSizeColumns(self):
        self._grid.AutoSizeColumns()
        if len(self._datasource.ColMinWidths) == self._grid.NumberCols-1:
            iColR=1     # Skip the first columnw hich contains the row number
            for width in self._datasource.ColMinWidths:
                w=self.Grid.GetColSize(iColR)
                if w < width:
                    self.Grid.SetColSize(iColR, width)
                iColR+=1


    def FillInRowNumbers(self, num: int) -> None:
        # Make the first grid column contain editable row numbers
        for iRowR in range(1, self.NumrowsR):  # The 0,0 cell is left blank
            self.SetCellValueR(iRowR, 0, str(iRowR))
            self.Grid.SetCellBackgroundColour(iRowR, 0, Color.LabelGray)
        self.Grid.SetCellBackgroundColour(0, 0, Color.LabelGray)

    def SetCellBackgroundColor(self, row, col, color):
        self.Grid.SetCellBackgroundColour(row+1, col+1, color)
        #print("("+str(row+1)+", "+str(col+1)+") --> "+str(color))

    # Row, col are Grid coordinates
    def ColorCellByValue(self, row: int, col: int) -> None:
        # Start by setting color to white
        self.SetCellBackgroundColor(row, col, Color.White)

        val=self._grid.GetCellValue(row+1, col+1)
        # We skip testing for "str"-type columns since anything at all is OK in a str column
        if self._coldatatypes[col] == "int":
            if val is not None and val != "" and not IsInt(val):
                self.SetCellBackgroundColor(row, col, Color.Pink)
        elif self._coldatatypes[col] == "date range":
            if val is not None and val != "" and FanzineDateRange().Match(val).IsEmpty():
                self.SetCellBackgroundColor(row, col, Color.Pink)
        elif self._coldatatypes[col] == "date":
            if val is not None and val != "" and FanzineDate().Match(val).IsEmpty():
                self.SetCellBackgroundColor(row, col, Color.Pink)

    def ColorCellsByValue(self):
        if len(self._coldatatypes) != self._grid.NumberCols-1:  # -1 to ignore row number column
            return

        # Analyze the data and highlight cells where the data type doesn't match the header.  (E.g., Volume='August', Month='17', year='20')
        # Col 0 is a number and 3 is a date and the rest are strings.   We walk the rows checking the type of data in that column.
        for iRow in range(0, self._grid.NumberRows-1):
            for iCol in range(0, self._grid.NumberCols-1):
                self.ColorCellByValue(iRow, iCol)


    def RefreshWindowFromData(self):
        self.EvtHandlerEnabled=False
        self.Grid.ClearGrid()

        self.SetColHeaders(self._colheaders)
        self.FillInRowNumbers(self.NumrowsR)

        # Fill in the cells
        for i in range(self._datasource.NumRows):
            for j in range(len(self._colheaders)):
                self.SetCellValue(i, j, self._datasource.Data(i, j))

        self.ColorCellsByValue()      #TODO: Maybe merge these into one call?
        self.AutoSizeColumns()

        #TODO: How to virtualize this?
        self.tConName="missing name"#self._conPage._name
        
    #------------------
    def MoveRow(self, oldrow, newnumf):
        newrows=[]
        if newnumf < 0:
            # Ok, it's being moved to the beginning
            newrows.append(self._datasource.Rows[oldrow])
            newrows.extend(self._datasource.Rows[0:oldrow])
            newrows.extend(self._datasource.Rows[oldrow+1:])
        elif newnumf > len(self._datasource.Rows):
            # OK, it's being moved to the end
            newrows.extend(self._datasource.Rows[0:oldrow])
            newrows.extend(self._datasource.Rows[oldrow+1:])
            newrows.append(self._datasource.Rows[oldrow])
        else:
            # OK, it've being moved internally
            newrow=math.ceil(newnumf)-1
            if oldrow < newrow:
                # Moving later
                newrows.extend(self._datasource.Rows[0:oldrow])
                newrows.extend(self._datasource.Rows[oldrow+1:newrow])
                newrows.append(self._datasource.Rows[oldrow])
                newrows.extend(self._datasource.Rows[newrow:])
            else:
                # Moving earlier
                newrows.extend(self._datasource.Rows[0:newrow])
                newrows.append(self._datasource.Rows[oldrow])
                newrows.extend(self._datasource.Rows[newrow:oldrow])
                newrows.extend(self._datasource.Rows[oldrow+1:])
        self._datasource.Rows=newrows

    # ------------------
    def CopyCells(self, top, left, bottom, right):
        self.clipboard=[]
        # We must remember that the first two data columns map to a single LST column.
        for row in self._datasource.Rows[top-1: bottom]:
            self.clipboard.append(row[left-1: right])

    # ------------------
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
        self.RefreshWindowFromData()


    #------------------
    def OnGridCellChanged(self, event):
        rowR=event.GetRow()
        colR=event.GetCol()
        newVal=self.Get(rowR, colR)

        # The first row is the column headers
        if rowR == 0:
            event.Veto()  # This is a bit of magic to prevent the event from making later changes to the grid.
            # Note that the Column Colheaders is offset by *2*. (The first column is the row number column and is blank; the second is the weird filename thingie and is untitled.)
            #TODO: Fix this
            if len(self._datasource.ColHeaders)+1 < colR:
                self._datasource.ColHeaders.extend(["" for x in range(colR-len(self._datasource.ColHeaders)-1)])
            self._datasource.ColHeaders[colR-2]=newVal
            self.RefreshWindowFromData()
            return

        # If we're entering data in a new row or a new column, append the necessary number of new rows of columns to lstData
        while rowR > len(self._datasource.Rows):
            self._datasource.Rows.append(self._datasource.Element())

        while colR > len(self._datasource.ColHeaders):
            self._datasource.Rows[rowR-1].append("")

        # Ordinary columns
        if colR > 0:
            self.EvtHandlerEnabled=False
            self._datasource.Rows[rowR-1].SetVal(colR-1, newVal)
            self.ColorCellByValue(rowR-1, colR-1)
            self.AutoSizeColumns()
            #self.DGrid.Grid.ForceRefresh()
            self.EvtHandlerEnabled=True
            return

        # What's left is column zero and thus the user is editing a row number
        # If it's an "X", the row has been deleted.
        if newVal.lower() == "x":
            del self._datasource.Rows[rowR-1]
            event.Veto()                # This is a bit of magic to prevent the event from making later changes to the grid.
            self.RefreshWindowFromData()
            return

        # If it's a number, it is tricky. We need to confirm that the user entered a new number.  (If not, we restore the old one and we're done.)
        # If there is a new number, we re-arrange the rows and then renumber them.
        try:
            newnumf=float(newVal)
        except:
            self.SetCellValueR(rowR, 0, rowR)    # Restore the old value
            return
        newnumf-=0.00001    # When the user supplies an integer, we drop the row *just* before that integer. No overwriting!

        # The indexes the user sees start with 1, but the rows list is 0-based.  Adjust accordingly.
        oldrow=rowR-1

        # We *should* have a fractional value or an integer value out of range. Check for this.
        self.MoveRow(oldrow, newnumf)
        event.Veto()  # This is a bit of magic to prevent the event from making later changed to the grid.
        self.RefreshWindowFromData()
        return

    #------------------
    def OnGridCellDoubleclick(self, event):
        if event.GetRow() == 0 and event.GetCol() == 0:
            self.Grid.AutoSize()
            return
        if event.GetRow() == 0 and event.GetCol() > 0:
            self.Grid.AutoSizeColumn(event.GetCol())

    #------------------
    def OnGridCellRightClick(self, event, m_menuPopup):
        self.rightClickedColumn=event.GetCol()

        # Set everything to disabled.
        for mi in m_menuPopup.GetMenuItems():
            mi.Enable(False)

        # Everything remains disabled when we're outside the defined columns
        if self.rightClickedColumn > len(self._datasource.ColHeaders)+1 or self.rightClickedColumn == 0:
            return

        # We enable the Copy item if have a selection
        sel=self.LocateSelection()
        if sel[0] != 0 or sel[1] != 0 or sel[2] != 0 or sel[3] != 0:
            mi=m_menuPopup.FindItemById(m_menuPopup.FindItem("Copy"))
            mi.Enable(True)

        # We enable the Paste popup menu item if there is something to paste
        mi=m_menuPopup.FindItemById(m_menuPopup.FindItem("Paste"))
        mi.Enabled=self.clipboard is not None and len(self.clipboard) > 0 and len(self.clipboard[0]) > 0  # Enable only if the clipboard contains actual content



    #-------------------
    # Locate the selection, real or implied
    # There are three cases, in descending order of preference:
    #   There is a selection block defined
    #   There is a SelectedCells defined
    #   There is a GridCursor location
    def LocateSelection(self):
        if len(self.Grid.SelectionBlockTopLeft) > 0 and len(self.Grid.SelectionBlockBottomRight) > 0:
            top, left=self.Grid.SelectionBlockTopLeft[0]
            bottom, right=self.Grid.SelectionBlockBottomRight[0]
        elif len(self.Grid.SelectedCells) > 0:
            top, left=self.Grid.SelectedCells[0]
            bottom, right=top, left
        else:
            left=right=self.Grid.GridCursorCol
            top=bottom=self.Grid.GridCursorRow
        return top, left, bottom, right

    def HasSelection(self):
        if len(self.Grid.SelectionBlockTopLeft) > 0 and len(self.Grid.SelectionBlockBottomRight) > 0:
            return True
        if len(self.Grid.SelectedCells) > 0:
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
            self.RefreshWindowFromData()
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