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

        #self.DGrid.NumcolsR=len(self._conPage.Colheaders)+1
        self.DGrid.SetColHeaders(self._conPage.Colheaders)
        self.DGrid.SetColTypes(self._conPage.ColDataTypes)
        self.DGrid.FillInRowNumbers(self.DGrid.NumrowsR)

        self.RefreshWindowFromData()
        self.Show()


    @property
    def DGrid(self) -> Grid:
        return self._grid

    def RefreshWindowFromData(self):
        self.DGrid.EvtHandlerEnabled=False
        self.DGrid.Grid.ClearGrid()

        self.DGrid.SetColHeaders(self.DGrid._colheaders)
        self.DGrid.FillInRowNumbers(self.DGrid.NumrowsR)

        # Fill in the cells
        for i in range(self._conPage.NumRows):
            for j in range(len(self._conPage.Colheaders)):
                self.DGrid.Set(i, j, self._conPage.Rows[i].GetVal(self._conPage.Colheaders[j]))

        self.DGrid.ColorCellsByValue()      #TODO: Maybe merge these into one call?
        #self.DGrid.Grid.ForceRefresh()
        self.DGrid.AutoSizeColumns()

        self.tConName=self._conPage._name
