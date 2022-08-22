#!/usr/bin/env python3

from fnmatch import fnmatch
from subprocess import run

from .inputs import Inputs


def gen_options(inputs: Inputs):
    options = []
    if inputs.config:
        options.extend(['-c', '~/.emacs.d/init.el'])
    if inputs.setup_file:
        options.extend(['-s', inputs.setup_file])
    return options


def tangle(f, inputs: Inputs):
    r = run(
        ['/opt/org-knit/knit.el', f.absolute(), '-t'] + gen_options(inputs),
        capture_output=True,
    )
    out = r.stderr.decode().rstrip()
    if out.startswith('Debugger entered--Lisp error'):
        raise RuntimeError(out)
    return out


export_functions = {
    'html': 'org-html-export-to-html',
    'md': 'org-md-export-to-markdown',
    'markdown': 'org-md-export-to-markdown',
    'ascii': 'org-ascii-export-to-ascii',
    'txt': 'org-ascii-export-to-ascii',
    'latex': 'org-latex-export-to-latex',
    'tex': 'org-latex-export-to-latex',
    'pdf': 'org-latex-export-to-pdf',
    'beamer': 'org-beamer-export-to-pdf',
    'odt': 'org-odt-export-to-odt',
    'org': 'org-org-export-to-org',
}


def export(f, mode, inputs: Inputs):
    mode = mode.lower()
    if mode not in export_functions.keys():
        raise ValueError(
            f'Export format {mode} not recognised. Must be one of:'
            f' {export_functions.keys()}.'
        )

    options = gen_options(inputs)
    if (
        inputs.eval
        if isinstance(inputs.eval, bool)
        else any(fnmatch(f, glob) for glob in inputs.eval)
    ):
        options.append('-v')
    all_modes = list(map(lambda s: s.lower(), inputs.export))
    if mode == 'tex' and 'pdf' in all_modes:
        print('TeX file will be produced when exporting to PDF. Skipping.')
    elif mode == 'pdf' and 'tex' not in all_modes:
        options.extend(
            ['-e', """(add-to-list \'org-latex-logfiles-extensionsa "tex")"""]
        )

    r = run(
        (
            [
                '/opt/org-knit/knit.el',
                f.absolute(),
                '-x',
                export_functions[mode],
            ]
            + options
        ),
        capture_output=True,
    )

    out = r.stderr.decode().rstrip()
    if out.startswith('Debugger entered--Lisp error'):
        raise RuntimeError(out)
    return out
