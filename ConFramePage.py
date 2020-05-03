import wx

from MainConFrame import MainConFrame
from Grid import Grid
from ConPage import ConPage, ConFile

#####################################################################################
class MainConFrameClass(MainConFrame):
    def __init__(self, parent):
        MainConFrame.__init__(self, parent)
        self._grid: Grid=Grid(self.gRowGrid)
        self._grid._datasource=ConPage()

        self.DGrid.SetColHeaders(self._grid._datasource.ColHeaders)
        self.DGrid.SetColTypes(self._grid._datasource.ColDataTypes)
        self.DGrid.FillInRowNumbers(self.DGrid.NumrowsR)

        self._grid.RefreshWindowFromData()
        self.Show()


    @property
    def DGrid(self) -> Grid:
        return self._grid

