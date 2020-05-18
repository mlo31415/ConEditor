from __future__ import annotations
from typing import Optional

import ftplib
import json
import os

from HelpersPackage import Log


class FTP:
    g_ftp: FTP=None      # A single FTP link for all instances of the class
    g_localroot: str=""
    g_curdirpath="/"


    def OpenConnection(self, cre: str) -> bool:
        with open(cre) as f:
            d=json.loads(f.read())
        FTP.g_ftp=ftplib.FTP(host=d["host"], user=d["ID"], passwd=d["PW"])
        pass


    def SetRoot(self, local=""):
        FTP.g_localroot=local

    def UpdateCurpath(self, newdir: str) -> None:
        if newdir == "/":
            FTP.g_curdirpath="/"
        elif newdir == "..":
            if FTP.g_curdirpath != "/":
                head, tail=os.path.split(self.g_curdirpath)
                FTP.g_curdirpath=head
        else:
            if FTP.g_curdirpath == "/":
                FTP.g_curdirpath+=newdir
            else:
                FTP.g_curdirpath+="/"+newdir

    def CWD(self, newdir: str) -> bool:
        Log("cwd from '"+self.PWD()+"' to '"+newdir+"'")
        msg=self.g_ftp.cwd(newdir)
        Log(msg)
        ret=msg.startswith("250 OK.")
        if ret:
            self.UpdateCurpath(newdir)
        self.PWD()
        return ret

    def MKD(self, newdir: str) -> bool:
        Log("make directory: '"+newdir+"'")
        msg=self.g_ftp.mkd(newdir)
        Log(msg)
        return msg.startswith("250 OK.")

    def PWD(self) -> str:
        dir=self.g_ftp.pwd()
        Log("pwd is now '"+dir+"'")

        # Check to see if this matches what self._curdirpath thinks it ought to
        head, tail=os.path.split(self.g_curdirpath)
        if self.g_curdirpath != dir and tail != dir:
            Log("PWD: error detected -- self._curdirpath='"+self.g_curdirpath+"' and pwd returns '"+dir+"'")
            assert False
        return dir

    def Exists(self, filedir: str) -> bool:
        Log("Does '"+filedir+"' exist?")
        if filedir in self.g_ftp.nlst():
            Log("'"+filedir+"' exists")
            return True
        Log("'"+filedir+"' does not exist")
        return False


    #-------------------------------
    def SetDirectory(self, newdir: str, create: bool=False) -> None:
        Log("SetDirectory: "+newdir)

        # Does the directory exist?
        if not self.Exists(newdir):
            # If not, are we allowed to create it"
            if not create:
                Log("SetDirectory was called with create=False")
                return
            if not self.MKD(newdir):
                Log("mkd failed...bailing out...")
                return

        # Now cwd to it.
        if not self.CWD(newdir):
            Log("cwd failed...bailing out...")


    #-------------------------------
    # Move a string to the Conventions FTP site or get a string from it
    # We map the local directory  ./Convention publications  to fanac.org/Cons
    # These two functions rely on the global g_ftp being defined and open
    def PutAF(self, fname: str) -> bool:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return False

        localfname=FTP.g_localroot+"/"+fname
        Log("STOR "+fname+"  from "+localfname)
        with open(localfname, "rb") as f:
            Log(self.g_ftp.storbinary("STOR "+fname, f))


    def GetFTPA(self, fname: str) -> Optional[str]:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return None

        global out
        out=""
        def my_function(data):
            global out
            out+=data
        status=self.g_ftp.retrlines('RETR '+fname, callback=my_function)
        Log('RETR '+fname+" -> "+status)
        Log(out)
        return out


