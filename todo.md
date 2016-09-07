  - make sure usernames are alphanumeric only
  - automate test using pytest
  - enable debugger only on localhost
  - remove specific configurations from conf/conf.py, they should go to toml and be imported



```
mkdir test
cd test/
git init
echo "master" > a
git add .
git commit -m "master init"
git checkout -b feature
echo "feature" > a
git commit -am "feature"
git checkout master
echo "master is better" > a
git commit -am "master commit"
git merge --no-commit -s recursive -X theirs feature
git reset HEAD *
cat a
git show master:a
echo "master also has feature now" > a
git add .
git commit -m "Merge"
cat a
git tree
git checkout feature
git merge master
git checkout master
git branch -d feature
```
