#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#--------------------------------------------------------------
#
# Instant
#               -- Go abroad for further study & grow
#
# helper to print out recent activities of team members
# including current milestone open issues,
# all recent closed issues, recent commits
# first command line parameter is user name
# checks by prefix of user name and return first match
# if no parameter, then print unassigned issues in current milestone
#
# Assumes you save your user, ps in local file 'ps.txt'
# use: python github_helper.py appledore
#
#--------------------------------------------------------------
#
# Date:     2015-11-01
#
# Author:   1p3akproduct@gmail.com
#

import sys
import pytz
import tzlocal
import github
import getpass
import logging
import argparse

__version__ = "0.0.1"
__version_info__ = __version__.split('.')

#--------------------------------------------------------------
# Global Constants & Vars
#--------------------------------------------------------------

REPO = 'Chipmunk'
NUM_ISSUES = 50

#--------------------------------------------------------------
# Global Functions
#--------------------------------------------------------------
_local = tzlocal.get_localzone()

def _local_time(tt):
    """ github created_at time was naive
    change to tz aware, and format nicely
    """
    aware = pytz.utc.localize(tt)
    return aware.astimezone(_local).strftime('%Y-%m-%d %I:%M %p')

def _log(msg, msg_type='info'):
    print ('[%s] %s' % (msg_type, msg)).encode('utf8')

#--------------------------------------------------------------
# Classes
#--------------------------------------------------------------
class GitLogin(object):
    """login with user,ps in ps.txt
    if doesn't exist, prompt user to input
    save to ps.txt optionally
    """
    def __init__(self):
        self.FILENAME = 'ps.txt'
        self.tryLogin()

    def loadFromFile(self):
        _log('Trying to load USER, PASSWORD from %s...' %self.FILENAME, 'Info')
        with open(self.FILENAME, 'rb') as f:
            self.USER, self.PASSWORD = f.readline().strip().split(',')

    def livePrompt(self):
        self.USER = raw_input('Your github login:')
        self.PASSWORD = getpass.getpass(prompt='Password:')

    def saveUserPass(self):
        with open(self.FILENAME, 'w') as f:
            f.write(','.join([self.USER, self.PASSWORD]))
        _log('saved to %s' %self.FILENAME, 'Info')

    def tryLogin(self):
        wronginfo = False
        try:
            self.loadFromFile()
        except:
            pass
        while True:
            try:
                self.g = github.Github(self.USER, self.PASSWORD)
                _log('Login Success!', 'Info')
                if wronginfo:
                    self.saveUserPass()
                break
            except Exception as e:
                _log(e, 'Error')
                self.livePrompt()
                wronginfo = True


class GitHelper(GitLogin):

    def __init__(self):
        GitLogin.__init__(self)
        self.repo = [repo for repo in self.g.get_user().get_repos() if repo.name == REPO].pop()
        self.team = self.repo.get_assignees()
        self.issues = self.repo.get_issues()
        self.closed_issues = self.repo.get_issues(state='closed')
        self.milestones = self.repo.get_milestones()

    def getTeam(self):
        print '\nTeam members are:\n'
        for each in self.team:
            print '     %-18s %-18s' %(each.login or '', each.name or '')

    def getMember(self, input_user):
        if not input_user:
            return
        check_user = str(input_user).lower()
        for each in self.team:
            if str(each.login).lower().startswith(check_user) or str(each.name).lower().startswith(check_user):
                return each


    def formatIssue(self, issue):
        return '    %s#%-3s %-50s   %s' %(
            '%s  By: %-18s ' % (_local_time(issue.closed_at), issue.closed_by.login) if issue.closed_at else '',
            issue.number,
            issue.title,
            ', '.join(['<%s>' % l.name for l in issue.labels]))


    def getUserOpenIssues(self, user):
        formatted_issues = [self.formatIssue(issue)
            for issue in self.repo.get_issues(
                milestone = self.milestone,
                assignee=user,
                state='open')]
        if formatted_issues:
            print '\n## Open Issues: %s' % len(formatted_issues)
            for i in formatted_issues:
                print i
        else:
            print '\n## No Open Issues.'


    def getUserClosedIssues(self, user):
        print '\n## Recently Closed Issues:'
        formatted_issues = [self.formatIssue(issue)
            for issue in self.closed_issues[:NUM_ISSUES]
            if issue.assignee
            if issue.assignee.login.lower() == user.login.lower()
            if issue.state == 'closed']
        for i in formatted_issues:
            print i


    def getUserRecentCommits(self, n=15, **kargs):
        print '\n## Recent commits:'
        user_commits = self.repo.get_commits(**kargs)
        for commit in user_commits[:n]:
            try:
                print '    %s  By: %-18s %s' %(
                    _local_time(commit.get_statuses()[0].created_at),
                    commit.author.login,
                    commit.commit.message.split('\n').pop(0)[:80])
            except:
                print '    sth wrong~~~'


    def listMilestones(self):
        for m in self.milestones:
            print '       %-20s [Due on: %s] Open: %-3s Closed: %-s' % \
                (m.title,
                 _local_time(m.due_on),
                 m.open_issues,
                 m.closed_issues)


    def getOverview(self, input_user=None, i_milestone=0):
        user = self.getMember(input_user)
        self.milestone = self.milestones[i_milestone]

        self.listMilestones()

        if user:
            print '\n%s -> %s, %s @ %s [Due on: %s]' % (
                input_user,
                user.login,
                user.name or '',
                self.milestones[i_milestone].title,
                _local_time(self.milestone.due_on))
            self.getUserOpenIssues(user)
            self.getUserClosedIssues(user)
            self.getUserRecentCommits(author=user)
        else:
            self.getTeam()
            print '\n==========================\nUnassigned @ %s [Due on: %s]' % (self.milestone.title, _local_time(self.milestone.due_on))
            self.getUserOpenIssues(github.GithubObject.NotSet)

            for member in self.team:
                print '\n==========================\n>>>>>> %s, %s' % (member.login or '', member.name or '')
                self.getUserOpenIssues(member)

            self.getUserRecentCommits(n=30)


#--------------------------------------------------------------
# Entry
#--------------------------------------------------------------

def get_arg():
    """ arg parser """
    parser = argparse.ArgumentParser(
        description="quick list of who's working on what Github Chipmunk.")
    parser.add_argument('-u', '--user', default=None, help="allows prefix match")
    parser.add_argument('-m', '--milestone', type=int, default=0, help="0-current milestone, 1-next milestone, etc. Larger number than available milestone is ignored.")

    args = parser.parse_args()
    print args.__dict__
    return args

def main():
    args = get_arg()
    githelper = GitHelper()
    githelper.getOverview(args.user, args.milestone)


if __name__ == '__main__':
    main()





