#!/bin/bash
set -e -o pipefail

# sudo chmod +x create_test_branch.sh

git config user.email "lxin42140@gmail.com"

git checkout main
git branch test-branch-1
git checkout test-branch-1
touch hello1.txt
git add .
git commit -a -m "added hello1 file"
git push --set-upstream origin test-branch-1

git branch test-branch-2
git checkout test-branch-2
git push --set-upstream origin test-branch-2

git checkout main
git branch test-branch-3
git checkout test-branch-3
touch hello2.txt
git add .
git commit -a -m "added hello2 file"
git push --set-upstream origin test-branch-3

git checkout main
git merge test-branch-1
git merge test-branch-3