import wx

from MainConFrame import MainConFrame
from Grid import Grid
from ConPage import ConPage, ConFile

#####################################################################################
class MainConFrameClass(MainConFrame):
    def __init__(self, parent):
        MainConFrame.__init__(self, parent)
        self._grid=self.gRowGrid
        self._conPage=ConPage()

        self.Show()


    @property
    def DGrid(self) -> Grid:
        return self._grid

    def RefreshWindowFromData(self):
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
                self.DGrid.Set(i, j, self.conSeriesData.Rows[i].GetVal(self.conSeriesData.Colheaders[j]))

        self.ColorCellByValue()
        self.DGrid.Grid.ForceRefresh()
        self.DGrid.Grid.AutoSizeColumns()

        self.tTopMatter.Value=self.conSeriesData.Name
