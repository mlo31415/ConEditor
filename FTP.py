from __future__ import annotations
from typing import Optional

import ftplib
import json
import io

from HelpersPackage import Log


class FTP:
    g_ftp: FTP=None      # A single FTP link for all instances of the class
    _localroot: str=""
    _siteroot: str=""
    _curdirpath=""


    def OpenConnection(self, cre: str) -> bool:
        with open(cre) as f:
            d=json.loads(f.read())
        FTP.g_ftp=ftplib.FTP(host=d["host"], user=d["ID"], passwd=d["PW"])


    def SetRoots(self, local="", site=""):
        FTP._localroot=local
        FTP._siteroot=site

    def CWD(self, newdir: str) -> bool:
        Log("cwd from '"+FTP.g_ftp.pwd()+"' to '"+newdir+"'")
        msg=FTP.g_ftp.cwd(newdir)
        Log(msg)
        Log("pwd now '"+FTP.g_ftp.pwd()+"'")
        return msg.startswith("250 OK.")

    def MKD(self, newdir: str) -> bool:
        Log("make directory: '"+newdir+"'")
        msg=FTP.g_ftp.mkd(newdir)
        Log(msg)
        return msg.startswith("250 OK.")

    def Exists(self, filedir: str) -> bool:
        Log("Does '"+filedir+"' exist?")
        if filedir in FTP.g_ftp.nlst():
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
            if not FTP().MKD(newdir):
                Log("mkd failed...bailing out...")
                return

        # Now cwd to it.
        if not FTP().CWD(newdir):
            Log("cwd failed...bailing out...")


    #-------------------------------
    # Move a string to the Conventions FTP site or get a string from it
    # We map the local directory  ./Convention publications  to fanac.org/Cons
    # These two functions rely on the global g_ftp being defined and open
    def PutAF(self, fname: str) -> bool:
        if FTP.g_ftp is None:
            Log("FTP not initialized")
            return False

        localfname=FTP._localroot+"/"+fname
        Log("STOR "+fname+"  from "+localfname)
        with open(localfname, "rb") as f:
            Log(FTP.g_ftp.storbinary("STOR "+fname, f))


    def GetFTPA(self, fname: str) -> Optional[str]:
        if FTP.g_ftp is None:
            Log("FTP not initialized")
            return None

        global out
        out=""
        def my_function(data):
            global out
            out+=data
        status=FTP.g_ftp.retrlines('RETR '+fname, callback=my_function)
        Log('RETR '+fname+" -> "+status)
        Log(out)
        return out


