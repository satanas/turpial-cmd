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
from libturpial.common import clean_bytecodes, ColumnType

try:
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
    'show': ['accounts', 'timeline', 'replies', 'directs', 'sent', 'favs',
        'rates', 'trends', 'following', 'followers', 'myprofile', 'userprofile']
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
        print "You don't have any registered account. Run add_account command"
        return False
        
    def __validate_arguments(self, arg_array, value):
        if value in arg_array:
            return True
        else:
            print 'Argument invalid'
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
            accounts = []
            print "Available accounts:"
            for acc in self.core.list_accounts():
                print "[%i] %s - %s" % (len(accounts), acc.split('-')[0], acc.split('-')[1])
                accounts.append(acc)
            if _all:
                index = raw_input('Select one account (or Enter for all): ')
            else:
                index = raw_input('Select one account: ')
            if not self.__validate_index(index, accounts, _all):
                print "Invalid account"
            else:
                break
        if index == '':
            return ''
        else:
            return accounts[int(index)]
            
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
    
    def default(self, line):
        print '\n'.join(['Comando no encontrado.', INTRO[1], INTRO[2]])
        
    def emptyline(self):
        pass
    
    def do_add_account(self, arg):
        username = raw_input('Username: ')
        password = getpass.unix_getpass('Password: ')
        protocol = self.__build_protocols_menu()
        acc_id = self.core.register_account(username, password, protocol)
        print 'Account added'
        
    def do_edit_account(self, arg):
        if not self.__validate_accounts(): return False
        account = self.__build_accounts_menu()
        password = getpass.unix_getpass('New Password: ')
        username = account.split('-')[0]
        protocol = account.split('-')[1]
        self.core.register_account(username, password, protocol)
        print 'Account edited'
        
    def do_login(self, arg):
        if not self.__validate_accounts(): return False
        account = self.__build_accounts_menu(True)
        if account == '':
            for acc in self.core.list_accounts():
                rtn = self.core.login(acc)
                if rtn.code > 0:
                    print rtn.errmsg
                else:
                    print 'Logged in with account %s' % acc.split('-')[0]
        else:
            rtn = self.core.login(account)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Logged in with account %s' % account.split('-')[0]
            
    def do_show(self, arg):
        if arg == 'accounts':
            self.show_accounts()
            return
        
        if not self.__validate_accounts(): return False
        if not self.__validate_arguments(ARGUMENTS['show'], arg): 
            self.help_show()
            return False
        
        account = self.__build_accounts_menu()
        if arg == 'timeline':
            rtn = self.core.get_column_statuses(account, ColumnType.TIMELINE)
            self.show_statuses(rtn)
        elif arg == 'replies':
            rtn = self.core.get_column_statuses(account, ColumnType.REPLIES)
            self.show_statuses(rtn)
        elif arg == 'directs':
            rtn = self.core.get_column_statuses(account, ColumnType.DIRECTS)
            self.show_statuses(rtn)
        elif arg == 'sent':
            rtn = self.core.get_column_statuses(account, ColumnType.SENT)
            self.show_statuses(rtn)
        elif arg == 'favorites':
            rtn = self.core.get_column_statuses(account, ColumnType.FAVORITES)
            self.show_statuses(rtn)
        elif arg == 'myprofile':
            rtn = self.core.get_own_profile(account)
            self.show_profiles(rtn)
        elif arg == 'userprofile':
            user = raw_input('Username: ')
            rtn = self.core.get_user_profile(account, user)
            self.show_profiles(rtn)
        #elif arg == 'following':
        #    self.show_profiles(self.controller.get_following())
        #elif arg == 'followers':
        #    self.show_followers(self.controller.get_followers())
        #elif arg == 'trends':
        #    self.show_trends(self.controller.get_trends())
        #elif arg == 'rates':
        #    self.show_rate_limits()
        else:
            self.default('')
        
    def do_search(self, args):
        args = args.split()
        if len(args) < 2: 
            self.help_search()
            return
        stype = args[0]
        query = args[1]
        
        if stype == 'people':
            self.show_profile(self.controller.search_people(query))
        
    def do_post(self, status):
        if not self.__validate_accounts(): return False
        message = self.__build_message_menu()
        if not message: return False
        
        account = self.__build_accounts_menu(True)
        if account == '':
            for acc in self.core.list_accounts():
                rtn = self.core.update_status(acc, message)
                if rtn.code > 0:
                    print rtn.errmsg
                else:
                    print 'Message posted in account %s' % acc.split('-')[0]
        else:
            rtn = self.core.update_status(account, message)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Message posted in account %s' % account.split('-')[0]
                
    def do_follow(self, user):
        self.controller.follow(user)
        
    def do_unfollow(self, user):
        self.controller.unfollow(user)
    '''
    def do_update(self, args):
        if len(args.split()) < 2: 
            self.help_update()
            return
        field = args.split()[0]
        value = args.replace(field + ' ', '')
        
        if field == 'bio':
            if not self.validate_message(value, 160):
                print u'NO se actualizó la bio.'
                return
            self.controller.update_profile(new_bio=value)
        elif field == 'location':
            if not self.validate_message(value, 30):
                print u'NO se actualizó la ubicacion.'
                return
            self.controller.update_profile(new_location=value)
        elif field == 'url':
            if not self.validate_message(value, 100):
                print u'NO se actualizó la URL.'
                return
            self.controller.update_profile(new_url=value)
        elif field == 'name':
            if not self.validate_message(value, 20):
                print u'NO se actualizó el nombre.'
                return
            self.controller.update_profile(new_name=value)
            
    def do_delete(self, number):
        twid = self.get_tweet_id(number)
        if twid is None:
            print 'No se puede localizar el mensaje seleccionado'
            print 'El mensaje NO fue borrado.'
            return
        self.controller.destroy_status(twid)
        
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
        
    def do_mute(self, user):
        self.controller.mute(user)
        
    def do_unmute(self, user):
        self.controller.unmute(user)
        
    def do_short(self, url):
        self.controller.short_url(url, self.show_shorten_url)
    '''
    def do_EOF(self, line):
        return self.do_exit('')
        
    def do_exit(self, line):
        print
        self.log.debug('Bye')
        return True
        
    def help_show(self):
        print '\n'.join(['Muestra los distintos mensajes del usuario',
            'show <arg>',
            '  <arg>: Lo que se desea ver. Valores posibles: tweets, ' \
            'replies, directs, favs, rates, trends, profile, following, ' \
            'followers',
        ])
        
    def help_search(self):
        print '\n'.join(['Ejecuta una busqueda en Twitter',
            'search <type> <query>',
            u'  <type>: Tipo de búsqueda a realizar. Valores ' \
                'posibles: people',
            '  <query>: La cadena que se desea buscar'
        ])
        
    def help_direct(self):
        print '\n'.join([u'Envía un mensaje directo a un usuario',
            'direct <user> <message>',
            '  <user>: Nombre del usuario. Ej: pedroperez',
            '  <message>: Mensaje que se desea enviar'
        ])
        
    def help_update(self):
        print '\n'.join(['Actualiza datos del usuario',
            'update <field> <value>',
            '  <field>: Campo que se desea actualizar. Valores ' \
                'posibles: bio, location, url, name',
            '  <value>: El nuevo valor para el campo seleccionado'
        ])
    
    def help_delete(self):
        print '\n'.join(['Borra un estado (tweet)',
            'delete <num>',
            u'  <num>: Número en pantalla del estado (tweet) que desea borrar',
        ])
        
    def help_fav(self):
        print '\n'.join(['Marca un estado (tweet) como favorito',
            'fav <num>',
            u'  <num>: Número en pantalla del estado (tweet) que desea marcar',
        ])
        
    def help_unfav(self):
        print '\n'.join(['Desmarca un estado (tweet) de los favoritos',
            'unfav <num>',
            u'  <num>: Número en pantalla del estado (tweet) que desea desmarcar',
        ])
        
    def help_tweet(self):
        print '\n'.join(['Actualiza el estado del usuario',
            'tweet <message>',
            '  <message>: Mensaje que desea postear',
        ])
        
    def help_follow(self):
        print '\n'.join(['Seguir a una persona',
            'follow <user>',
            '  <user>: Persona a la que desea seguir',
        ])
        
    def help_unfollow(self):
        print '\n'.join(['Dejar de seguir a una persona',
            'unfollow <user>',
            '  <user>: Persona que ya no se desea seguir',
        ])
        
    def help_mute(self):
        print '\n'.join(['Silencia los mensajes de una persona sin bloquearla',
            'mute <user>',
            '  <user>: Persona a la que se desea silenciar',
        ])
        
    def help_unmute(self):
        print '\n'.join(['Visualiza los mensajes de una persona previamente silenciada',
            'unmute <user>',
            '  <user>: Persona cuyos mensajes se desean leer de nuevo',
        ])
        
    def help_short(self):
        print '\n'.join(['Corta una URL con el servicio seleccionado en las preferencias de usuario',
            'short <url>',
            '  <url>: URL que se desea cortar',
        ])
        
    def help_help(self):
        print 'Muestra la ayuda'
        
    def help_exit(self):
        print 'Salir de Turpial'
    
    def help_EOF(self):
        print 'Salir de Turpial'
        
    def get_tweet_id(self, num):
        if num == '': return None
        
        num = int(num) - 1
        arr = self.controller.tweets[:]
        arr.reverse()
        if (num < 1) or (num > len(arr)): return None
        
        return arr[num]['id']
        
    def show_accounts(self):
        print "Available accounts:"
        for acc in self.core.list_accounts():
            print "* %s - %s" % (acc.split('-')[0], acc.split('-')[1])
        
    def show_statuses(self, statuses):
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
    
    def show_trends(self, trends):
        topten = ''
        for t in trends['trends']:
            topten += t['name'] + '  '
        print topten
            
    def show_profiles(self, people):
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
                print "Last: %s\n" % p.last_update
        
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
