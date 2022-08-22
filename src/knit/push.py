#!/usr/bin/env python3

from os import environ
from pathlib import Path
from subprocess import run

from .colour import blue, green
from .inputs import Inputs


def git_result(work_dir, *args):
    r = run(['git', *args], cwd=work_dir, capture_output=True)
    return r.stdout.decode().strip()


def remote_from_token(params: Inputs):
    # TODO add checks, i.e. is branch prohibited? is repo external?
    return f"https://x-access-token:{params.github_token}@github.com/{environ['GITHUB_REPOSITORY']}.git"


def push(work_dir: Path, params: Inputs):
    def git(*args):
        return run(['git', *args], cwd=work_dir)

    print(blue | f'Configure repository to push to {params.branch}')

    if params.keep_files:
        git('remote', 'rm', 'origin')

    if params.force_orphan:
        run(['rm', '-rf', work_dir.absolute() / '.git'])
        git('init')

    if git('show-ref', '-q', '--heads').returncode != 0:
        git('branch', params.branch)

    git('checkout', params.branch)

    print(blue | 'Add remote, and stage files')

    git('remote', 'add', 'origin', remote_from_token(params))

    git('add', '--all')

    git('config', 'user.name', params.name)
    git('config', 'user.email', params.email)

    message = params.commit_message.replace('!#!', environ['GITHUB_SHA'])
    git('commit', '-m', message)

    print(f'Commited: "{message}"')

    if params.force_orphan:
        git('push', 'origin', '--force', params.branch)
    else:
        git('push', 'origin', params.branch)

    print(green | 'Pushed.')
