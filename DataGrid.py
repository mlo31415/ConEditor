from __future__ import annotations
from typing import List, Union, Tuple, Optional

import wx
import wx.grid
import math

from HelpersPackage import IsInt
from FanzineIssueSpecPackage import FanzineDateRange, FanzineDate
from Log import Log

class Color:
     # Define some RGB color constants
     LabelGray=wx.Colour(230, 230, 230)
     Pink=wx.Colour(255, 230, 230)
     LightGreen=wx.Colour(240, 255, 240)
     LightBlue=wx.Colour(240, 230, 255)
     Blue=wx.Colour(100, 100, 255)
     LightGray=wx.Colour(242, 242, 242)
     White=wx.Colour(255, 255, 255)

# An abstract class which defines the structure of a data source for the Grid class
class GridDataSource():

    def __init__(self):
        self._allowCellEdits: List[Tuple[int, int]]=[]     # A list of cells where editing has been permitted by overriding a "maybe" for the col

    def Signature(self) -> int:
        return hash(self)

    @property
    def Element(self):
        return self._element

    @property
    def ColHeaders(self) -> List[str]:
        assert False
        return []

    @property
    def ColDataTypes(self) -> List[str]:
        assert False
        return []

    @property
    def ColMinWidths(self) -> List[int]:
        assert False
        return []

    @property
    def ColEditable(self) -> List[int]:
        assert False
        return []

    @property
    def AllowCellEdits(self) -> List[Tuple[int, int]]:
        return self._allowCellEdits
    @AllowCellEdits.setter
    def AllowCellEdits(self, val: List[Tuple[int, int]]) -> None:
        self._allowCellEdits=val

    @property
    def NumCols(self) -> int:
        return len(self.ColHeaders)

    @property
    def NumRows(self) -> int:
        assert False
        return -1

    def GetData(self, iRow: int, iCol: int) -> str:
        assert False
        pass

    @property
    def Rows(self) -> List:     # Types of list elements needs to be undefined since we don't know what they will be.
        return []
    @Rows.setter
    def Rows(self, rows: List) -> None:
        assert False
        pass

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str, FanzineDateRange]) -> None:
        assert False
        pass

    @property
    def CanAddColumns(self) -> bool:
        return False            # Override this if adding columns is allowed

    @property
    def CanEditColumnHeaders(self) -> bool:
        return False            # Override this if editing the column headers is allowed

    @property
    def IsText(self, row: int) -> bool:
        return False            # Override only if needed

    @property
    def SpecialTextColor(self) -> Optional[Color]:
        return None
    @SpecialTextColor.setter
    def SpecialTextColor(self, val: Optional[Color]) -> None:
        return

    # Make text lines to be merged and editable
    def MakeTextLinesEditable(self) -> None:
        for irow, row in enumerate(self.Rows):
            if row.IsText:
                for icol in range(self.NumCols):
                    if self.ColEditable[icol] == "maybe":
                        self.AllowCellEdits.append((irow, icol))


    def Signature(self) -> int:
        sum=0
        for row in self.Rows:
            sum+=row.Signature()
        return sum


################################################################################
class DataGrid():

    def __init__(self, grid: wx.grid.Grid):         # Grid
        self._grid: wx.grid.Grid=grid

        self._datasource: GridDataSource=GridDataSource()
        self.clipboard=None         # The grid's clipboard
        self.cntlDown=False         # There's no cntl-key currently down


    # Set a grid cell value
    # Note that this does not change the underlying source data
    def SetCellValue(self, iRow: int, iCol: int, val) -> None:        # Grid
        # Extend the grid if needed
        nrows=self._grid.GetNumberRows()
        if iRow >= nrows:
            self._grid.AppendRows(iRow-nrows+1)
        ncols=self._grid.GetNumberCols()
        if iCol >= ncols:
            self._grid.AppendCols(iCol-ncols+1)

        # None values are replaced by empty strings
        if val is None:
            val=""
        if type(val) is not str:
            val=str(val)

        self._grid.SetCellValue(iRow, iCol, val)

    # --------------------------------------------------------
    # Get a cell value
    # Note that this does not change the underlying data
    def Get(self, row: int, col: int) -> str:
        return self._grid.GetCellValue(row, col)


    # --------------------------------------------------------
    @property
    # Get the number of columns
    def Numcols(self) -> int:
        return self._grid.NumberCols
    @Numcols.setter
    # Get or set the number of columns
    def Numcols(self, nCols: int) -> None:
        if self._grid.NumberCols == nCols:
            return
        if self._grid.NumberCols > nCols:
            self._grid.DeleteCols(nCols, self._grid.NumberCols-nCols)
        else:
            self._grid.AppendCols(nCols, self._grid.NumberCols-nCols)

    # --------------------------------------------------------
    @property
    def NumRows(self) -> int:
        return self._grid.NumberRows

    # --------------------------------------------------------
    @property
    def Datasource(self) -> GridDataSource:
        return self._datasource
    @Datasource.setter
    def Datasource(self, val: GridDataSource):
        self._datasource=val

    # --------------------------------------------------------
    @property
    def Grid(self):        # Grid
        return self._grid

    # --------------------------------------------------------
    def AppendRows(self, rows: int) -> None:        # Grid
        assert False

    # --------------------------------------------------------
    def AppendEmptyRows(self, nrows: int) -> None:        # Grid
        self._grid.AppendRows(nrows)

    # --------------------------------------------------------
    # Insert one or more empty rows in the data source.
    # irow and everything after it will be shifted later to make room for the new rows
    # Expand the grid, also, but don't bother to repopulate it as a later RefreshWindow will take care of that
    def InsertEmptyRows(self, irow: int, nrows: int) -> None:        # Grid
        self._grid.InsertRows(irow, nrows)  # Expand the grid
        # Append nrows at the end, them move the displaced rows to later
        oldnumrows=self._datasource.NumRows
        self._datasource.Rows.extend([self._datasource.Element() for _ in range(nrows)])
        self.MoveRows(irow, oldnumrows-irow, irow+nrows)

        # Now update the editable status of non-editable columns
        # All row numbers >= irow are incremented by nrows
        for i, (row, col) in enumerate(self._datasource.AllowCellEdits):
            if row >= irow:
                self._datasource.AllowCellEdits[i]=(row+nrows, col)


    # --------------------------------------------------------
    def AppendEmptyCols(self, ncols: int) -> None:        # Grid
        self._grid.AppendCols(ncols)

    # --------------------------------------------------------
    def SetColHeaders(self, headers: List[str]) -> None:        # Grid
        self.Numcols=len(headers)
        if len(headers) == self.Numcols:
            # Add the column headers
            iCol=0
            for colhead in headers:
                self._grid.SetColLabelValue(iCol, colhead)
                iCol+=1

    # --------------------------------------------------------
    def AutoSizeColumns(self):        # Grid
        self._grid.AutoSizeColumns()
        if len(self._datasource.ColMinWidths) == self._grid.NumberCols-1:
            iCol=0
            for width in self._datasource.ColMinWidths:
                w=self._grid.GetColSize(iCol)
                if w < width:
                    self._grid.SetColSize(iCol, width)
                iCol+=1

    # --------------------------------------------------------
    def SetCellBackgroundColor(self, row, col, color):        # Grid
        self._grid.SetCellBackgroundColour(row, col, color)

    # --------------------------------------------------------
    # Row, col are Grid coordinates
    def ColorCellByValue(self, row: int, col: int) -> None:        # Grid
        # Start by setting color to white
        self.SetCellBackgroundColor(row, col, Color.White)

        # Deal with col overflow
        if col >= len(self._datasource.ColHeaders):
            return

        # Row overflow is permitted and extra rows (rows in the grid, but not in the datasource) are colored generically
        if row >= self.Datasource.NumRows:
            # These are trailing rows and should get default formatting
            self._grid.SetCellSize(row, col, 1, 1)  # Eliminate any spans
            self._grid.SetCellFont(row, col, self._grid.GetCellFont(row, col).GetBaseFont())
            if self._datasource.ColEditable[col] == "no" or self._datasource.ColEditable[col] == "maybe":
                self.SetCellBackgroundColor(row, col, Color.LightGray)
            return

        val=self._grid.GetCellValue(row, col)

        # If the row is a text row and if there's a special text color, color it thus
        self._grid.SetCellFont(row, col, self._grid.GetCellFont(row, col).GetBaseFont())    # First turn off any special formatting
        if row < self._datasource.NumRows and self._datasource.Rows[row].IsText and self._datasource.SpecialTextColor is not None:
            if self._datasource.SpecialTextColor is not None:
                if type(self._datasource.SpecialTextColor) is Color:
                    self.SetCellBackgroundColor(row, col, self._datasource.SpecialTextColor)
                else:
                    self._grid.SetCellFont(row, col, self._grid.GetCellFont(row, col).Bold())

        # If the column is not editable, color it light gray regardless of its value
        elif self._datasource.ColEditable[col] == "no":
            self.SetCellBackgroundColor(row, col, Color.LightGray)
        elif self._datasource.ColEditable[col] == "maybe" and (row, col) not in self._datasource.AllowCellEdits:
            self.SetCellBackgroundColor(row, col, Color.LightGray)

        else:
            # If it *is* editable or potentially editable, then color it according to its value
            # We skip testing for "str"-type columns since anything at all is OK in a str column
            if self._datasource.ColDataTypes[col] == "int":
                if val is not None and val != "" and not IsInt(val):
                    self.SetCellBackgroundColor(row, col, Color.Pink)
            elif self._datasource.ColDataTypes[col] == "date range":
                if val is not None and val != "" and FanzineDateRange().Match(val).IsEmpty():
                    self.SetCellBackgroundColor(row, col, Color.Pink)
            elif self._datasource.ColDataTypes[col] == "date":
                if val is not None and val != "" and FanzineDate().Match(val).IsEmpty():
                    self.SetCellBackgroundColor(row, col, Color.Pink)

        # Special handling for URLs: we add an underline
        if self._datasource.ColDataTypes[col] == "url":
            if val is not None and val != "" and len(self._datasource.Rows[row].URL) > 0:
                self._grid.SetCellTextColour(row, col, Color.Blue)
                font=self._grid.GetCellFont(row, col)
                font.MakeUnderlined()
                self._grid.SetCellFont(row, col, font)

    # --------------------------------------------------------
    def ColorCellsByValue(self):        # Grid
        # Analyze the data and highlight cells where the data type doesn't match the header.  (E.g., Volume='August', Month='17', year='20')
        # Col 0 is a number and 3 is a date and the rest are strings.   We walk the rows checking the type of data in that column.
        for iRow in range(self._grid.NumberRows):
            for iCol in range(self._grid.NumberCols):
                self.ColorCellByValue(iRow, iCol)

    # --------------------------------------------------------
    def RefreshGridFromData(self):        # Grid
        self.EvtHandlerEnabled=False
        self._grid.ClearGrid()
        # if self._grid.NumberRows > self._datasource.NumRows:
        #     # This is to get rid of any trailling formatted rows
        #     self._grid.DeleteRows(self._datasource.NumRows, self._grid.NumberRows-self._datasource.NumRows)
        #     self._grid.AppendRows(self._grid.NumberRows-self._datasource.NumRows)
        #     #TODO: Need to decide if we're going to leave any empty rows

        self.SetColHeaders(self._datasource.ColHeaders)

        # Fill in the cells
        for i in range(self._datasource.NumRows):
            if self._datasource.Rows[i].IsText:
                self._grid.SetCellSize(i, 0, 1, self.Numcols)   # Make text rows all one cell
            else:
                self._grid.SetCellSize(i, 0, 1, 1)  # Set as normal unspanned cell

            for j in range(len(self._datasource.ColHeaders)):
                self.SetCellValue(i, j, self._datasource.GetData(i, j))

        self.ColorCellsByValue()
        self.AutoSizeColumns()


    #--------------------------------------------------------
    # Move a block of rows within the data source
    # All row numbers are logical
    # Oldrow is the 1st row of the block to be moved
    # Newrow is the target position to which oldrow is moved

    def MoveRows(self, oldrow, numrows, newrow):        # Grid
        rows=self._datasource.Rows

        dest=newrow
        start=oldrow
        end=oldrow+numrows-1
        if newrow < oldrow:
            # Move earlier
            b1=rows[0:dest]
            i1=list(range(0, dest))
            b2=rows[dest:start]
            i2=list(range(dest, start))
            b3=rows[start:end+1]
            i3=list(range(start, end+1))
            b4=rows[end+1:]
            i4=list(range(end+1, len(rows)))
        else:
            # Move later
            b1=rows[0:start]
            i1=list(range(0, start))
            b2=rows[start:end+1]
            i2=list(range(start, end+1))
            b3=rows[end+1:end+1+dest-start]
            i3=list(range(end+1, end+1+dest-start))
            b4=rows[end+1+dest-start:]
            i4=list(range(end+1+dest-start, len(rows)))

        rows=b1+b3+b2+b4
        self._datasource.Rows=rows

        tpermuter=i1+i3+i2+i4
        permuter=[None]*len(tpermuter)     # This next bit of code inverts the permuter. (There ought to be a more elegant way to generate it!)
        for i, r in enumerate(tpermuter):
            permuter[r]=i

        # Now use the permuter to update the row numbers of the cells which are allowed to be edited
        for i, (row, col) in enumerate(self._datasource.AllowCellEdits):
            self._datasource.AllowCellEdits[i]=(permuter[row], col)


    #------------------
    def MoveRow(self, oldrow, newnumf):        # Grid
        newrow=math.ceil(newnumf)-1
        self.MoveRows(oldrow, 1, newrow)


    # ------------------
    def CopyCells(self, top, left, bottom, right):        # Grid
        self.clipboard=[]
        for iRow in range(top, bottom+1):
            v=[]
            for jCol in range(left, right+1):
                v.append(self._datasource.GetData(iRow, jCol))
            self.clipboard.append(v)


    # ------------------
    def PasteCells(self, top, left):        # Grid
        # We paste the clipboard data into the block of the same size with the upper-left at the mouse's position
        # Might some of the new material be outside the current bounds?  If so, add some blank rows and/or columns

        # Define the bounds of the paste-to box
        pasteTop=top
        pasteBottom=top+len(self.clipboard)
        pasteLeft=left
        pasteRight=left+len(self.clipboard[0])

        # Does the paste-to box extend beyond the end of the available rows?  If so, extend the available rows.
        num=pasteBottom-len(self._datasource.Rows)+1
        if num > 0:
            for i in range(num):
                self._datasource.Rows.append(self._datasource.Element())
        # Copy the cells from the clipboard to the grid in lstData.
        for i, row in enumerate(self.clipboard, start=pasteTop):
            for j, cellval in enumerate(row, start=pasteLeft):
                self._datasource.SetDataVal(i, j, cellval)
        self.RefreshGridFromData()

    # --------------------------------------------------------
    # Expand the grid's data source so that the local item (irow, icol) exists.
    def ExpandDataSourceToInclude(self, irow: int, icol: int):
        assert irow >= 0 and icol >= 0
        while irow >= len(self._datasource.Rows):
            self._datasource.Rows.append(self._datasource.Element())

        # Many data sources do not allow expanding the number of columns, so check that first
        assert icol < len(self._datasource.ColHeaders) or self._datasource.CanAddColumns
        if self._datasource.CanAddColumns:
            while icol >= len(self._datasource.ColHeaders):
                self._datasource.ColHeaders.append("")
                for j in range(self._datasource.NumRows):
                    self._datasource.Rows[j].append("")


    #------------------
    def OnGridCellChanged(self, event):        # Grid
        self.EvtHandlerEnabled=False
        row=event.GetRow()
        col=event.GetCol()

        # If we're entering data in a new row or a new column, append the necessary number of new rows and/or columns to the data source
        self.ExpandDataSourceToInclude(row, col)

        newVal=self.Get(row, col)
        self._datasource.SetDataVal(row, col, newVal)
        #Log("set datasource("+str(row)+", "+str(col)+")="+newVal)
        self.ColorCellByValue(row, col)
        self.AutoSizeColumns()
        self.RefreshGridFromData()
        self.EvtHandlerEnabled=True

        return

    #------------------
    def OnGridCellRightClick(self, event, m_menuPopup):        # Grid
        self.rightClickedColumn=event.GetCol()
        self.rightClickedRow=event.GetRow()

        # Set everything to disabled.
        for mi in m_menuPopup.GetMenuItems():
            mi.Enable(False)

        # Everything remains disabled when we're outside the defined columns
        if self.rightClickedColumn > len(self._datasource.ColHeaders)+1:
            return

        # We enable the Copy item if have a selection
        if self.HasSelection():
            mi=m_menuPopup.FindItemById(m_menuPopup.FindItem("Copy"))
            mi.Enable(True)

        # We enable the Paste popup menu item if there is something to paste
        mi=m_menuPopup.FindItemById(m_menuPopup.FindItem("Paste"))
        mi.Enabled=self.clipboard is not None and len(self.clipboard) > 0 and len(self.clipboard[0]) > 0  # Enable only if the clipboard contains actual content

    #-------------------
    def OnGridCellDoubleClick(self):        # Grid
        pass

    #-------------------
    def OnGridLabelRightClick(self, event):        # Grid
        # This might be a good place to pop up a dialog to change a column header
        pass

    #-------------------
    # Locate the selection, real or implied
    # There are three cases, in descending order of preference:
    #   There is a selection block defined
    #   There is a SelectedCells defined
    #   There is a GridCursor location
    def LocateSelection(self):        # Grid
        if len(self._grid.SelectionBlockTopLeft) > 0 and len(self._grid.SelectionBlockBottomRight) > 0:
            top, left=self._grid.SelectionBlockTopLeft[0]
            bottom, right=self._grid.SelectionBlockBottomRight[0]
        elif len(self._grid.SelectedCells) > 0:
            top, left=self._grid.SelectedCells[0]
            bottom, right=top, left
        else:
            left=right=self._grid.GridCursorCol
            top=bottom=self._grid.GridCursorRow
        return top, left, bottom, right

    def HasSelection(self):        # Grid
        if len(self._grid.SelectionBlockTopLeft) > 0 and len(self._grid.SelectionBlockBottomRight) > 0:
            return True
        if len(self._grid.SelectedCells) > 0:
            return True
        return False

    #-------------------
    def OnKeyDown(self, event):        # Grid
        top, left, bottom, right=self.LocateSelection()

        if event.KeyCode == 67 and self.cntlDown:   # cntl-C
            self.CopyCells(top, left, bottom, right)
        elif event.KeyCode == 86 and self.cntlDown and self.clipboard is not None and len(self.clipboard) > 0: # cntl-V
            self.PasteCells(top, left)
        elif event.KeyCode == 308:                  # cntl
            self.cntlDown=True
        elif event.KeyCode == 68:                   # Kludge to be able to force a refresh (press "d")
            self.RefreshGridFromData()
        elif event.KeyCode == 315 and self.HasSelection():      # Up arrow
            tl=self._grid.SelectionBlockTopLeft
            br=self._grid.SelectionBlockBottomRight
            # Only if there's a single selected block
            if len(tl) == 1 and len(br) == 1:
                top, left=tl[0]
                bottom, right=br[0]
                if top > 0: # Can't move up if the first row selected is row 0
                    # Extend the selection to be the whole row(s)
                    left=0
                    right=self.Numcols-1
                    # And move 'em up 1
                    self.MoveRows(top, bottom-top+1, top-1)
                    # And re-establish the selection
                    top-=1
                    bottom-=1
                    self._grid.SelectBlock(top, left, bottom, right)
                    self.RefreshGridFromData()
        elif event.KeyCode == 317 and self.HasSelection():      # Down arrow
            tl=self._grid.SelectionBlockTopLeft
            br=self._grid.SelectionBlockBottomRight
            # Only if there's exactly one selected block
            if len(tl) == 1 and len(br) == 1:
                top, _=tl[0]
                bottom, right=br[0]
                self.ExpandDataSourceToInclude(bottom+1, right)
                if bottom < self._grid.NumberRows:
                    # Extend the selection to be the whole row(s)
                    right=self.Numcols-1
                    # And move 'em down 1
                    self.MoveRows(top, bottom-top+1, top+1)
                    # And re-establish the selection
                    top+=1
                    bottom+=1
                    self._grid.SelectBlock(top, left, bottom, right)
                    self.RefreshGridFromData()
        else:
            event.Skip()

    #-------------------
    def OnKeyUp(self, event):        # Grid
        if event.KeyCode == 308:                    # cntl
            self.cntlDown=False
        event.Skip()

    #------------------
    def OnPopupCopy(self, event):        # Grid
        # We need to copy the selected cells into the clipboard object.
        # (We can't simply store the coordinates because the user might edit the cells before pasting.)
        top, left, bottom, right=self.LocateSelection()
        self.CopyCells(top, left, bottom, right)
        event.Skip()

    #------------------
    def OnPopupPaste(self, event):        # Grid
        top, left, _, _=self.LocateSelection()
        self.PasteCells(top, left)
        event.Skip()

    # ------------------
    def HideRowLabels(self) -> None:
        self._grid.HideRowLabels()