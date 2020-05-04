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

        self._grid.SetColHeaders(self._grid._datasource.ColHeaders)
        self._grid.SetColTypes(self._grid._datasource.ColDataTypes)
        self._grid.FillInRowNumbers(self._grid.NumrowsR)

        self._grid.RefreshWindowFromData()
        self.Show()


    def OnAddFilesButton(self, event):
        event.Skip()
