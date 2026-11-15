from __future__ import annotations

import time
import wx

from WxHelpers import SetWindowIcon
from HelpersPackage import PyiResourcePath


# A modeless progress dialog for the three "bring up to date" actions. The walk runs on the main thread; this
# dialog stays responsive because the walk calls Checkpoint() after every bottom-level PDF, and Checkpoint()
# pumps the event queue (so the Pause/Quit buttons register) and, while paused, keeps pumping until Resume or
# Quit. The buttons only set flags; the walk acts on them at the next Checkpoint -- i.e. after the current PDF
# has finished -- so a pause or quit never interrupts a file mid-write.
#
# It also duck-types WxHelpers.ProgressMessage2 (it has an Update(msg, delay) method), so it can be passed as the
# "pm" the existing walk already threads through -- the con/sub-page loaders then report into this one window
# instead of opening their own progress dialogs.
class BringUpToDateProgress(wx.Dialog):

    def __init__(self, parent, title: str, showSeries: bool=False) -> None:
        super().__init__(parent, title=title, size=(640, 460),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        try:
            SetWindowIcon(self, PyiResourcePath("ConEditor.ico"))
        except Exception:
            pass

        self._start: float=time.monotonic()
        self._paused: bool=False
        self._quit: bool=False
        self._showSeries: bool=showSeries

        outer=wx.BoxSizer(wx.VERTICAL)

        # Status lines. "Series remaining" is shown only for a whole-site run.
        status=wx.BoxSizer(wx.VERTICAL)
        self._elapsedText=wx.StaticText(self, label="Elapsed: 0:00:00")
        status.Add(self._elapsedText, 0, wx.ALL, 2)
        self._seriesText=wx.StaticText(self, label="Series remaining: -")
        status.Add(self._seriesText, 0, wx.ALL, 2)
        self._seriesText.Show(showSeries)
        self._consText=wx.StaticText(self, label="Conventions remaining: -")
        status.Add(self._consText, 0, wx.ALL, 2)
        self._pdfsText=wx.StaticText(self, label="PDFs remaining on this page: -")
        status.Add(self._pdfsText, 0, wx.ALL, 2)
        self._nowText=wx.StaticText(self, label="Now: -")
        status.Add(self._nowText, 0, wx.ALL, 2)
        outer.Add(status, 0, wx.EXPAND | wx.ALL, 8)

        # The scrolling log of what has been updated.
        self._log=wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP)
        outer.Add(self._log, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Buttons.
        btns=wx.BoxSizer(wx.HORIZONTAL)
        self._pauseButton=wx.Button(self, label="Pause")
        self._quitButton=wx.Button(self, label="Quit")
        btns.Add(self._pauseButton, 0, wx.ALL, 6)
        btns.Add(self._quitButton, 0, wx.ALL, 6)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.SetSizer(outer)
        self._pauseButton.Bind(wx.EVT_BUTTON, self.OnPause)
        self._quitButton.Bind(wx.EVT_BUTTON, self.OnQuit)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)     # the window's X means "quit after the current item"

    # ---- button handlers: set a flag only; the walk acts on it at the next Checkpoint ----
    def OnPause(self, event) -> None:
        if self._quit:
            return
        self._paused=not self._paused
        self._pauseButton.SetLabel("Resume" if self._paused else "Pause")

    def OnQuit(self, event) -> None:
        self._quit=True
        self._pauseButton.Enable(False)
        self._quitButton.SetLabel("Quitting…")
        self._quitButton.Enable(False)

    @property
    def QuitRequested(self) -> bool:
        return self._quit

    # ---- API the walk uses ----
    # Append a permanent line to the log. A bottom-level PDF line is prefixed by the caller with its directory.
    def LogItem(self, text: str) -> None:
        self._log.AppendText(text+"\n")

    # Transient "what is happening right now" line. Named Update so this can stand in for ProgressMessage2.
    def Update(self, msg: str, delay: float=0) -> None:
        self._nowText.SetLabel("Now: "+msg)
        self._RefreshElapsed()

    def SetSeriesRemaining(self, n: int) -> None:
        if self._showSeries:
            self._seriesText.SetLabel(f"Series remaining: {n}")

    def SetConsRemaining(self, n: int) -> None:
        self._consText.SetLabel(f"Conventions remaining: {n}")

    def SetPdfsRemaining(self, n: int) -> None:
        self._pdfsText.SetLabel(f"PDFs remaining on this page: {n}")

    def _RefreshElapsed(self) -> None:
        secs=int(time.monotonic()-self._start)
        self._elapsedText.SetLabel(f"Elapsed: {secs//3600}:{(secs%3600)//60:02d}:{secs%60:02d}")

    # Called by the walk after each bottom-level PDF (and between items). Pumps the event queue so the buttons
    # register, blocks here while paused, and returns True if the user has asked to quit. The walk, seeing True,
    # stops taking on new work and unwinds, saving what it has done. No-op-safe when there is no running event
    # loop (e.g. tests): SafeYield simply finds nothing to do.
    def Checkpoint(self) -> bool:
        self._RefreshElapsed()
        try:
            wx.SafeYield(self, onlyIfNeeded=True)
            while self._paused and not self._quit:
                self._RefreshElapsed()
                wx.SafeYield(self, onlyIfNeeded=True)
                wx.MilliSleep(100)
        except Exception:
            pass
        return self._quit
