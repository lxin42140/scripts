#!/bin/bash
set -e -o pipefail

# sudo chmod +x create_test_branch.sh

git branch -D feature/test-branch-1

git checkout main
git branch test-branch-1
git checkout test-branch-1
touch hello1.txt
git add .
git commit -a -m "added hello1 file"
git push --set-upstream origin test-branch-1

git checkout main
git merge test-branch-1
