from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ConInstance import ConInstanceRow
from FTP import FTP

# These classes track changes to the list of files for a particular Con Instance
# All it cares about is the files and their names
# Once the user is done editing the ConInstance page and does an upload, this class will provide the instructions
#   for the upload so that all the accumulated edits get up there.

@dataclass
class Delta:
    Verb: str
    Con: ConInstanceRow
    Oldname: str=""

    def __str__(self) -> str:
        s=f"{self.Verb}: {self.Con}"
        if self.Oldname is not None and len(self.Oldname) > 0:
            s+=f" oldname={self.Oldname}"
        return s


# Changes (the tuple providing info needed to defined them) are (in the order in which they must be executed):
#       Delete a file which exists on the website ("delete", con, "")
#       Rename an existing website file ("rename", con, oldname)
#       Add a new file ("add", con, "")
#       Replace an existing file ("replace", con, oldname)
# When two deltas affect the same file, they are usually merged.  (E.g., Add followed by Delete cancels out; Add followed by Rename updates the Add with the new name.)
class ConInstanceDeltaTracker:
    def __init__(self):
        self._deltas: list[Delta]=list()

    def __str__(self) -> str:
        if self._deltas is None or len(self._deltas) == 0:
            return ""
        s=""
        for d in self._deltas:
            s+=f">>{d}\n"
        return s

    def Add(self, con: ConInstanceRow) -> None:
        self._deltas.append(Delta("add", con, ""))

    def Delete(self, con: ConInstanceRow) -> None:
        # If the item being deleted was just added, simply remove the add from the deltas list
        for i, item in enumerate(self._deltas):
            if item.Verb == "add":
                if item.Con.DisplayTitle == con.DisplayTitle:
                    del self._deltas[i]
                    return
        # OK, the item is not queued to be added so it must already be on the website: add a delete action to the deltas list
        self._deltas.append(Delta("delete", con, ""))

    # Change the name of a file on the website site
    def Rename(self, con: ConInstanceRow, oldname: str) -> None:
        # First check to see if this is a rename of a rename.  If it is, merge them by updating the existing rename.
        for i, item in enumerate(self._deltas):
            if item.Verb == "rename":
                if item.Oldname == con.DisplayTitle:
                    self._deltas[i]=Delta("rename", con, oldname)
                    return
            # Now check to see if this is a rename of a newly-added file.  If so, we just modify the add Delta
            elif item.Verb == "add":
                if item.Con.DisplayTitle == con.DisplayTitle:
                    item.Con=con
                    return

        # If it doesn't match anything in the delta list, then it must be a rename of an existing file.
        self._deltas.append(Delta("rename", con, oldname))

    # We want to replace one file with another
    def Replace(self, con: ConInstanceRow, oldname: str):
        # Check to see if the replacement is in a row yet to be uploaded or a row which has been renamed.
        for i, item in enumerate(self._deltas):
            if item.Verb == "rename":
                if item.Con.SourcePathname == con.SourcePathname:
                    self._deltas[i]=Delta("rename", con, oldname)
                    return
            # Now check to see if this is a rename of a newly-added file
            elif item.Verb == "add":
                if item.Con.SourcePathname == con.SourcePathname:
                    # Just update the local pathname in the add entry
                    self._deltas[i].Con.SourcePathname=con.SourcePathname
                    return

        # If it doesn't match anything in the delta list, then it must be a new local file to replace an old one in an existing entry
        # We need to delete the old file and then upload the new.
        self._deltas.append(Delta("replace", con, oldname))


    @property
    def Num(self) -> int:
        return len(self._deltas)

    @property
    def Deltas(self) -> list[Delta]:
        return self._deltas


class UpdateFTPLog:
    g_ID: str|None =None
    g_Logfilename: str|None=None

    @staticmethod
    def Init(id: str, logfilename: str) -> None:
        UpdateFTPLog.g_ID=id
        UpdateFTPLog.g_Logfilename=logfilename

    @staticmethod
    def Tagstring() -> str:
        return f"[{FTP().GetEditor()}  {datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")} EST]"


    @staticmethod
    def LogDeltas(series: str, con: str = "", deltas: ConInstanceDeltaTracker|None = None):
        lines=f"Uploaded ConInstance: {series}:{con}   {UpdateFTPLog.Tagstring()}\n"

        if deltas is not None and deltas.Num > 0:
            lines+=f"^^deltas by {FTP().GetEditor()}:\n{deltas}\n"

        FTP().AppendString(UpdateFTPLog.g_Logfilename, lines)


    @staticmethod
    def LogText(txt: str):
        FTP().AppendString(UpdateFTPLog.g_Logfilename, f"{txt} {UpdateFTPLog.Tagstring()}\n")