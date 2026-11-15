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
        # A prominent line that acknowledges a Pause/Quit request the instant it is registered (and explains that
        # it takes effect when the file in progress finishes). Bold + coloured so it stands out from the status.
        self._stateText=wx.StaticText(self, label="")
        f=self._stateText.GetFont(); f.MakeBold(); self._stateText.SetFont(f)
        self._stateText.SetForegroundColour(wx.Colour(180, 80, 0))
        status.Add(self._stateText, 0, wx.ALL, 2)
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

    # ---- button handlers: set a flag and give immediate on-screen acknowledgement; the walk acts on the flag at
    # the next checkpoint (after the file in progress finishes). The handler runs inside a pump (see _Pump), so the
    # label and banner it sets below repaint right away -- that is the immediate feedback the button press needs.
    def OnPause(self, event) -> None:
        if self._quit:
            return
        self._paused=not self._paused
        if self._paused:
            self._pauseButton.SetLabel("Resume")
            self._SetState("Pausing — will take effect when the current file finishes"+self._nowActionParen())
        else:
            self._pauseButton.SetLabel("Pause")
            self._SetState("Resuming…")

    def OnQuit(self, event) -> None:
        if self._quit:
            return
        self._quit=True
        self._paused=False          # unblock the pause loop if we were paused, so the walk can wind down and save
        self._pauseButton.Enable(False)
        self._quitButton.SetLabel("Quitting…")
        self._quitButton.Enable(False)
        self._SetState("Quitting — will stop and save when the current file finishes"+self._nowActionParen())

    # The current action in parentheses, e.g. " (Uploading xxxTest/Con 3/program.pdf)", for the banner; "" if idle.
    def _nowActionParen(self) -> str:
        lbl=self._nowText.GetLabel()
        return f" ({lbl[5:]})" if lbl.startswith("Now: ") and lbl != "Now: -" and len(lbl) > 5 else ""

    def _SetState(self, text: str) -> None:
        self._stateText.SetLabel(text)
        self._stateText.Update()    # repaint this one control immediately, without waiting for the next idle

    @property
    def QuitRequested(self) -> bool:
        return self._quit

    # ---- API the walk uses ----
    # Append a permanent line to the log. A bottom-level PDF line is prefixed by the caller with its directory.
    def LogItem(self, text: str) -> None:
        self._log.AppendText(text+"\n")

    # Transient "what is happening right now" line. Named Update so this can stand in for ProgressMessage2. The
    # walk calls it before each slow step (download / stamp / upload of a PDF, saving a page), and it pumps the
    # event queue so the new "Now:" line actually paints AND a Pause/Quit click made during the previous step is
    # picked up and acknowledged -- without this, nothing renders between one checkpoint and the next.
    def Update(self, msg: str, delay: float=0) -> None:
        self._nowText.SetLabel("Now: "+msg)
        self._RefreshElapsed()
        self._Pump()

    # Process pending UI events (button clicks, repaints) on the GUI thread. Safe with no running loop (tests).
    def _Pump(self) -> None:
        try:
            wx.SafeYield(self, onlyIfNeeded=True)
        except Exception:
            pass

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
        self._Pump()
        if self._paused and not self._quit:
            self._SetState("Paused — press Resume to continue.")
            while self._paused and not self._quit:
                self._RefreshElapsed()
                self._Pump()
                wx.MilliSleep(100)
            if not self._quit:
                self._SetState("")      # resumed
        return self._quit
