from __future__ import annotations
from typing import Optional

import os
import wx
import wx.grid
import sys
from bs4 import BeautifulSoup, NavigableString
from urllib.request import urlopen
import json

from GeneratedConEditorFrame import GeneratedConEditorFrame

from HelpersPackage import Bailout, StripExternalTags, SubstituteHTML, FormatLink, FindBracketedText, WikiPagenameToWikiUrlname, UnformatLinks, RemoveAllHTMLTags
from HelpersPackage import FindIndexOfStringInList
from Log import LogOpen

class ConEditorFrame(GeneratedConEditorFrame):
    def __init__(self, parent):
        GeneratedConEditorFrame.__init__(self, parent)
        self.Show()


# Start the GUI and run the event loop
LogOpen("Log -- ConEditor.txt", "Log (Errors) -- ConEditor.txt")
app = wx.App(False)
frame = ConEditorFrame(None)
app.MainLoop()
