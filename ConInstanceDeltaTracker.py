from __future__ import annotations
from typing import List, Union, Optional, Tuple

from ConInstance import ConFile

# This class tracks changes to the list of files for a particular Con Instance
# All it cares about is the files and their names
# Once the user is done editing the ConInstance page and does an upload, this class will provide the instructions
#   for the upload so that all the accumulated edits get up there.

# Changes (the tuple providing info needed to defined them) are (in the order in which they must be executed):
#       Delete a file which exists on the website ("delete", con, "")
#       Rename an existing website file ("rename", con, oldname)
#       Add a new file ("add", con, "")
class ConInstanceDeltaTracker():
    def __init__(self):
        self._deltas: List[Tuple[str, ConFile, str]]=[]

    def Add(self, con: ConFile) -> None:
        self._deltas.append(("add", con, ""))

    def Delete(self, con: ConFile) -> None:
        # If the item being deleted was just added, simply remove the add from the deltas list
        for i, item in enumerate(self._deltas):
            if item[0] == "add":
                if item[1].DisplayTitle == con.DisplayTitle:
                    del self._deltas[i]
                    return
        # OK, the item is not queued to be added so it must already be on the website: add a delete action to the deltas list
        self._deltas.append(("delete", con, ""))

    def Rename(self, con: ConFile, oldname: str) -> None:
        # First check to see if this is a rename of a rename.  If it is, merge them.
        for i, item in enumerate(self._deltas):
            if item[0] == "rename":
                if item[2] == con.DisplayTitle:
                    self._deltas[i]=("rename", con, oldname)
                    return

        # Now check to see if this is a rename of a newly-added file
        for i, item in enumerate(self._deltas):
            if item[0] == "add":
                if item[1].DisplayTitle == con.DisplayTitle:
                    newcon=con
                    newcon.DisplayTitle=oldname
                    self._deltas[i]=("add", newcon, "")     # In that case, change the sitename in the 'add' entry to be the new name and skip the rename step
                    return
        # It's just a rename of an existing file.
        self._deltas.append(("rename", con, oldname))

    @property
    def Num(self) -> int:
        return len(self._deltas)

    @property
    def Deltas(self) -> List[Tuple[str, ConFile, str]]:
        return self._deltas