
## Update database

You may need:

    source vir/bin/activate
    cd migrations

Create new revision

    alembic revision --autogenerate -m "Message"

Check if the generated file is correct.

    alembic upgrade head

## Init translations

You may need:

    source vir/bin/activate

In the applications folder

    pybabel extract -F babel.cfg -o messages.pot .

    pybabel init -i messages.pot -d translations -l de

    pybabel compile -d translations

## Update translations

You may need:

    source vir/bin/activate

Then in folder `applications` type:

    pybabel extract -F babel.cfg -o messages.pot .

    pybabel update -i messages.pot -d translations

Do the actual translation, then

    pybabel compile -d translations

## Main views

### Global

  - new G/P
  - home
  - profile

### Project

  - project
  - pdf

### Branch

  - branch
  - clone G/P
  - newfile G/P
  - requests
  - finish
  - view
  - edit G/P
  - commit G/P
  - merge
  - review G/P
  - diff
  - accept

## States of a branch

### Clean (not dirty)

  - `is_dirty` evaluates to `False`
  - no `merging` file
  - if has requests, all views will write: You have unreviewed requests!!!
  - can access views:
    - branch
    - clone
    - newfile P/G (Post will make the branch dirty)
    - requests (can be empty)
    - view
    - edit G/P (Post will make the branch dirty)
    - commit G/P (Post will make an empty commit, which works fine as a request)
    - merge (other)
      - if other has no requests, redirects to view with: other has no requests now
      - otherwise goes to state merging (other)
    - finish, review, diff, accept (redirects to view with: you are not merging)

### Dirty

  - `is_dirty` evaluates to `True`
  - no `merging` file
  - if has requests, does NOT show: You have unreviewed requests!!!
  - all views will write: You have uncommitted changes!!!
  - can access views:
    - branch
    - clone
    - newfile P/G
    - requests (redirects to branch with: Commit your changes before reviewing requests)
    - view
    - edit G/P
    - commit G/P (Post will commit and clean)
    - merge (redirects to branch with: Commit your changes before reviewing requests)
    - finish, review, diff, accept (redirects to view with: you are not merging)

### Merging

  - `is_dirty` evaluates to `True`
  - `merging` file
  - can access views:
    - branch, clone, newfile P/G, view, edit G/P, commit G/P
      all of these redirect to merge
    - merge (shows merging)
    - review G/P (Post redirects to accept)
    - diff
    - accept (removes one file from modified)
    - finish (if no more unreviewed, cleans branch)

## Routine of each view

  - new G/P: check unique name, create
  - branch: check owner, if owner check merge pendencies, show branch
  - clone G/P: check merge pendencies, clone (create branch, setup parent)
  - newfile G/P: check merge pendencies, check owner, check unique name, create file, add file
  - requests: check owner, check dirty, show requests
  - finish: check owner, check if merging, check unreviewed, commit merge, push up, push down
  - view: check owner, check merge pendencies, view
  - edit G/P: check owner, check merge pendencies, edit/save and add
  - commit G/P: check owner, check if merging, push up, push down
  - merge: if not merging start merging, show files
  - review G/P: check owner, check if not merging, save and add
  - diff: check owner, check if not merging, show diff
  - accept: check owner, check if not merging, save and add

## Actions that interfere with other branches

  - commit (send request to origin, propagate changes to subtree)
  - finish merge (send request to origin, propagate changes to subtree)

## Code style

  - indent always by 2 spaces.
