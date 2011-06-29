# -*- coding: utf-8 -*-

"""Module to handle app configuration of turpial-cmd"""
#
# Author: Wil Alvarez (aka Satanas)
# Jun 26, 2011

import os

from libturpial.config import ConfigBase, GLOBAL_CFG

CMD_CFG = GLOBAL_CFG
CMD_CFG['App']['version'] = '0.0.1-a1'

class ConfigApp(ConfigBase):
    """Configuracion de la aplicacion"""
    
    def __init__(self):
        ConfigBase.__init__(self, default=CMD_CFG)
        
        self.dir = os.path.join(os.path.expanduser('~'), '.config', 'turpial-cmd')
        self.filepath = os.path.join(self.dir, 'global')
        
        if not os.path.isdir(self.dir): 
            os.makedirs(self.dir)
        if not os.path.isfile(self.filepath): 
            self.create()
        
        self.load()
        
        if self.read('App', 'version') != self.default['App']['version']:
            self.write('App', 'version', self.default['App']['version'])
