from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup, NavigableString
from urllib.request import urlopen
import json

from GenConEditorFrame import GenConEditorFrame

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import LogOpen

class ConEditorFrame(GenConEditorFrame):
    def __init__(self, parent):
        GenConEditorFrame.__init__(self, parent)
        self.Show()




# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")
app = wx.App(False)
frame = ConEditorFrame(None)
app.MainLoop()
