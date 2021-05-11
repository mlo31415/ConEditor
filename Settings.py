from __future__ import annotations
from typing import Optional, Dict

import os
import json

class Settings():
    g_settings:Dict[str, ]={}
    g_settingsFilename: str=""

    def Load(self, fname: str) -> None:
        Settings.g_settingsFilename=os.path.join(os.getcwd(), fname)
        if os.path.exists(fname):
            with open(fname, "r") as file:
                lines=file.read()
                if len(lines) > 0:
                    Settings.g_settings=json.loads(lines)

    def Put(self, name: str, val) -> None:
        Settings.g_settings[name]=val
        self.Save()

    def Save(self) -> None:
        if len(Settings.g_settingsFilename)> 0 and os.path.exists(Settings.g_settingsFilename):
            with open(Settings.g_settingsFilename, "w+") as file:
                file.write(json.dumps(Settings.g_settings))

    def Get(self, name: str) -> Optional[str]:
        if name not in Settings.g_settings.keys():
            return None
        return Settings.g_settings[name]