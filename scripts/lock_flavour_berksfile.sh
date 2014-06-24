#!/bin/sh
# ############################################################
# Locks the flavour of a berksfile if there isn\t one.
# generates a berksfile
# pulls the latest git commit version from the master branch of
# the cookbook repositories.
# if your flavour berksfile exists it will only look at the
# cookbooks on the flavour berksfile and will ignore the default
# one, so no new cookbooks will be added, but all the patches
# and additional changes will be taken into account
# (if you run this that is)
#
#USAGE: sh lock_flavour_berksfile.sh nexus
#
# Author dario.more@telegraph.co.uk
# Date 24/Apr/2014
##############################################################

[ "$1" = "" ] && echo "usage: $0 <flavour>" && exit 1

#pulls a list of git repositories to grab the commit tags from
INPUT_FILE=../config/default.berksfile
FLAVOUR=$1
FLAVOURED_BERKS_FILE=../config/$1.berksfile
echo "checking for berksfile $FLAVOURED_BERKS_FILE"
if [ -f $FLAVOURED_BERKS_FILE ];
then
   echo "detected $FLAVOURED_BERKS_FILE"
else
   sudo cp $INPUT_FILE $FLAVOURED_BERKS_FILE
   echo "created $FLAVOURED_BERKS_FILE"
fi

sudo rm -rf "$FLAVOURED_BERKS_FILE.tmp"

cat $FLAVOURED_BERKS_FILE | while read LINE; do
    echo "line $LINE"
    GIT_REPO=$(echo $LINE | grep git | awk -F':git =>' '{print $2}')
    GIT_REF=$(echo $LINE | grep git | awk -F':ref =>' '{print $2}')
    #GIT_BRANCH=$(echo $LINE | grep git | awk -F':branch =>' '{print $2}')
    GIT_REPO=$(echo ${GIT_REPO%%,*})
    COOKBOOK=$(echo $LINE | grep git | awk -F', :git =>' '{print $1}' | sed -e "s/cookbook//g")
    echo "git repo=$GIT_REPO"
    echo "cookbook=$COOKBOOK"
    echo "file=$FLAVOURED_BERKS_FILE"
    sh refresh_cookbook_tag.sh $GIT_REPO $COOKBOOK $FLAVOURED_BERKS_FILE $GIT_REF
done

cat "$FLAVOURED_BERKS_FILE"
echo "flavoured file created/updated with latest tags for its cookbooks"