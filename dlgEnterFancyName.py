from GenDlgEnterFancyName import dlgEnterFancyName

#####################################################################################
class dlgEnterFancyNameWindow(dlgEnterFancyName):
    def __init__(self, parent):
        dlgEnterFancyName.__init__(self, parent)
        self._FancyName: str=""
        self.ShowModal()
        self.Destroy()

    def OnBuCreateConSeries(self, event):
        self.Hide()

    def OnTextChanged(self, event):
        self._FancyName=self.m_textCtrl4.GetValue()