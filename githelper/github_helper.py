#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#--------------------------------------------------------------
#
# helper to print out recent activities of multiple github accounts
# Similar to contribution counted by github, but exclude issues
#
# Assumes you save your user, ps in local file 'ps.txt', 'ps2.txt'
# use: python github_merger.py
#
#--------------------------------------------------------------
#

import sys
import pytz
import tzlocal
import github
import getpass
import logging
import argparse
import time
from collections import Counter, OrderedDict
from datetime import date, timedelta, datetime

__version__ = "0.0.1"
__version_info__ = __version__.split('.')

#--------------------------------------------------------------
# Global Constants & Vars
#--------------------------------------------------------------
DEBUG = False
START = datetime(2015, 8, 30)
#--------------------------------------------------------------
# Global Functions
#--------------------------------------------------------------
_local = tzlocal.get_localzone()

def _e(val):
    if isinstance(val, unicode):
        return val.encode('utf8')
    return val

def _local_time(tt):
    """ github created_at time was naive
    change to tz aware, and format nicely
    """
    aware = pytz.utc.localize(tt)
    return aware.astimezone(_local).strftime('%Y-%m-%d %I:%M %p')

def _d2s(date_obj, format = '%Y-%m-%d'):
    """ date object to time"""
    aware = pytz.utc.localize(date_obj)
    return aware.astimezone(_local).strftime(format)

def _s2d(date_str, format = '%Y-%m-%d'):
    """ from string to date object"""
    return datetime.strptime(date_str, format)

def _log(msg, msg_type='info'):
    print ('[%s] %s' % (msg_type, msg)).encode('utf8')

def print_dict(d):
    for k,v in d.iter():
        print '%-15s: %s' %k, v

# Helper functions

def commit_header(string):
    """first line of commit msg"""
    return string.split('\n')[0] if string else ''

def commit_info(commit):
    """ date, author and header of commit msg"""
    if type(commit) == github.Commit.Commit:
        return _d2s(commit.commit.author.date), \
                commit.author.login, \
                commit_header(commit.commit.message), \
                'commit'

def issue_info(issue):
    """ date, creater and title of issue"""
    if type(issue) == github.Issue.Issue:
        return _d2s(issue.created_at), \
               issue.user.login, \
               issue.title, \
               'issue'

def filter_date(time_obj, year=None, month=None, day = None):
    """filter by year, month date of time_obj"""
    m_year = year is None or time_obj.tm_year == year
    m_month = month is None or time_obj.tm_mon == month
    m_day = day is None or time_obj.tm_mday == day
    return m_year and m_month and m_day

def filter_msg(msg):
    """only allow commits with certain msg signature"""
    merge = msg.startswith("Merge branch")
    readme = 'readme' in msg.lower()
    # return (not merge) and (not readme)
    return not merge


def counts_to_clog(counts):
    """
    take a Count() dict: {date_str: count}
    turn into contribution log of to feed into streak
    """
    dates = counts.keys()
    start, end = max(START, _s2d(min(dates))), _s2d(max(dates))
    datei = start
    c_log = OrderedDict()
    while datei <= end:
        if DEBUG: print '%s: %s contributions'% (_d2s(datei), counts.get(_d2s(datei), 0))
        c_log[_d2s(datei)] = counts.get(_d2s(datei), 0)
        datei += timedelta(days=1)
    return c_log

def streak(contribution_lst):
    """
    find current and longest streak
    @contribution_lst: [0, 0, 13, 0, 3, 2, 0,1,2,1,1,0,0,10,1,2]
    """
    curr_streak, longest_streak = 0, 0
    for n in contribution_lst:
        if n == 0:
            curr_streak = 0
        else:
            curr_streak += 1
            if curr_streak > longest_streak:
                longest_streak = curr_streak
        if DEBUG: print 'curr = %s, curr_streak = %s, longest_streak = %s' %(n, curr_streak, longest_streak)
    return curr_streak, longest_streak


#--------------------------------------------------------------
# Classes
#--------------------------------------------------------------
class GitHelper(object):
    """login with user,ps in ps.txt
    if doesn't exist, prompt user to input
    save to ps.txt optionally
    """
    def __init__(self, filename):
        self.FILENAME = filename
        self.tryLogin()
        self.contributions = self.load_commits() + self.load_issues()
        if DEBUG: _log('%s contributions loaded for %s' % (len(self.contributions), self.USER), 'Info')
        self.by_day = Counter()
        self.daily_log = OrderedDict()


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
                _log('Login as %s: Success!' %self.USER, 'Info')
                if wronginfo:
                    self.saveUserPass()
                break
            except Exception as e:
                _log(e, 'Error')
                self.livePrompt()
                wronginfo = True

    def load_commits(self):
        return [tuple([repo.name]+list(commit_info(commit)))
              for repo in self.g.get_user().get_repos()
              if repo.size > 0
              for commit in repo.get_commits(author=self.USER)
              if filter_msg(_e(commit_header(commit.commit.message)))]

    def load_issues(self):
        return [tuple([repo.name]+list(issue_info(issue)))
              for repo in self.g.get_user().get_repos()
              if repo.size > 0
              for issue in repo.get_issues()
              if issue.user.login == self.USER]

    def count_contributions_by_day(self):
        for repo, date_str, author, title, ctype in self.contributions:
            self.by_day[date_str] += 1

    def counts_to_clog(self):
        self.daily_log = counts_to_clog(self.by_day)

    def longest_streak(self):
        self.curr_streak, self.longest_streak = streak(self.daily_log.values())

    def show(self):
        if DEBUG:
            for c in self.contributions:
                print c
        print '--------------- %s: total %s contributions ------------' % (self.USER, len(self.contributions))
        print '--------------- count by day ----------------'
        print self.by_day
        print '--------------- counts to contribution log --------'
        print self.daily_log
        print 'current streak = %s, longest streak = %s' %(self.curr_streak, self.longest_streak)

    def tabulate(self):
        self.count_contributions_by_day()
        self.counts_to_clog()
        self.longest_streak()
        # self.show()

class GitMerger(GitHelper):

    def __init__(self, filenames):
        self.FILENAME = filenames
        self.contributions = []
        self.USER = []
        self.by_day = Counter()
        self.daily_log = OrderedDict()

    def merge(self):
        for f in self.FILENAME:
            acc = GitHelper(f)
            self.USER.append(acc.USER)
            self.contributions += acc.contributions




#--------------------------------------------------------------
# Entry
#--------------------------------------------------------------

def main():
    accounts = ['ps1.txt', 'ps2.txt']
    # g=GitHelper(accounts[0])
    # g.tabulate()
    # g.go()
    merger = GitMerger(accounts)
    merger.merge()
    merger.tabulate()
    merger.show()

if __name__ == '__main__':
    main()





