# Pushy: A Git-Like Version Control System in Shell

## Overview

**Pushy** is a lightweight, Git-inspired version control system written entirely in POSIX-compliant shell script. It's a minimalist take on Git's core functionality—ideal for learning, experimenting, or version-controlling small projects without the complexity of Git.

## Features

### Repository Management

- `pushy-init`: Initialize a new `.pushy/` repository in the current directory.

### Staging and Committing

- `pushy-add <file>`: Stage a file for commit.
- `pushy-commit -m "<message>"`: Commit staged files with a message.
- `pushy-commit -a -m "<message>"`: Automatically stage tracked files and commit.
- `pushy-log`: View commit history.

### File Inspection

- `pushy-show <commit>:<file>`: View a file from a specific commit or from the index.

### Status and Removal

- `pushy-status`: View file changes (modified, staged, untracked).
- `pushy-rm [--cached|--force] <file>`: Remove a file from the index and/or working directory.

## Example Workflow

```sh
./pushy-init
./pushy-add file.txt
./pushy-commit -m "Add file"
./pushy-branch new-feature
./pushy-checkout new-feature
# make changes...
./pushy-commit -a -m "Update on new-feature"
./pushy-checkout master
./pushy-merge new-feature -m "Merge changes from new-feature"

