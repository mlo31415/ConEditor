from __future__ import annotations
from typing import Optional

import os
import json
import sys

class Settings():
    g_settings={}

    def Load(self, fname: str) -> None:
        if os.path.exists(fname):
            with open(fname, "r") as file:
                lines=file.read()
                if len(lines) > 0:
                    Settings.g_settings=json.loads(lines)

    def Put(self, name: str, val: str) -> None:
        Settings.g_settings[name]=val
        self.Save()

    def Save(self) -> None:
        pathname=os.path.join(os.path.split(sys.argv[0])[0], "ConEditor settings.json")
        with open(pathname, "w+") as file:
            file.write(json.dumps(Settings.g_settings))

    def Get(self, name: str) -> Optional[str]:
        if name not in Settings.g_settings.keys():
            return None
        return Settings.g_settings[name]