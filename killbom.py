"""killbom

Removes the UTF-8 BOM in commits.
"""


import codecs
import io
import os
import shutil

from mercurial import util


def killbom(ui, repo, **opts):
    """Removes Unicode BOM."""
    onlyUtf8 = True if opts["utf8only"] else False
    if onlyUtf8:
        ui.debug("killbom applied to UTF-8 encoding only\n")
    else:
        ui.debug("killbom applied to UTF-8, UTF-16 and UTF-32 encodings\n")

    return execute(ui, repo, repo[None], opts, onlyUtf8, True)

def checkbom(ui, repo, **opts):
    """Checks for Unicode BOM."""
    onlyUtf8 = True if opts["utf8only"] else False
    if onlyUtf8:
        ui.debug("checkbom applied to UTF-8 encoding only\n")
    else:
        ui.debug("checkbom applied to UTF-8, UTF-16 and UTF-32 encodings\n")

    return execute(ui, repo, repo[None], opts, onlyUtf8, False)


def modify(ui, repo, **kwargs):
    ui.debug("killbom modify hook\n")
    return execute(ui, repo, repo[None], kwargs, False, True)

def verify(ui, repo, **kwargs):
    ui.debug("killbom verify hook\n")
    return execute(ui, repo, repo[None], kwargs, False, False)


def reposetup(ui, repo):
    ui.setconfig("hooks", "precommit.killbom", modify)
    ui.setconfig("hooks", "pretxncommit.killbom", verify)
    ui.setconfig("hooks", "pretxnchangegroup.killbom", verify)

cmdtable = {
    'killbom':  (
                 killbom,
                 [('8', 'utf8only', False, 'removes only UTF-8 BOM signature')],
                 'hg killbom [options]'
                ),

    'checkbom': (
                 checkbom,
                 [('8', 'utf8only', False, 'checks for only UTF-8 BOM signature')],
                 'hg checkbom [options]'
                )
}

testedwith = '2.9.2 3.0.2'
buglink = 'https://bitbucket.org/jmedved/hg-killbom/issues'

################################################################################    

def execute(ui, repo, ctx, opts, onlyUtf8, allowModify):
    maxSize = ui.config('tortoisehg', 'maxdiff', default='1024', untrusted=False)
    if not maxSize.isdigit: maxSize = 1024;
    maxSize = int(maxSize) * 1024; #converts to bytes
    ui.debug("maximum file size to check is {0}\n".format(maxSize))

    anyBomed = False

    files = ctx.files() if ctx else []
    ui.debug("checking {0} file(s)\n".format(len(files)))

    for file in files:
        ui.note("checking {0}\n".format(file))
        
        if not os.path.isfile(file):
            ui.debug("skipping {0}: not found\n".format(file))
            continue
        
        size = os.path.getsize(file)
        if size < 3:
            ui.debug("skipping {0}: too small\n".format(file))
            continue
        
        if size > maxSize:
            ui.debug("skipping {0}: too big\n".format(file))
            continue

        with io.open(file, 'rb') as f:
            raw = f.read(8)
            f.close()
        
        if raw.startswith(codecs.BOM_UTF8):
            encoding = "utf-8-sig"
        else:
            if onlyUtf8:
                ui.debug("skipping {0}: no UTF-8 BOM\n".format(file))
                continue
            else:
                if raw.startswith(codecs.BOM_UTF16_BE):
                    encoding = "utf-16-be"
                elif raw.startswith(codecs.BOM_UTF16_LE):
                    encoding = "utf-16-le"
                elif raw.startswith(codecs.BOM_UTF32_BE):
                    encoding = "utf-32-be"
                elif raw.startswith(codecs.BOM_UTF32_LE):
                    encoding = "utf-32-le"
                else:
                    ui.debug("skipping {0}: no known Unicode BOM\n".format(file))
                    continue

        
        ui.debug("detected {1} in {0}\n".format(file, encoding))

        if allowModify:
            ui.debug("removing BOM in {0}\n".format(file))
            with io.open(file, "rb") as f:
                raw = f.read()
                f.close()

            raw = raw.decode(encoding)
            raw = raw.encode("utf-8")
            
            #do it again otherwise utf-16 and utf-32 will have utf-8 bom present
            raw = raw.decode("utf-8-sig")
            raw = raw.encode("utf-8")
 
            newFile = file + ".killbom.final"
            with io.open(newFile, "wb") as f:
                f.write(raw)
                f.close()

            shutil.move(newFile, file)
            ui.status("removed BOM in {0}\n".format(file))
        else:
            ui.status("skipped BOM removal for {0}\n".format(file))
            anyBomed = True

    return 1 if anyBomed else 0
