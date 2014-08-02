"""killbom

Removes the UTF-8 BOM in commits.
"""


import codecs
import encodings
import os

from mercurial import util


def killbom(ui, repo, **opts):
    """Removes UTF-8 BOM."""
    return execute(ui, repo, repo[None], opts, True)

def checkbom(ui, repo, **opts):
    """Checks for UTF-8 BOM."""
    return execute(ui, repo, repo[None], opts, False)


def modify(ui, repo, **kwargs):
    ui.debug("killbom modify hook\n")
    return execute(ui, repo, repo[None], kwargs, True)

def verify(ui, repo, **kwargs):
    ui.debug("killbom verify hook\n")
    return execute(ui, repo, repo[None], kwargs, False)


def reposetup(ui, repo):
    ui.setconfig("hooks", "precommit.killbom", modify)
    ui.setconfig("hooks", "pretxncommit.killbom", verify)
    ui.setconfig("hooks", "pretxnchangegroup.killbom", verify)

cmdtable = {
    'killbom':  (
                 killbom,
                 [],
                 'hg killbom [options]'
                ),

    'checkbom': (
                 checkbom,
                 [],
                 'hg checkbom [options]'
                )
}

testedwith = '2.9.2 3.0.2'
buglink = 'https://bitbucket.org/jmedved/hg-killbom/issues'

################################################################################    

def execute(ui, repo, ctx, opts, allowModify):
    anyBomed = False

    files = ctx.files() if ctx else []
    for file in files:
        ui.note("checking %s\n" % file)
        
        if not os.path.isfile(file):
            ui.debug("skipping %s: not found\n" % file)
            continue
        
        size = os.path.getsize(file)
        if size < 3:
            ui.debug("skipping %s: too small\n" % file)
            continue
        
        if size > 1048576:
            ui.debug("skipping %s: too big\n" % file)
            continue

        with open(file, 'rb') as f:
            raw = f.read(3)
            f.close()
        
        if not raw.startswith(codecs.BOM_UTF8):
            ui.debug("skipping %s: no UTF-8 BOM\n" % file)
            continue
        else:
            encoding = "utf-8-sig"

        if allowModify:
            ui.debug("removing BOM in %s\n" % file)
            with codecs.open(file, "rb", encoding=encoding) as f:
                raw = f.read(size)
                f.close()
            with codecs.open(file, "wb", encoding="utf-8") as f:
                f.write(raw)
                f.close()
            ui.status("removed BOM in %s\n" % file)
        else:
            ui.status("skipped BOM removal for %s\n" % file)
            anyBomed = True

    return 1 if anyBomed else 0
