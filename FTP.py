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
        if filedir == "/":
            return True     # "/" always exists
        if filedir in self.g_ftp.nlst():
            Log("'"+filedir+"' exists")
            return True
        Log("'"+filedir+"' does not exist")
        return False


    #-------------------------------
    # Setting create=True allows the creation of new directories as needed
    # Newdir can be a whole path starting with "/" or a path relative to the current directory if it doesn't starts with a "/"
    def SetDirectory(self, newdir: str, create: bool=False) -> bool:
        Log("SetDirectory: "+newdir)

        # Split newdir into components
        if newdir is None or len(newdir) == 0:
            return True

        components=[]
        if newdir[0] == "/":
            components.append("/")
            newdir=newdir[1:]
        components.extend(newdir.split("/"))

        # Now walk the component list
        for component in components:
            # Does the directory exist?
            if not self.Exists(component):
                # If not, are we allowed to create it"
                if not create:
                    Log("SetDirectory was called with create=False")
                    return False
                if not self.MKD(component):
                    Log("mkd failed...bailing out...")
                    return False

            # Now cwd to it.
            if not self.CWD(component):
                Log("cwd failed...bailing out...")
                return False

        return True


    #-------------------------------
    # Copy the local file fname to fanac.org in the current directory and with the same name
    def PutString(self, fname: str, s: str) -> bool:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return False

        if not os.path.exists("temp") or not os.path.isdir("temp"):
            os.mkdir("temp")
        localfname="temp/"+fname

        # Save the string as a local file
        with open(localfname, "w+") as f:
            f.write(s)

        localfname="temp/"+fname
        Log("STOR "+fname+"  from "+localfname)
        with open(localfname, "rb") as f:
            Log(self.g_ftp.storbinary("STOR "+fname, f))

    #-------------------------------
    # Copy the local file fname to fanac.org in the current directory and with the same name
    def PutFile(self, fname: str, toname: str) -> bool:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return False

        Log("STOR "+fname)
        with open(fname, "rb") as f:
            Log(self.g_ftp.storbinary("STOR "+fname, f))
            Log(self.g_ftp.rename(fname, toname))


    # Download the ascii file named fname in the current directory on fanac.org into a string
    def GetAsString(self, fname: str) -> Optional[str]:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return None

        if not os.path.exists("temp") or not os.path.isdir("temp"):
            os.mkdir("temp")

        localfname="temp/"+fname
        Log("RETR "+fname+"  to "+localfname)
        with open(localfname, "wb+") as f:
            msg=self.g_ftp.retrbinary("RETR "+fname, f.write)
            Log(msg)
            if not msg.startswith("226-File successfully transferred"):
                Log("GetAsString failed")
                return None


        with open(localfname, "r") as f:
            out=f.readlines()
        out="/n".join(out)
        Log(out)
        return out
