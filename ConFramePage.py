import wx

from MainConFrame import MainConFrame
from Grid import Grid
from ConPage import ConPage, ConFile

#####################################################################################
class MainConFrameClass(MainConFrame):
    def __init__(self, parent):
        MainConFrame.__init__(self, parent)
        self._grid: Grid=Grid(self.gRowGrid)
        self._conPage=ConPage()

        self.RefreshWindowFromData()
        self.Show()


    @property
    def DGrid(self) -> Grid:
        return self._grid

    def ColorCellByValue(self) -> None:
        pass

    def RefreshWindowFromData(self):
        self.DGrid.EvtHandlerEnabled=False
        self.DGrid.Grid.ClearGrid()

        # The grid is a bit non-standard, since I want to be able to edit row numbers and column headers
        # The row and column labels are actually the (editable) 1st column and 1st row of the spreadsheet (they're colored gray)
        # and the "real" row and column labels are hidden.
        self.gRowGrid.HideRowLabels()
        self.gRowGrid.HideColLabels()

        self.DGrid.Numcols=len(self._conPage.Colheaders)
        self.DGrid.SetColHeaders(self._conPage.Colheaders)
        self.DGrid.SetRowNumbers(self.DGrid.Numrows)

        # Fill in the cells
        for i in range(self._conPage.NumRows):
            for j in range(len(self._conPage.Colheaders)):
                self.DGrid.Set(i, j, self._conPage.Rows[i].GetVal(self._conPage.Colheaders[j]))

        self.ColorCellByValue()
        self.DGrid.Grid.ForceRefresh()
        self.DGrid.Grid.AutoSizeColumns()

        self.tConName=self._conPage._name
