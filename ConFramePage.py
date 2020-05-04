import wx
import os

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
        # Call the File Open dialog to get an con series HTML file
        dlg=wx.FileDialog(self, "Select files to upload", ".", "", "*.*", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)
        dlg.SetWindowStyle(wx.STAY_ON_TOP)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Raise()
            dlg.Destroy()
            return

        conf=ConFile()
        conf._displayTitle=dlg.GetFilename()
        conf._pathname=os.path.join(dlg.GetDirectory(), dlg.GetFilename())
        self._grid._datasource.Rows.append(conf)
        dlg.Destroy()
        self._grid.RefreshWindowFromData()