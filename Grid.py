from __future__ import annotations
from typing import List

import wx
import wx.grid

from HelpersPackage import Color

# The class hides the machinations needed to handle the row and column headers
class Grid():

    def __init__(self, grid: wx.grid.Grid):
        self._grid: wx.grid.Grid=grid

    # Set using raw row and column numbers (raw includes the row and column headers as index 0)
    def RawSet(self, row: int, col: int, val: str) -> None:
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
        assert (False)

    def AppendEmptyRows(self, nrows: int) -> None:
        self._grid.AppendRows(nrows)

    def AppendEmptyCols(self, ncols: int) -> None:
        self._grid.AppendCols(ncols)

    def SetColHeaders(self, headers: List[str]) -> None:
        # Color all the column headers white before coloring the ones that actually exist gray.  (This handles cases where a column has been deleted.)
        for i in range(0, self.Numcols-1):
            self.Grid.SetCellBackgroundColour(0, i, Color.White)

        # Add the column headers
        self.Grid.SetCellValue(0, 0, "")
        i=1
        for colhead in headers:
            self.RawSet(0, i, colhead)  # Set the column header number
            self.Grid.SetCellBackgroundColour(0, i, Color.LabelGray)  # Set the column header background
            i+=1
        self.Grid.SetCellBackgroundColour(0, 0, Color.LabelGray)
        self.Grid.SetCellBackgroundColour(0, 1, Color.LabelGray)

    def SetRowNumbers(self, num: int) -> None:
        # Make the first grid column contain editable row numbers
        for i in range(1, self.Numrows):  # The 0,0 cell is left blank
            self.RawSet(i, 0, str(i))
            self.Grid.SetCellBackgroundColour(i, 0, Color.LabelGray)
        self.Grid.SetCellBackgroundColour(0, 0, Color.LabelGray)

    def SetCellBackgroundColor(self, row, col, color):
        self.Grid.SetCellBackgroundColour(row+1, col+1, color)

