from __future__ import annotations
from typing import List, Optional

from datetime import datetime

from ConInstance import ConFile
from FTP import FTP

# These classes track changes to the list of files for a particular Con Instance
# All it cares about is the files and their names
# Once the user is done editing the ConInstance page and does an upload, this class will provide the instructions
#   for the upload so that all the accumulated edits get up there.

class Delta:
    def __init__(self, verb: str, confile: ConFile, oldname: str):
        self._verb: str=verb
        self._con: ConFile=confile
        self._oldname: str=oldname

    def __str__(self) -> str:
        s=self.Verb+": "+str(self.Con)
        if self.Oldname is not None and len(self.Oldname) > 0:
            s+=" oldname="+self.Oldname
        return s

    
    @property
    def Verb(self):
        return self._verb

    @property
    def Con(self):
        return self._con
    @Con.setter
    def Con(self, val: ConFile):
        self._con=val
    
    @property
    def Oldname(self):
        return self._oldname

# Changes (the tuple providing info needed to defined them) are (in the order in which they must be executed):
#       Delete a file which exists on the website ("delete", con, "")
#       Rename an existing website file ("rename", con, oldname)
#       Add a new file ("add", con, "")
#       Replace an existing file ("replace", con, oldname)
# When two deltas affect the same file, they are usually merged.  (E.g., Add followed by Delete cancels out; Add followed by Rename updates the Add with the new name.)
class ConInstanceDeltaTracker:
    def __init__(self):
        self._deltas: List[Delta]=[]

    def __str__(self) -> str:
        if self._deltas is None or len(self._deltas) == 0:
            return []
        s=""
        for d in self._deltas:
            s+=">>"+str(d)+"\n"
        return s

    def Add(self, con: ConFile) -> None:
        self._deltas.append(Delta("add", con, ""))

    def Delete(self, con: ConFile) -> None:
        # If the item being deleted was just added, simply remove the add from the deltas list
        for i, item in enumerate(self._deltas):
            if item.Verb == "add":
                if item.Con.DisplayTitle == con.DisplayTitle:
                    del self._deltas[i]
                    return
        # OK, the item is not queued to be added so it must already be on the website: add a delete action to the deltas list
        self._deltas.append(Delta("delete", con, ""))

    # Change the name of a file on the website site
    def Rename(self, con: ConFile, oldname: str) -> None:
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
    def Replace(self, con: ConFile, oldname: str):
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
    def Deltas(self) -> List[Delta]:
        return self._deltas



class UpdateLog():
    g_ID: Optional[str]=None

    def Init(self, id: str):
        UpdateLog.g_ID=id
        pass

    def Log(self, series: str, con: str = "", deltas: Optional[ConInstanceDeltaTracker] = None):
        lines="Uploaded ConInstance: "+series+":"+con+"   "+"["+UpdateLog.g_ID+"  "+datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST]\n"
        if deltas is not None and deltas.Num > 0:
            lines+="^^deltas by "+FTP().GetEditor()+":\n"+str(deltas)+"\n"
        FTP().AppendString("/updatelog.txt", lines)
        pass

    def LogText(self, txt: str):
        FTP().AppendString("/updatelog.txt", txt+"   ["+UpdateLog.g_ID+"  "+FTP().GetEditor()+"  "+datetime.now().strftime("%A %B %d, %Y  %I:%M:%S %p")+" EST]\n")