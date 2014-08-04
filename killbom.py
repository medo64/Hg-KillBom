"""
killbom

Removes the Unicode BOM in commits.
"""


import codecs
import io
import os
import shutil

from mercurial import util


def killbom(ui, repo, **opts):
    """Removes Unicode BOM."""
    kb = KillBom(ui, repo, opts, ['modify'])
    return kb.process()

def checkbom(ui, repo, **opts):
    """Checks for Unicode BOM."""
    kb = KillBom(ui, repo, opts, ['verify'])
    return kb.process()


def modify(ui, repo, **kwargs):
    ui.debug("killbom: modify hook\n")
    kb = KillBom(ui, repo, None, ['modify', 'verify', 'ignore'])
    return kb.process()

def verify(ui, repo, **kwargs):
    ui.debug("killbom: verify hook\n")
    kb = KillBom(ui, repo, None, ['verify', 'ignore'])
    return kb.process()


def reposetup(ui, repo):
    ui.setconfig("hooks", "precommit.killbom", modify)
    ui.setconfig("hooks", "pretxncommit.killbom", verify)
    ui.setconfig("hooks", "pretxnchangegroup.killbom", verify)

cmdtable = {
    'killbom':  (
                 killbom,
                 [('8', 'utf8only', False, "removes only UTF-8 BOM signature"),
                  ('a', 'all', False, "check all files in the repository")],
                 'hg killbom [options]'
                ),

    'checkbom': (
                 checkbom,
                 [('8', 'utf8only', False, "checks for only UTF-8 BOM signature"),
                  ('a', 'all', False, "check all files in the repository")],
                 'hg checkbom [options]'
                )
}


testedwith = '2.9.2 3.0.2'
buglink = 'https://bitbucket.org/jmedved/hg-killbom/issues'


################################################################################


class KillBom:
    BOM_UTF8     = ('utf-8-sig', codecs.BOM_UTF8,     "utf-8")
    BOM_UTF16_LE = ('utf-16_le', codecs.BOM_UTF16_LE, "utf-16le")
    BOM_UTF16_BE = ('utf-16_be', codecs.BOM_UTF16_BE, "utf-16be")
    BOM_UTF32_LE = ('utf-32_le', codecs.BOM_UTF32_LE, "utf-32le")
    BOM_UTF32_BE = ('utf-32_be', codecs.BOM_UTF32_BE, "utf-32be")
    BOM_ALL = [BOM_UTF8, BOM_UTF16_LE, BOM_UTF16_BE, BOM_UTF32_LE, BOM_UTF32_BE]

    def __init__(self, ui, repo, opts, validActions):
        self.ui = ui

        if (opts == None):
            ui.debug("killbom: reading settings from hgrc\n")
            action = ui.config('killbom', 'action', '');
            encodings = [encoding.lower() for encoding in ui.configlist('killbom', 'encodings', default=[])]
            maxsize = ui.config('killbom', 'maxsize', self.ui.config('tortoisehg', 'maxdiff', default='1024'));
            modified, added, removed, deleted, unknown, ignored, clean = repo.status(clean=True)
            files = modified + added

        else: #check from command line
            ui.debug("killbom: reading settings from command line\n")
            action = validActions[0];
            encodings = ['utf-8-sig'] if opts["utf8only"] else []
            maxsize = opts["maxsize"] if "maxsize" in opts else ui.config('killbom', 'maxsize', self.ui.config('tortoisehg', 'maxdiff', default='1024'))
            modified, added, removed, deleted, unknown, ignored, clean = repo.status(clean=True)
            if opts["all"]:
                files = modified + added + clean
            else:
                files = modified + added

        action = action.lower()
        self.action = validActions[0]
        for validAction in validActions:
            if validAction==action:
                self.action = validAction
                break
        ui.note("killbom: action: {0}\n".format(self.action))

        self.encodings = []
        for encoding in encodings:
            if   encoding=="utf-8-sig" or encoding=="utf-8"    or encoding=="utf8sig" or encoding=="utf8" : self.encodings.append(self.BOM_UTF8)
            elif encoding=="utf-16-le" or encoding=="utf-16le" or encoding=="utf16le" or encoding=="utf16": self.encodings.append(self.BOM_UTF16_LE)
            elif encoding=="utf-16-be" or encoding=="utf-16be" or encoding=="utf16be"                     : self.encodings.append(self.BOM_UTF16_BE)
            elif encoding=="utf-32-le" or encoding=="utf-32le" or encoding=="utf32le" or encoding=="utf32": self.encodings.append(self.BOM_UTF32_LE)
            elif encoding=="utf-32-be" or encoding=="utf-32be" or encoding=="utf32be"                     : self.encodings.append(self.BOM_UTF32_BE)
            else: ui.warn("unknown encoding {0}!\n".format(encoding))
        if len(self.encodings) == 0: self.encodings = self.BOM_ALL
        ui.note("killbom: encodings:")
        [ui.note(" " + encoding[2]) for encoding in self.encodings]
        ui.note("\n")

        try:
            self.maxsize = int(maxsize) * 1024 
        except Exception, e:
            if not maxsize=='':
                ui.warn("unknown maximum size {1}: {0}!\n".format(e, maxsize))
            self.maxsize = 1024 * 1024
        ui.note("killbom: maxsize: {0} kb\n".format(self.maxsize / 1024))
        
        self.files = files
        ui.note("killbom: files (count): {0}\n".format(len(self.files)))


    def process(self):    
        anyBomed = False

        for file in self.files:
            self.ui.debug("killbom: checking {0}\n".format(file))
            
            if not os.path.isfile(file):
                self.ui.debug("killbom: skipping {0}: not found\n".format(file))
                continue
            
            size = os.path.getsize(file)
            if size < 3:
                self.ui.debug("killbom: skipping {0}: too small\n".format(file))
                continue
            
            if size > self.maxsize:
                self.ui.debug("killbom: skipping {0}: too big\n".format(file))
                continue

            with io.open(file, 'rb') as f:
                raw = f.read(8)
                f.close()


            detectedEncoding = None
            for encoding in self.encodings:
                self.ui.debug("killbom: testing for {1}\n".format(file, encoding[2]))
                if raw.startswith(encoding[1]):
                    detectedEncoding = encoding
                    break

            if detectedEncoding==None:
                if not self.action=='modify':
                    self.ui.debug("killbom: skipping {0}: Unicode BOM not found\n".format(file))
                continue

            if self.action=='modify':
                self.ui.debug("killbom: removing {1} BOM in {0}\n".format(file, detectedEncoding[2]))
                try:
                    with io.open(file, "rb") as f:
                        raw = f.read();
                        f.close()

                    raw = raw.decode(detectedEncoding[0])
                    raw = raw.encode("utf-8")
                    
                    #do it again otherwise utf-16 and utf-32 will have utf-8 bom present
                    raw = raw.decode("utf-8-sig")
                    raw = raw.encode("utf-8")

                    newFile = file + ".killbom"
                    with io.open(newFile, "wb") as f:
                        f.write(raw)
                        f.close()

                    shutil.move(newFile, file)
                    self.ui.status("removed {1} BOM in {0}\n".format(file, detectedEncoding[2]))
                except Exception, e:
                    self.ui.warn("error removing {1} BOM in {0}: {2}\n".format(file, detectedEncoding[2], e))

            else:
                self.ui.status("found {1} BOM in {0}\n".format(file, detectedEncoding[2]))
                anyBomed = True

        if not anyBomed:
            return 0
        elif self.action=='ignore':
            self.ui.debug("killbom: ignoring validation failure\n")
            return 0
        else:
            return 1

