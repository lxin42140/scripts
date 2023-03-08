#!/bin/bash
set -e -o pipefail

# sudo chmod +x create_test_branch.sh

git branch -D test-branch-1
git branch -D test-branch-2
git branch -D test-branch-3

git checkout main
git branch feature/test-branch-1
git checkout feature/test-branch-1
touch hello1.txt
git add .
git commit -a -m "added hello1 file"
git push --set-upstream origin feature/test-branch-1

git checkout main
git merge feature/test-branch-1
