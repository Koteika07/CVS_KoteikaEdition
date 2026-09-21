"""CLI-интерфейс: argparse-команды (init, add, commit, checkout, log, branch, tag)"""

import argparse
import sys
from .repo import Repository


def main():
    parser = argparse.ArgumentParser(prog='cvs', description='CVS Koteika - Simple Version Control System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init
    subparsers.add_parser('init', help='Initialize a new repository')

    # add
    p_add = subparsers.add_parser('add', help='Add file contents to the index')
    p_add.add_argument('paths', nargs='+', help='Files or directories to add')

    # commit
    p_commit = subparsers.add_parser('commit', help='Record changes to the repository')
    p_commit.add_argument('-m', '--message', required=True, help='Commit message')

    # checkout
    p_checkout = subparsers.add_parser('checkout', help='Switch branches or restore working tree files')
    p_checkout.add_argument('target', help='Branch, tag, or commit SHA')

    # log
    subparsers.add_parser('log', help='Show commit logs')

    # branch
    p_branch = subparsers.add_parser('branch', help='Create a new branch')
    p_branch.add_argument('name', help='Branch name')

    # tag
    p_tag = subparsers.add_parser('tag', help='Create a new tag')
    p_tag.add_argument('name', help='Tag name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # команда init не требует существующего репозитория
    if args.command == 'init':
        Repository().init()
        return

    # для остальных команд репозиторий должен быть инициализирован
    try:
        repo = Repository()
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # маршрутизация команд
    if args.command == 'add':
        repo.add(args.paths)
    elif args.command == 'commit':
        repo.commit(args.message)
    elif args.command == 'checkout':
        repo.checkout(args.target)
    elif args.command == 'log':
        repo.log()
    elif args.command == 'branch':
        repo.branch(args.name)
    elif args.command == 'tag':
        repo.tag(args.name)
