from typing import Union, Tuple, Optional, List
import time
import wx

from Log import Log, LogClose


# This is used:
#   with ModalDialogManager(dialog object, object's init arguments...) as dlg
#       dlg.ShowModal()
#       etc.
#   It deals with dlg.destroy()

class ModalDialogManager():
    def __init__(self, name: wx.Dialog, *args, **kargs):
        self._name: wx.Dialog=name
        self._args=args
        self._kargs=kargs

    def __enter__(self):
        self._dlg=self._name(*self._args, **self._kargs)
        return self._dlg

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._dlg.Destroy()


#==============================================================
# A class to display progress messages
#       ProgressMessage(parent).Show(message)       # Display a message, creating a popup dialog if needed
#       ProgressMessage(parent).Close(delay=sec)    # Delay sec seconds and then close the progress message
class ProgressMessage:
    _progressMessageDlg: wx.ProgressDialog=None

    def __init__(self, parent: Optional[wx.Dialog]) -> None:
        self._parent=parent


    def Show(self, s: Optional[str], close: bool=False, delay: float=0) -> None:  # ConInstanceFramePage
        if ProgressMessage._progressMessageDlg is None:
            ProgressMessage._progressMessageDlg=wx.ProgressDialog("progress", s, maximum=100, parent=None, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        Log("ProgressMessage.Show('"+s+"')")
        ProgressMessage._progressMessageDlg.Pulse(s)

        if close:
            self.Close(delay)

    def UpdateMessage(self, s: str):
        if ProgressMessage._progressMessageDlg is None:
            Log("ProgressMessage.UpdateMessage() called without an existing ProgressDialog")
            return
        Log("ProgressMessage.Update('"+s+"')")
        ProgressMessage._progressMessageDlg.Update(0, s)
        ProgressMessage._progressMessageDlg.Pulse(s)


    def Close(self, delay: float=0) -> None:
        if ProgressMessage._progressMessageDlg is None:
            Log("ProgressMessage.Close() called without an existing ProgressDialo")
            return

        if delay > 0:
            time.sleep(delay)
        ProgressMessage._progressMessageDlg.WasCancelled()
        ProgressMessage._progressMessageDlg=None
        if self._parent is not None:
            self._parent.SetFocus()
            self._parent.Raise()
