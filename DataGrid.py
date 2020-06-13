from __future__ import annotations
from typing import List, Union

import wx
import wx.grid
import math

from HelpersPackage import IsInt
from FanzineIssueSpecPackage import FanzineDateRange, FanzineDate
#from Log import Log

class Color:
     # Define some RGB color constants
     LabelGray=wx.Colour(230, 230, 230)
     Pink=wx.Colour(255, 230, 230)
     LightGreen=wx.Colour(240, 255, 240)
     LightBlue=wx.Colour(240, 230, 255)
     Blue=wx.Colour(100, 100, 255)
     White=wx.Colour(255, 255, 255)

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

    def GetData(self, iRow: int, iCol: int) -> str:
        pass

    @property
    def Rows(self) -> List:     # Types of list elements needs to be undefined since we don't know what they will be.
        return []
    @Rows.setter
    def Rows(self, rows: List) -> None:
        pass

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str, FanzineDateRange]) -> None:
        pass

    @property
    def Updated(self) -> bool:
        pass
    @Updated.setter
    def Updated(self, val: bool) -> None:
        pass

    @property
    def CanAddColumns(self) -> bool:
        return False            # Override this if adding columns is allowed

    @property
    def CanEditColumnHeaders(self) -> bool:
        return False            # Override this if editing the column headers is allowed



################################################################################
class DataGrid():

    def __init__(self, grid: wx.grid.Grid):         # Grid
        self._grid: wx.grid.Grid=grid

        self._datasource: GridDataSource=GridDataSource()
        self.clipboard=None         # The grid's clipboard
        self.cntlDown=False         # There's no cntl-key currently down


    # Set a value in the source data using logical coordinates
    # Note that we can handle irow== -1 indicating a column header
    def SetSourceValue(self, iRow: int, iCol: int, val) -> None:        # Grid
        assert iCol > -1
        self.ExpandDataSourceToInclude(iRow, iCol)

        if iRow == -1:
            self._datasource.ColHeaders[iCol]=val
            self._datasource.Updated=True
            return

        c=self._datasource.Rows[iRow]
        try:
            c.SetVal(c, iCol, val)
            self._datasource.Updated=True
        except:
            pass


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


    # Get a cell value
    # Note that this does not change the underlying data
    def Get(self, row: int, col: int) -> str:
        return self._grid.GetCellValue(row, col)


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

    @property
    def NumRows(self) -> int:
        return self._grid.NumberRows

    @property
    def Datasource(self) -> GridDataSource:
        return self._datasource
    @Datasource.setter
    def Datasource(self, val: GridDataSource):
        self._datasource=val

    @property
    def Grid(self):        # Grid
        return self._grid

    def AppendRows(self, rows: int) -> None:        # Grid
        assert False

    def AppendEmptyRows(self, nrows: int) -> None:        # Grid
        self._grid.AppendRows(nrows)

    def InsertEmptyRows(self, irow: int, nrows: int) -> None:        # Grid
        self._grid.InsertRows(irow, nrows)
        rows=self._datasource.Rows
        newrows=[]
        if irow > 0:
            newrows=rows[:irow]
        newrows.extend([self._datasource.Element()]*nrows)
        if irow < self._datasource.NumRows-1:
            newrows.extend(rows[irow:])
        self._datasource.Rows=newrows

    def AppendEmptyCols(self, ncols: int) -> None:        # Grid
        self._grid.AppendCols(ncols)

    def SetColHeaders(self, headers: List[str]) -> None:        # Grid
        self._colheaders=headers
        self.Numcols=len(headers)
        if len(headers) == self.Numcols:
            # Add the column headers
            iCol=0
            for colhead in headers:
                self._grid.SetColLabelValue(iCol, colhead)
                iCol+=1

    # --------------------------------------------------------
    def SetColTypes(self, coldatatypes: List[str]) -> None:        # Grid
        self._coldatatypes=coldatatypes

    # --------------------------------------------------------
    def SetColMinWidths(self, defaultwidths: List[int]) -> None:        # Grid
        self._colminwidths=defaultwidths

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

        if col >= len(self._datasource.ColHeaders):
            return

        val=self._grid.GetCellValue(row, col)
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
        elif self._coldatatypes[col] == "url":
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

        self.SetColHeaders(self._colheaders)

        # Fill in the cells
        for i in range(self._datasource.NumRows):
            for j in range(len(self._colheaders)):
                self.SetCellValue(i, j, self._datasource.GetData(i, j))
                #Log("set grid("+str(i)+", "+str(j)+")="+self._datasource.GetData(i, j))

        self.ColorCellsByValue()
        self.AutoSizeColumns()


    #--------------------------------------------------------
    # Move a block of rows within the data source
    # All row numbers are logical
    # Oldrow is the 1st row of the block to be moved
    # Newrow is the target position to which oldrow is moved
    def MoveRows(self, oldrow, numrows, newrow):        # Grid
        if newrow <= 0:
            # The old rows are being moved to the beginning
            newrows=self._datasource.Rows[oldrow:oldrow+numrows]
            newrows.extend(self._datasource.Rows[0:oldrow])
            newrows.extend(self._datasource.Rows[oldrow+numrows:])

        elif newrow >= len(self._datasource.Rows):
            # The old rows are being moved to the end
            newrows=self._datasource.Rows[0:oldrow]
            newrows.extend(self._datasource.Rows[oldrow+numrows:])
            newrows.extend(self._datasource.Rows[oldrow:oldrow+numrows])

        else:
            # The old rows are being moved internally
            if oldrow > newrow:
                # Moving earlier
                newrows=self._datasource.Rows[0:newrow]                         # Unchanged rows before newrow
                newrows.extend(self._datasource.Rows[oldrow:oldrow+numrows])    # The moving block (numrows long)
                newrows.extend(self._datasource.Rows[newrow:oldrow])            # Rows displaced towards the end by the move
                newrows.extend(self._datasource.Rows[oldrow+numrows:])          # Rows after the displaced block's final position which are unaffected
            else:
                # Moving later
                newrows=self._datasource.Rows[0:oldrow]                         # Unchanged rows before oldrow
                newrows.extend(self._datasource.Rows[oldrow+numrows:newrow+numrows])        # Rows after the moving block which are displaced forward
                newrows.extend(self._datasource.Rows[oldrow:oldrow+numrows])    # The moving block (numrows long)
                newrows.extend(self._datasource.Rows[newrow+numrows:])          # Row after the moving block's final position which are unaffected

        self._datasource.Rows=newrows
        self._datasource.Updated=True

        
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
        self._datasource.Updated=True


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
        self._datasource.Updated=True
        self.RefreshGridFromData()

    # Expand the grid's data source so that the local item (irow, icol) exists.
    def ExpandDataSourceToInclude(self, irow: int, icol: int):
        if irow >= 0:   # This test is needed in case we were working on the column headers (irowR->0) and then had to pass in irowR-1
            while irow >= len(self._datasource.Rows):
                self._datasource.Rows.append(self._datasource.Element())
            self._datasource.Updated=True

        # Many data sources do not allow expanding the number of columns, so check that first
        assert icol < len(self._datasource.ColHeaders) or self._datasource.CanAddColumns
        if icol >= 0:   # This test is needed in case we were working on the row headers (icolR->0) and then had to pass in icolR-1
            if self._datasource.CanAddColumns:
                while icol >= len(self._datasource.ColHeaders):
                    self._datasource.ColHeaders.append("")
                    for j in range(self._datasource.NumRows):
                        self._datasource.Rows[j].append("")
                self._datasource.Updated=True


    #------------------
    def OnGridCellChanged(self, event):        # Grid
        self.EvtHandlerEnabled=False
        row=event.GetRow()
        col=event.GetCol()

        # If we're entering data in a new row or a new column, append the necessary number of new rows and/or columns to the data source
        self.ExpandDataSourceToInclude(row, col)

        newVal=self.Get(row, col)
        self._datasource.Rows[row].SetVal(col, newVal)
        self._datasource.Updated=True
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

    def OnGridCellDoubleClick(self):        # Grid
        pass

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