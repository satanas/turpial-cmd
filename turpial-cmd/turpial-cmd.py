# -*- coding: utf-8 -*-

"""Shell interface for Turpial"""
#
# Author: Wil Alvarez (aka Satanas)
# 26 Jun, 2011

import cmd
import sys
import getpass
import logging
import readline
from optparse import OptionParser

from config import ConfigApp
from libturpial.api.core import Core
from libturpial.common import clean_bytecodes, detect_os
from libturpial.common import ColumnType, OS_MAC

try:
    if detect_os() != OS_MAC:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        libc.prctl(15, 'turpial-cmd', 0, 0)
except ImportError:
    pass

INTRO = [
    'Welcome to Turpial (shell mode).', 
    'Type "help" to get a list of available commands.',
    'Type "help <command>" to get a detailed help about that command'
]

ARGUMENTS = {
    'account': ['add', 'edit', 'delete', 'list', 'change', 'default'],
    'status': ['update', 'delete'],
    'profile': ['me', 'user', 'update'],
    'friend': ['list', 'follow', 'unfollow', 'mute', 'unmute'],
    'direct': ['send', 'delete'],
    'favorite': ['mark', 'unmark'],
}

class Turpial(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        
        parser = OptionParser()
        parser.add_option('-d', '--debug', dest='debug', action='store_true',
            help='show debug info in shell during execution', default=False)
        parser.add_option('-m', '--command', dest='command', action='store_true',
            help='execute a single command', default=False)
        parser.add_option('-c', '--clean', dest='clean', action='store_true',
            help='clean all bytecodes', default=False)
        parser.add_option('-s', '--save-credentials', dest='save', action='store_true',
            help='save user credentials', default=False)
        parser.add_option('--version', dest='version', action='store_true',
            help='show the version of Turpial and exit', default=False)
        
        (options, args) = parser.parse_args()
        
        if options.debug or options.clean: 
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        
        self.log = logging.getLogger('Turpial:Cmd')
        #self.config = None
        self.prompt = 'turpial> '
        self.intro = '\n'.join(INTRO)
        self.core = Core()
        self.app_cfg = ConfigApp()
        self.version = self.app_cfg.read('App', 'version')
        
        if options.clean:
            clean_bytecodes(__file__, self.log)
            sys.exit(0)
            
        if options.version:
            print "Turpial (cmd) v%s" % self.version
            print "Python v%X" % sys.hexversion
            sys.exit(0)
        
        self.account = None
        
        try:
            self.cmdloop()
        except EOFError:
            self.do_exit()
    
    def __validate_index(self, index, array, blank=False):
        try:
            a = array[int(index)]
            return True
        except IndexError:
            return False
        except ValueError:
            if blank and index == '':
                return True
            elif not blank and index == '':
                return False
            elif blank and index != '':
                return False
        except TypeError:
            if index is None:
                return False
    
    def __validate_accounts(self):
        if len(self.core.list_accounts()) > 0:
            return True
        print "You don't have any registered account. Run 'account add' command"
        return False
    
    def __validate_default_account(self):
        if self.account:
            return True
        print "You don't have a default account. Run 'account change' command"
        return False
        
    def __validate_arguments(self, arg_array, value):
        if value in arg_array:
            return True
        else:
            print 'Invalid Argument'
            return False
    
    def __build_message_menu(self):
        text = raw_input('Message: ')
        if text == '':
            print 'You must write something to post'
            return None
        
        if len(text) > 140:
            trunc = raw_input ('Your message has more than 140 characters. Do you want truncate it? [Y/n]: ')
            if trunc.lower() == 'y' or trunc == '':
                return text[:140]
            return None
        return text
    
    def __build_accounts_menu(self, _all=False):
        if len(self.core.list_accounts()) == 1: 
            return self.core.list_accounts()[0]
        
        index = None
        while 1:
            accounts = self.__show_accounts()
            if _all:
                index = raw_input('Select account (or Enter for all): ')
            else:
                index = raw_input('Select account: ')
            if not self.__validate_index(index, accounts, _all):
                print "Invalid account"
            else:
                break
        if index == '':
            return ''
        else:
            return accounts[int(index)]
    
    def __build_change_account_menu(self):
        if len(self.core.list_accounts()) == 1:
            if self.account:
                print "Your unique account is already your default"
            else:
                self.__add_first_account_as_default()
        elif len(self.core.list_accounts()) > 1:
            while 1:
                accounts = self.__show_accounts()
                index = raw_input('Select you new default account (or Enter for keep current): ')
                if index == '':
                    print "Default account remain with no changes"
                    return True
                if not self.__validate_index(index, accounts):
                    print "Invalid account"
                else:
                    break
            self.account = accounts[int(index)]
            print "Set %s in %s as your new default account" % (
                self.account.split('-')[0], self.account.split('-')[1])
        
    def __build_protocols_menu(self):
        index = None
        protocols = self.core.list_protocols()
        while 1:
            print "Available protocols:"
            for i in range(len(protocols)):
                print "[%i] %s" % (i, protocols[i])
            index = raw_input('Select protocol: ')
            if not self.__validate_index(index, protocols):
                print "Invalid protocol"
            else:
                break
        return protocols[int(index)]
    
    def __build_confirm_menu(self, message):
        confirm = raw_input(message + ' [y/N]: ')
        if confirm.lower() == 'y':
            return True
        else:
            return False
            
    def __user_input(self, message, blank=False):
        raise NotImplemented
        
    def __add_first_account_as_default(self):
        self.account = self.core.list_accounts()[0]
        print "Selected account %s in %s as default (*)" % (
            self.account.split('-')[0], self.account.split('-')[1])
    
    def __show_accounts(self):
        if len(self.core.list_accounts()) == 0:
            print "There are no registered accounts"
            return
        
        accounts = []
        print "Available accounts:"
        for acc in self.core.list_accounts():
            ch = ''
            if acc == self.account:
                ch = ' (*)'
            print "[%i] %s - %s%s" % (len(accounts), acc.split('-')[0], acc.split('-')[1], ch)
            accounts.append(acc)
        return accounts
        
    def __show_profiles(self, people):
        if people.code > 0: 
            print people.errmsg
            return
        
        for p in people:
            protected = '<protected>' if p.protected else ''
            following = '<following>' if p.following else ''
            
            header = "@%s (%s) %s %s" % (p.username, p.fullname, 
                following, protected)
            print header
            print '-' * len(header)
            print "URL: %s" % p.url
            print "Location: %s" % p.location
            print "Bio: %s" % p.bio
            if p.last_update: 
                print "Last: %s" % p.last_update
            print ''
    
    def __show_statuses(self, statuses):
        if statuses.code > 0:
            print statuses.errmsg
            return
        
        count = 1
        for status in statuses:
            text = status.text.replace('\n', ' ')
            inreply = ''
            if status.in_reply_to_user:
                inreply = ' in reply to %s' % status.in_reply_to_user
            print "%d. @%s: %s" % (count, status.username, text)
            print "%s from %s%s" % (status.datetime, status.source, inreply)
            if status.reposted_by:
                users = ''
                for u in status.reposted_by:
                    users += u + ' '
                print 'Retweeted by %s' % status.reposted_by
            print
            count += 1
    
    def default(self, line):
        print '\n'.join(['Command not found.', INTRO[1], INTRO[2]])
        
    def emptyline(self):
        pass
    
    def do_account(self, arg):
        if not self.__validate_arguments(ARGUMENTS['account'], arg): 
            self.help_account(False)
            return False
        
        if arg == 'add':
            username = raw_input('Username: ')
            password = getpass.unix_getpass('Password: ')
            protocol = self.__build_protocols_menu()
            acc_id = self.core.register_account(username, password, protocol)
            print 'Account added'
            if len(self.core.list_accounts()) == 1: 
                self.__add_first_account_as_default()
        elif arg == 'edit':
            if not self.__validate_default_account(): 
                return False
            password = getpass.unix_getpass('New Password: ')
            username = self.account.split('-')[0]
            protocol = self.account.split('-')[1]
            self.core.register_account(username, password, protocol)
            print 'Account edited'
        elif arg == 'delete':
            if not self.__validate_accounts(): 
                return False
            account = self.__build_accounts_menu()
            conf = self.__build_confirm_menu('Do you want to delete account %s?' %
                account)
            if not conf:
                print 'Command cancelled'
                return False
            self.core.unregister_account(account)
            if self.account == account:
                self.account = None
            print 'Account deleted'
        elif arg == 'change':
            if not self.__validate_accounts():
                return False
            self.__build_change_account_menu()
        elif arg == 'list':
            self.__show_accounts()
        elif arg == 'default':
            print "Default account: %s in %s" % (
                self.account.split('-')[0], self.account.split('-')[1])
    
    def help_account(self, desc=True):
        text = 'Manage user accounts'
        if not desc:
            text = ''
        print '\n'.join([text,
            'Usage: account <arg>\n',
            'Possible arguments are:',
            '  add:\t\t Add a new user account',
            '  edit:\t\t Edit an existing user account',
            '  delete:\t Delete a user account',
            '  list:\t\t Show all registered accounts',
            '  default:\t Show default account',
        ])
    
    def do_login(self, arg):
        if not self.__validate_accounts(): 
            return False
        
        _all = True
        if len(self.core.list_accounts()) > 1:
            _all = self.__build_confirm_menu('Do you want to login with all available accounts?')
        
        if _all:
            for acc in self.core.list_accounts():
                rtn = self.core.login(acc)
                if rtn.code > 0:
                    print rtn.errmsg
                else:
                    print 'Logged in with account %s' % acc.split('-')[0]
        else:
            account = self.__build_accounts_menu()
            rtn = self.core.login(account)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Logged in with account %s' % account.split('-')[0]
    
    def help_login(self):
        print 'Login with one or many accounts'
    
    def do_profile(self, arg):
        if not self.__validate_arguments(ARGUMENTS['profile'], arg): 
            self.help_profile(False)
            return False
        
        if not self.__validate_default_account(): 
            return False
        
        if arg == 'me':
            profile = self.core.get_own_profile(self.account)
            if profile is None:
                print 'You must be logged in'
            else:
                self.__show_profiles(profile)
        elif arg == 'user':
            user = raw_input('Type the username: ')
            if user == '':
                print 'You must specify a username'
                return False
            profile = self.core.get_user_profile(self.account, user)
            if profile is None:
                print 'You must be logged in'
            else:
                self.__show_profiles(profile)
        elif arg == 'update':
            args = {}
            name = raw_input('Type your name (ENTER for none): ')
            bio = raw_input('Type your bio (ENTER for none): ')
            url = raw_input('Type your url (ENTER for none): ')
            location = raw_input('Type your location (ENTER for none): ')
            
            if name != '':
                args['name'] = name
            if bio != '':
                args['description'] = bio
            if url != '':
                args['url'] = url
            if location != '':
                args['location'] = location
            result = self.core.update_profile(self.account, args)
            
            if result.code > 0: 
                print result.errmsg
            else:
                print 'Profile updated'
    
    def help_profile(self, desc=True):
        text = 'Manage user profile'
        if not desc:
            text = ''
        print '\n'.join([text,
            'Usage: profile <arg>\n',
            'Possible arguments are:',
            '  me:\t\t Show own profile',
            '  user:\t\t Show profile for a specific user',
            '  update:\t Update own profile',
        ])
    
    def do_status(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        if not self.__validate_arguments(ARGUMENTS['status'], arg): 
            self.help_status(False)
            return False
        
        if arg == 'update':
            message = self.__build_message_menu()
            if not message:
                print 'You must to write something'
                return False
            
            broadcast = self.__build_confirm_menu('Do you want to post the message in all available accounts?')
            if broadcast:
                for acc in self.core.list_accounts():
                    rtn = self.core.update_status(acc, message)
                    if rtn.code > 0:
                        print rtn.errmsg
                    else:
                        print 'Message posted in account %s' % acc.split('-')[0]
            else:
                rtn = self.core.update_status(self.account, message)
                if rtn.code > 0:
                    print rtn.errmsg
                else:
                    print 'Message posted in account %s' % account.split('-')[0]
        elif arg == 'delete':
            print 'Not implemented'
    
    def help_status(self, desc=True):
        text = 'Manage statuses for each protocol'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: status <arg>\n',
            'Possible arguments are:',
            '  update:\t Update status ',
            '  delete:\t Delete status',
        ])
    
    def do_column(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        lists = self.core.list_columns(self.account)
        if arg == '':
            self.help_column(False)
        elif arg == 'list':
            if len(lists) == 0:
                print "No column available. Maybe you need to login"
                return False
            print "Available columns:"
            for li in lists:
                print "  %s" % li
        elif arg == ColumnType.TIMELINE:
            rtn = self.core.get_column_statuses(self.account, ColumnType.TIMELINE)
            self.__show_statuses(rtn)
        elif arg == ColumnType.REPLIES:
            rtn = self.core.get_column_statuses(self.account, ColumnType.REPLIES)
            self.__show_statuses(rtn)
        elif arg == ColumnType.DIRECTS:
            rtn = self.core.get_column_statuses(self.account, ColumnType.DIRECTS)
            self.__show_statuses(rtn)
        elif arg == ColumnType.FAVORITES:
            rtn = self.core.get_column_statuses(self.account, ColumnType.FAVORITES)
            self.__show_statuses(rtn)
        elif arg == ColumnType.SENT:
            rtn = self.core.get_column_statuses(self.account, ColumnType.SENT)
            self.__show_statuses(rtn)
        else:
            if arg in lists:
                rtn = self.core.get_column_statuses(self.account, arg)
                self.__show_statuses(rtn)
            else:
                print "Invalid column '%s'" % arg
    
    def help_column(self, desc=True):
        text = 'Show user columns'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: column <arg>\n',
            'Possible arguments are:',
            '  list:\t\t List all available columns for that account',
            '  timeline:\t Show timeline',
            '  replies:\t Show replies',
            '  directs:\t Show directs messages',
            '  favs:\t\t Show statuses marked as favorites',
            '  <list_id>:\t Show statuses for the user list with id <list_id>',
        ])
        
    def do_friend(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        if not self.__validate_arguments(ARGUMENTS['friend'], arg): 
            self.help_friend(False)
            return False
        
        if arg == 'list':
            friends = self.core.get_friends(self.account)
            if friends.code > 0:
                print rtn.errmsg
                return False
            
            if len(friends) == 0:
                print "Hey! What's wrong with you? You've no friends"
                return False
            print "Friends list:"
            for fn in friends:
                print "+ @%s (%s)" % (fn.username, fn.fullname)
        elif arg == 'follow':
            user = raw_input('Username: ')
            if user == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.follow(self.account, user)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Following %s" % user
        elif arg == 'unfollow':
            user = raw_input('Username: ')
            if user == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.unfollow(self.account, user)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Not following %s" % user
        elif arg == 'mute':
            print 'Not implemented'
        elif arg == 'unmute':
            print 'Not implemented'
    
    def help_friend(self, desc=True):
        text = 'Manage user friends'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: friend <arg>\n',
            'Possible arguments are:',
            '  list:\t\t List all friends',
            '  follow:\t Follow user',
            '  unfollow:\t Unfollow friend',
            '  mute:\t\t Put a friend into the silence box',
            '  unmute:\t Get out a friend from the silence box',
        ])
        
    '''
    def do_search(self, args):
        args = args.split()
        if len(args) < 2: 
            self.help_search()
            return
        stype = args[0]
        query = args[1]
        
        if stype == 'people':
            self.show_profile(self.controller.search_people(query))
        
    def do_fav(self, number):
        twid = self.get_tweet_id(number)
        if twid is None:
            print 'No se puede localizar el mensaje seleccionado'
            print 'El mensaje NO fue marcado.'
            return
        self.controller.set_favorite(twid)
        
    def do_unfav(self, number):
        twid = self.get_tweet_id(number)
        if twid is None:
            print 'No se puede localizar el mensaje seleccionado'
            print 'El mensaje NO fue desmarcado.'
            return
        self.controller.unset_favorite(twid)
        
    def do_direct(self, line):
        if len(line.split()) < 2: 
            self.help_direct()
            return
        user = line.split()[0]
        message = line.replace(user + ' ', '')
        if not self.validate_message(message):
            print u'NO se envió ningun mensaje.'
            return
        self.controller.send_direct(user, message)
        
    def do_short(self, url):
        self.controller.short_url(url, self.show_shorten_url)
    '''
    def do_EOF(self, line):
        return self.do_exit('')
        
    def do_exit(self, line=None):
        print
        self.log.debug('Bye')
        return True
    
    def help_help(self):
        print 'Show help. Dah!'
        
    def help_exit(self):
        print 'Close the application'
    
    def help_EOF(self):
        print 'Close the application'
    
    def show_trends(self, trends):
        topten = ''
        for t in trends['trends']:
            topten += t['name'] + '  '
        print topten
        
    def show_following(self, people):
        total = len(people)
        self.show_profile(people)
        if total > 1: suffix = 'personas' 
        else: suffix = 'persona'
        print "Estas siguiendo a %d %s" % (total, suffix)
        
    def show_followers(self, people):
        total = len(people)
        self.show_profile(people)
        if total > 1: suffix = 'personas' 
        else: suffix = 'persona'
        print "Te siguen %d %s" % (total, suffix)
        
    def show_shorten_url(self, text):
        print "URL Cortada:", text

if __name__ == "__main__":
    t = Turpial()
