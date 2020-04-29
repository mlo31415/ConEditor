from __future__ import annotations
from typing import Union, Tuple, Optional, List

import os
import wx
import wx.grid
import math
import sys
import re
from GUIClass import MainFrame

from HelpersPackage import Bailout, CanonicizeColumnHeaders
from Log import LogOpen

from ConSeries import ConSeries, Con

def ValidateData(a, b):
    return True


class Grid():

    def __init__(self, grid):
        self._grid=grid

    def Refresh(self, cs: ConSeries):
        pass

    def Set(self, col: int, row: int, val: str) -> None:
        self._grid.SetCellValue(row, col, val)

    def Get(self, row: int, col: int) -> str:
        return ""

    @property
    def Numcols(self) -> int:
        return self._grid.NumberCols

    @property
    def Numrows(self) -> int:
        return self._grid.NumberRows
    
    @property
    def Grid(self):
        return self._grid



class MainWindow(MainFrame):
    def __init__(self, parent, title):
        MainFrame.__init__(self, parent)

        self.highlightRows=[]       # A List of the names of fanzines in highlighted rows
        self.clipboard=None         # The grid's clipboard
        self.userSelection=None
        self.cntlDown: bool=False
        self.rightClickedColumn: Optional[int]=None
        self.conSeriesData: ConSeries=ConSeries()

        self.dirname: str=''
        if len(sys.argv) > 1:
            self.dirname=os.getcwd()

        self._grid: wx.grid.Grid=Grid(self.gRowGrid)

        # Read the LST file
        self.LoadLSTFile()

        self.Show(True)

    @property
    def DGrid(self) -> Grid:
        return self._grid

    #------------------
    # Given a LST file of disk load it into self
    def LoadLSTFile(self):

        # Clear out any old information
        self.conSeriesData=ConSeries()
        self.tTopMatter.SetValue("")
        self.tPText.SetValue("")
        for i in range(0, self.DGrid.Numcols):
            for j in range(0, self.DGrid.Numrows):
                self.DGrid.Set(i, j, "")

        # Call the File Open dialog to get an LST file
        dlg=wx.FileDialog(self, "Select LST file to load", self.dirname, "", "*.LST", wx.FD_OPEN)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        self.lstFilename=dlg.GetFilename()
        self.dirname=dlg.GetDirectory()
        dlg.Destroy()

        # Read the lst file
        pathname=os.path.join(self.dirname, self.lstFilename)
        try:
            self.conSeriesData.Read(pathname)
        except Exception as e:
            Bailout(e, "MainWindow: Failure reading LST file '"+pathname+"'", "LSTError")

        # Fill in the upper stuff
        self.tTopMatter.SetValue(self.conSeriesData.FirstLine)
        if len(self.conSeriesData.TopTextLines) > 0:
            self.tPText.SetValue("\n".join(self.conSeriesData.TopTextLines))
        elif len(self.conSeriesData.BottomTextLines) > 0:
            self.tPText.SetValue("\n".join(self.conSeriesData.BottomTextLines))

        # The grid is a bit non-standard, since I want to be able to edit row numbers and column headers
        # The row and column labels are actually the (editable) 1st column and 1st row of the spreadsheet (they're colored gray)
        # and the "real" row and column labels are hidden.
        self.DGrid.HideRowLabels()
        self.DGrid.HideColLabels()

        # And now determine the identities of the column headers. (There are many ways to label a column that amount to the same thing.)
        self.conSeriesData.IdentifyColumnHeaders()

        # Insert the row data into the grid
        self.RefreshGridFromLSTData()


    #------------------
    def OnLoadNewLSTFile(self, event):
        self.LoadLSTFile()
        pass

    # Define some RGB color constants
    labelGray=wx.Colour(230, 230, 230)
    pink=wx.Colour(255, 230, 230)
    lightGreen=wx.Colour(240, 255, 240)
    lightBlue=wx.Colour(240, 230, 255)
    white=wx.Colour(255, 255, 255)

    #------------------
    # The LSTFile object has the official information. This function refreshes the display from it.
    def RefreshGridFromLSTData(self):
        self.DGrid.EvtHandlerEnabled=False
        self.DGrid.ClearGrid()

        # In effect, this makes all row and col references to data (as opposed to the labels) to be 1-based

        # Color all the column headers white before coloring the ones that actually exist gray.  (This handles cases where a column has been deleted.)
        for i in range(0, self.DGrid.NumberCols-1):
            self.DGrid.SetCellBackgroundColour(0, i, self.white)

        # Add the column headers
        self.DGrid.SetCellValue(0, 0, "")
        self.DGrid.SetCellValue(0, 1, "First Page")
        i=2
        for colhead in self.conSeriesData.Colheaders:
            self.DGrid.SetCellValue(0, i, colhead)               # Set the column header number
            self.DGrid.SetCellBackgroundColour(0, i, self.labelGray)  # Set the column header background
            i+=1
        self.DGrid.SetCellBackgroundColour(0, 0, self.labelGray)
        self.DGrid.SetCellBackgroundColour(0, 1, self.labelGray)

        # Make the first grid column contain editable row numbers
        for i in range(1, grid.GetNumberRows()):
            self.DGrid.SetCellValue(i, 0, str(i))
            self.DGrid.SetCellBackgroundColour(i, 0, self.labelGray)
        self.DGrid.SetCellBackgroundColour(0, 0, self.labelGray)

        # Now insert the row data
        self.DGrid.AppendRows(len(self.conSeriesData.Rows))
        i=1
        for row in self.conSeriesData.Rows:
            j=1
            for cell in row:
                self.DGrid.SetCellValue(i, j, cell)
                j+=1
            i+=1

        self.ColorCellByValue()
        self.DGrid.ForceRefresh()
        self.DGrid.AutoSizeColumns()
        self.DGrid.EvtHandlerEnabled=True


    def ColorCellByValue(self):
        # Analyze the data and highlight cells where the data type doesn't match the header.  (E.g., Volume='August', Month='17', year='20')
        # We walk the columns.  For each column we decide on the proper type. Then we ewalk the rows checking the type of data in that column.
        for iCol in range(0, len(self.conSeriesData.Colheaders)+1):        # Because of that damned doubled 1st column...
            colhead=self.conSeriesData.Colheaders[iCol-1]      # Because of that damned doubled 1st column...
            coltype=CanonicizeColumnHeaders(colhead)
            for iRow in range(0, len(self.conSeriesData.Rows)):
                row=self.conSeriesData.Rows[iRow]
                if iCol >= len(row):
                    continue
                cell=row[iCol]
                color=self.white
                if len(cell) > 0 and not ValidateData(cell, coltype):
                    color=self.pink
                self.DGrid.SetCellBackgroundColour(iRow+1, iCol+1, color)

    #------------------
    # Save an LSTFile object to disk.
    def OnSaveLSTFile(self, event):
        # Rename the old file
        oldname=os.path.join(self.dirname, self.lstFilename)
        newname=os.path.join(self.dirname, os.path.splitext(self.lstFilename)[0]+"-old.LST")
        try:
            i=0
            while os.path.exists(newname):
                i+=1
                newname=os.path.join(self.dirname, os.path.splitext(self.lstFilename)[0]+"-old-"+str(i)+".LST")

            os.rename(oldname, newname)
        except:
            Bailout(PermissionError, "OnSaveLSTFile fails when trying to rename "+oldname+" to "+newname, "LSTError")

        try:
            self.conSeriesData.Save(oldname)
        except:
            Bailout(PermissionError, "OnSaveLSTFile fails when trying to write file "+newname, "LSTError")


    #------------------
    # We load a bunch of files, including one or more.issue files.
    # The .issue files tell us what image files we have present.
    # Add one row for each .issue file
    def OnLoadNewIssues(self, event):
        # Call the File Open dialog to get the .issue files
        self.dirname=''
        dlg=wx.FileDialog(self, "Select .issue files to load", self.dirname, "", "*.issue", wx.FD_OPEN|wx.FD_MULTIPLE)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        files=dlg.GetFilenames()
        dlg.Destroy()
        for file in files:
            # Decode the file name to get the row info.
            # The filename consists of:
            #       A first section (ending in $$) which is the prefix of the associated image files
            #       A number of space-delimited segments consisting of a capital letter followed by data
            row=self.DecodeIssueFileName(file)
            bestColTypes=self.conSeriesData.GetInsertCol(row)
            fIndex=self.conSeriesData.GetBestRowIndex(bestColTypes, row)  # "findex" to remind me this is probably a floating point number to indicate an insertion between two rows
            self.conSeriesData.Rows.append(row)
            self.MoveRow(len(self.conSeriesData.Rows)-1, fIndex)
            self.highlightRows.append(row[0][1:])   # Add this row's fanzine name to the list of newly-added rows.

        self.RefreshGridFromLSTData()
        pass


    #------------------
    def DecodeIssueFileName(self, filename: str):
        if filename is None or len(filename) == 0:
            return None

        # Start by dividing on the "$$"
        sections=filename.split("$$")
        if len(sections) != 2:
            Bailout(ValueError, "ConEditor.DecodeIssueFileName: Missing $$ in '"+filename+"'", "LSTError")
        namePrefix=sections[0].strip()

        # Now remove the extension and divide the balance of the name by spaces
        balance=os.path.splitext(sections[1])[0]    # Get the filename and then drop the extension
        rest=[r for r in balance.split(" ") if len(r) > 0]

        # We have the table of column headers types in lstData.ColumnHeaderTypes
        # Match them up and create the new row with the right stuff in each column.
        row=[""]*len(self.conSeriesData.Colheaders)    # Create an empty list of the correct size
        for val in rest:
            if len(val) > 1:
                valtype=val[0]
                val=val[1:]     # The value is the part after the initial character (which is the val type)
                if not valtype.isupper():
                    continue
                try:
                    index=self.conSeriesData.ColumnHeaderTypes.index(valtype)
                    row[index]=val
                except:
                    pass    # Just ignore the error and the column
        row[0]=namePrefix
        return row


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
            self.DGrid.AutoSize()
            return
        if event.GetRow() == 0 and event.GetCol() > 0:
            self.DGrid.AutoSizeColumn(event.GetCol())

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

        # We only enable Extract Scanner when we're in the Notes column and there's something to extract.
        mi=self.m_menuPopup.FindItemById(self.m_menuPopup.FindItem("Extract Scanner"))
        if self.rightClickedColumn < len(self.conSeriesData.Colheaders)+2:
            if self.conSeriesData.Colheaders[self.rightClickedColumn-2] == "Notes":
                # We only want to enable the Notes column if it contains scanned by information
                for row in self.conSeriesData.Rows:
                    if len(row) > self.rightClickedColumn-1:
                        note=row[self.rightClickedColumn-1].lower()
                        if "scan by" in note or \
                                "scans by" in note or \
                                "scanned by" in note or \
                                "scanning by" in note or \
                                "scanned at" in note:
                            mi.Enable(True)

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
        if len(self.DGrid.SelectionBlockTopLeft) > 0 and len(self.DGrid.SelectionBlockBottomRight) > 0:
            top, left=self.DGrid.SelectionBlockTopLeft[0]
            bottom, right=self.DGrid.SelectionBlockBottomRight[0]
        elif len(self.DGrid.SelectedCells) > 0:
            top, left=self.DGrid.SelectedCells[0]
            bottom, right=top, left
        else:
            left=right=self.DGrid.GridCursorCol
            top=bottom=self.DGrid.GridCursorRow
        return top, left, bottom, right

    def HasSelection(self):
        if len(self.DGrid.SelectionBlockTopLeft) > 0 and len(self.DGrid.SelectionBlockBottomRight) > 0:
            return True
        if len(self.DGrid.SelectedCells) > 0:
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
            self.RefreshGridFromLSTData()
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
                self.conSeriesData.Rows.append(["" for x in range(len(self.conSeriesData.Rows[0]))])  # The strange contortion is to append a list of distinct empty strings

        # Does the paste-to box extend beyond the right side of the availables? If so, extend the rows with more columns.
        num=pasteRight-len(self.conSeriesData.Rows[0])-1
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
        self.RefreshGridFromLSTData()

    #------------------
    def DeleteColumn(self, col):
        # Some columns are sacrosanct
        # Column 0 is the row number and col 1 is the "first page" (computerd) column
        # We must subtract 2 from col because the real data only starts at the third column.
        col=col-2
        if col >= len(self.conSeriesData.Rows[0]) or col < 0:
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
        self.RefreshGridFromLSTData()

    # ------------------
    def AddColumnToLeft(self, col):
        col=col-2
        self.conSeriesData.ColHeaders=self.conSeriesData.ColHeaders[:col]+[""]+self.conSeriesData.ColHeaders[col:]
        for i in range(0, len(self.conSeriesData.Rows)):
            row=self.conSeriesData.Rows[i]
            row=row[:col+1]+[""]+row[col+1:]
            self.conSeriesData.Rows[i]=row

        # And redisplay
        self.RefreshGridFromLSTData()

    # ------------------
    def ExtractScanner(self, col):
        # Start by adding a Scanned column to the right of the Notes column. (We check to see if one already exists.)
        # Located the Notes and Scanned columns, if any.
        scannedCol=None
        for i in range(0, len(self.conSeriesData.ColHeaders)):
            if self.conSeriesData.ColHeaders[i] == "Scanned":
                scannedCol=i
                break
        notesCol=None
        for i in range(0, len(self.conSeriesData.ColHeaders)):
            if self.conSeriesData.ColHeaders[i] == "Notes":
                notesCol=i
                break

        # Add the Scanned column if needed
        if scannedCol is None:
            for i in range(0, len(self.conSeriesData.Rows)):
                row=self.conSeriesData.Rows[i]
                row=row[:notesCol+2]+[""]+row[notesCol+2:]
                self.conSeriesData.Rows[i]=row
            self.conSeriesData.ColHeaders=self.conSeriesData.ColHeaders[:notesCol+1]+["Scanned"]+self.conSeriesData.ColHeaders[notesCol+1:]
            scannedCol=notesCol+1
            notesCol=notesCol

        # Now parse the notes looking for scanning information
        # Scanning Info will look like one of the four prefixes (Scan by, Scanned by, Scanned at, Scanning by) followed by
        #   two capitalized words
        #   or a capitalized word, then "Mc", then a capitalized word  (e.g., "Sam McDonald")
        #   or a capitalized word, then "Mac", then a capitalized word  (e.g., "Anne MacCaffrey")
        #   or "O'Neill"
        #   or a capitalized word, then a letter followed by a period, then a capitalized word  (e.g., "John W. Campbell")
        #   or a capitalized word followed by a number
        pattern=(
            "[sS](can by|cans by|canned by|canned at|canning by) ([A-Z][a-z]+) ("   # A variation of "scanned by" followed by a first name;
            #   This all followed by one of these:
            "(?:Mc|Mac|O')[A-Z][a-z]+|"     # Celtic names
            "[A-Z]\.[A-Z][a-z]+|"   # Middle initial
            "[A-Z][a-z]+|" # This needs to go last because it will ignore characters after it finds a match (with "Sam McDonald" it matches "Sam Mc")
            "[0-9]+)"       # Boskone 23
        )
        for i in range(0, len(self.conSeriesData.Rows)):
            row=self.conSeriesData.Rows[i]
            note=row[notesCol+1]
            m=re.search(pattern, note)
            if m is not None:
                row[scannedCol+1]=m.groups()[1]+" "+m.groups()[2]     # Put the matched name in the scanned
                note=re.sub(pattern, "", note)  # Delete the matched text from the note
                # Now remove leading and trailing spans of spaces and commas from the note.
                note=re.sub("^([ ,]*)", "", note)
                note=re.sub("([ ,]*)$", "", note)
                row[notesCol+1]=note

        # And redisplay
        self.RefreshGridFromLSTData()

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
        self.RefreshGridFromLSTData()

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
        self.RefreshGridFromLSTData()

    #------------------
    def MoveSelectionRight(self, rightClickedColumn):
        top, left, bottom, right=self.LocateSelection()

        for i in range(top-1, bottom):
            row=self.conSeriesData.Rows[i]
            row=row[:left-1]+[""]+row[left-1:right]+row[right+1:]
            self.conSeriesData.Rows[i]=row

        # Move the selection along with it
        self.DGrid.SelectBlock(top, left+1, bottom, right+1)

        # And redisplay
        self.RefreshGridFromLSTData()

    #------------------
    # Move the selection one column to the left.  The vacated cells to the right are filled with blanks
    def MoveSelectionLeft(self, rightClickedColumn):
        top, left, bottom, right=self.LocateSelection()

        for i in range(top-1, bottom):
            row=self.conSeriesData.Rows[i]
            row=row[:left-2]+row[left-1:right]+[""]+row[right:]
            self.conSeriesData.Rows[i]=row

        # Move the selection along with it
        self.DGrid.SelectBlock(top, left-1, bottom, right-1)

        # And redisplay
        self.RefreshGridFromLSTData()

    #------------------
    def OnGridCellChanged(self, event):
        row=event.GetRow()
        col=event.GetCol()
        newVal=self.DGrid.GetCellValue(row, col)

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
            self.RefreshGridFromLSTData()
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
            self.DGrid.AutoSizeColumns()
            self.DGrid.EvtHandlerEnabled=True
            return

        # What's left is column zero and thus the user is editing a row number
        # If it's an "X", the row has been deleted.
        if newVal.lower() == "x":
            del self.conSeriesData.Rows[row-1]
            event.Veto()                # This is a bit of magic to prevent the event from making later changes to the grid.
            self.RefreshGridFromLSTData()
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
        self.RefreshGridFromLSTData()
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
frame = MainWindow(None, "Sample editor")
app.MainLoop()
