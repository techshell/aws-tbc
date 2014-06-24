#!/bin/sh
# ############################################################
# grabs the latest commit tag for a cookbook and updates
# the tags on a flavour berksfile.
# This is used by lock_flavour_berksfile only.
# Author dario.more@telegraph.co.uk
# Date 24/Apr/2014
##############################################################

GIT_REPO=$(echo $1 | sed -e "s/'//g")
COOKBOOK=$2
FLAVOURED_BERKS_FILE=$3
OLD_COMMIT_TAG=$(echo $4 | sed -e "s/'//g")

echo "berksfile :$FLAVOURED_BERKS_FILE"
tmpdir=`mktemp -d /tmp/git-tmp.XXXXXX` || exit 1
echo "temp dir: $tmpdir"

pushd "$tmpdir" || exit 1

git clone --depth=1 -n $GIT_REPO .

#pick the cookbook commit tag
COMMIT_TAG=$(git rev-parse HEAD)
echo "commit tag=$COMMIT_TAG"

#a
popd

#aim to find the line on the flavoured file for this cookbook, otherwise we add it twice...
COOKBOOK_CHECK=$(cat $FLAVOURED_BERKS_FILE | grep $COOKBOOK)

echo "cookbook check: $COOKBOOK_CHECK"
echo "old commit tag: $OLD_COMMIT_TAG"
echo "new commit tag: $COMMIT_TAG"

if [ -n "$COOKBOOK_CHECK" ]
then
    echo "cookbook found, s/$OLD_COMMIT_TAG/$COMMIT_TAG/g $FLAVOURED_BERKS_FILE"
    cat $FLAVOURED_BERKS_FILE | sed -e s/"$OLD_COMMIT_TAG"/"$COMMIT_TAG"/g > "$FLAVOURED_BERKS_FILE.tmp"
    sudo cp $FLAVOURED_BERKS_FILE.tmp $FLAVOURED_BERKS_FILE
    sudo rm $FLAVOURED_BERKS_FILE.tmp
else
    #add new line to the flavoured file when is new.
    echo "cookbook $COOKBOOK, :git => '$GIT_REPO', :ref => '$COMMIT_TAG'" >> $FLAVOURED_BERKS_FILE
fi

# delete tmp dir
rm -rf "$tmpdir"