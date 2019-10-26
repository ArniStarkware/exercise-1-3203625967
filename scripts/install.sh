#!/bin/bash

set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    python -m virtualenv .env --prompt "[exercise 1] "
    find .env -name site-packages -exec bash -c 'echo "../../../../" > {}/self.pth' \;
    pip install -U pip
    pip install -r requirements.txt
}


main "$@"
