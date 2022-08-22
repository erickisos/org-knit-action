#!/usr/bin/env -S python3 -u

import concurrent.futures
import sys
from fnmatch import fnmatch
from pathlib import Path
from shutil import copy, copytree

from . import inputs, knit, push, setup
from .colour import bblue, bgreen, blue, bold, bred, cyan, green, red, yellow

exit_code = 0
github_work_dir = Path('/github/workspace')

print(cyan | 'Starting org-knit')

params = inputs.Inputs(*sys.argv[1:])

params.args['name'] = push.git_result(
    github_work_dir, 'log', '-1', '--format=%an', 'HEAD'
)
params.args['email'] = push.git_result(
    github_work_dir, 'log', '-1', '--format=%ae', 'HEAD'
)

print('::group::configuration')
print(params.pretty_print())
print('::endgroup::')

if params.config:
    print('::group::setup emacs config')
    setup.config(params.config)
    print('::endgroup::')
else:
    setup.empty_config()

if params.commit_message and params.branch and not params.github_token:
    print(red | 'GitHub Token missing, will not be able to create commit.')
    exit(1)


work_dir = Path('/tmp/workspace')

if params.keep_files:
    copytree(github_work_dir, work_dir)
else:
    work_dir.mkdir()
    files = []
    for glob in params.files:
        files.extend(list(github_work_dir.glob(glob)))
    if not params.keep_files:
        for glob in params.keep_files:
            files.extend(list(github_work_dir.glob(glob)))
    for f in files:
        copy(f, work_dir / f.relative_to(github_work_dir))


print('::group::export and tangle')

files = []
for glob in params.files:
    files.extend(list(work_dir.glob(glob)))

if not files:
    print(yellow | 'No files to process')
    print('::endgroup::')
    exit()

print(
    (bblue | str(len(files)))
    + (blue | f" file{'s' if len(files) > 1 else ''} to process: ")
    + ', '.join(map(lambda f: (bblue | str(f.relative_to(work_dir))), files))
)

with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_result = {}
    if params.export:
        future_to_result.update(
            {
                executor.submit(
                    knit.export,
                    f,
                    form,
                    params,
                ): ('exported', f, form)
                for f in files
                for form in params.export
            }
        )
    if params.tangle:
        future_to_result.update(
            {
                executor.submit(knit.tangle, f, params): ('tangled', f, None)
                for f in files
                if params.tangle
                or any(fnmatch(f, glob) for glob in params.tangle)
            }
        )

    for future in concurrent.futures.as_completed(future_to_result):
        action, f, form = future_to_result[future]
        try:
            data = future.result()
        except Exception as exc:
            print(
                (red | ' ✗ ')
                + (bold | str(f.relative_to(work_dir)))
                + ' was not '
                + action
                + (' to ' + (cyan | form) if form else '')
                + '\n   '
                + '\n   '.join([red | line for line in str(exc).split('\n')])
            )
            if params.fragile:
                exit_code = 1
        else:
            print(
                (green | ' ✓ ')
                + (bold | str(f.relative_to(work_dir)))
                + ' '
                + action
                + (' to ' + (cyan | form) if form else '')
                + ' sucessfully'
            )
            if isinstance(data, str) and data != '':
                print(
                    '   '
                    + '\n   '.join(
                        [yellow | line for line in data.split('\n')]
                    )
                )

print('::endgroup::')

if params.commit_message and params.branch:
    print('::group::pushing')
    push.push(work_dir, params)
    print('::endgroup::')

if exit_code == 0:
    print(bgreen | 'Completed')
else:
    print(bred | 'Failed')

exit(exit_code)
