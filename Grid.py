from __future__ import annotations
from typing import List

import wx
import wx.grid
import math

from HelpersPackage import Color, IsInt
from FanzineIssueSpecPackage import FanzineDateRange, FanzineDate

class GridDataSource():

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

        # self._colminwidths: List[int]=[]
        # self._coltypes: List[str]=[]
        # self._colheaders: List[str]=[]

        # The grid is a bit non-standard, since I want to be able to edit row numbers and column headers
        # The row and column labels are actually the (editable) 1st column and 1st row of the spreadsheet (they're colored gray)
        # and the "real" row and column labels are hidden.
        self._grid.HideRowLabels()
        self._grid.HideColLabels()


    # Set a cell value using raw row and column numbers (raw includes the row and column headers as index 0)
    def RawSet(self, rowR: int, colR: int, val: str) -> None:
        if rowR >= self.NumrowsR:
            self.AppendEmptyRows(self.NumrowsR-rowR+1)
        if colR >= self.NumcolsR:
            self.AppendEmptyCols((self.NumcolsR-colR+1))
        self._grid.SetCellValue(rowR, colR, val)

    # Set a cell value using logical row and column indexes (i.e., data indexing starts at 0)
    def Set(self, row: int, col: int, val: str) -> None:
        if val is None:
            self.RawSet(row+1, col+1, "")
        else:
            self.RawSet(row+1, col+1, val)

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
            iRowR=1
            for colhead in headers:
                self.RawSet(0, iRowR, colhead)  # Set the column header number
                self.Grid.SetCellBackgroundColour(0, iRowR, Color.LabelGray)  # Set the column header background
                iRowR+=1
            self.Grid.SetCellBackgroundColour(0, 0, Color.LabelGray)


    def SetColTypes(self, coltypes: List[str]) -> None:
        self._coltypes=coltypes

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
            self.RawSet(iRowR, 0, str(iRowR))
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
        if self._coltypes[col] == "int":
            if val is not None and val != "" and not IsInt(val):
                self.SetCellBackgroundColor(row, col, Color.Pink)
        elif self._coltypes[col] == "date range":
            if val is not None and val != "" and FanzineDateRange().Match(val).IsEmpty():
                self.SetCellBackgroundColor(row, col, Color.Pink)
        elif self._coltypes[col] == "date":
            if val is not None and val != "" and FanzineDate().Match(val).IsEmpty():
                self.SetCellBackgroundColor(row, col, Color.Pink)

    def ColorCellsByValue(self):
        if len(self._coltypes) != self._grid.NumberCols-1:  # -1 to ignore row number column
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
                self.Set(i, j, self._datasource.Data(i, j))

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
