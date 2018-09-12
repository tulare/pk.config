# -*- encoding: utf-8 -*-
from __future__ import (
    absolute_import,
    print_function, division,
    #unicode_literals
)

__all__ = [
    'HKEYS', 'REG_TYPES', 'REG_TYPES_ID',
    'RegistryKeyOk', 'RegistryKeyError',
    'RegistryValueError',
    'Registry', 'RegValue',
]

import sys
PY3 = sys.version_info > (3,)

import os
import datetime

if PY3 :
    # python 3.x
    import winreg
else :
    # python 2.x
    import _winreg as winreg

from .exceptions import (
    RegistryKeyOk, RegistryKeyError,
    RegistryValueError
)

# --------------------------------------------------------------------

HKEYS = {
    item[0] : item[1]
    for item in filter(
        lambda it : it[0].startswith('HKEY_'),
        vars(winreg).items()
    )
}

KEYSAM = {
    item[0] : item[1]
    for item in filter(
        lambda it : it[0].startswith('KEY_'),
        vars(winreg).items()
    )
}

VALUE_TYPES = (
    'REG_BINARY',
    'REG_DWORD',
    'REG_DWORD_BIG_ENDIAN',
    'REG_EXPAND_SZ',
    'REG_LINK',
    'REG_MULTI_SZ',
    'REG_NONE',
    'REG_RESOURCE_LIST',
    'REG_FULL_RESOURCE_DESCRIPTOR',
    'REG_RESOURCE_REQUIREMENTS_LIST',
    'REG_SZ',
)

REG_TYPES = {
    key : value
    for key, value in filter(
        lambda item : item[0] in VALUE_TYPES,
        vars(winreg).items()
    )
}

REG_TYPES_ID = dict(
    (v,k) for k,v in REG_TYPES.items()
)

WIN32_EPOCH = datetime.datetime(1601, 1, 1)

# --------------------------------------------------------------------

def reg_unicode(chaine) :
    if PY3 :
        return chaine
    if isinstance(chaine, unicode) :
        return chaine
    try :
        return chaine.decode('utf8')
    except UnicodeDecodeError :
        return chaine.decode(sys.stdout.encoding)

def reg_str(value) :
    if PY3 :
        return str(value)
    try :
        return str(value)
    except UnicodeEncodeError :
        return value.encode(sys.stdout.encoding)

def reg_unicode_iso(value) :
    if PY3 :
        return value
    return value.decode('ISO-8859-1')

def reg_str_iso(value) :
    if PY3 :
        return value
    return value.encode('ISO-8859-1')

def reg_datetime(timestamp) :
    return WIN32_EPOCH + datetime.timedelta(microseconds=timestamp // 10)

# --------------------------------------------------------------------

class RegValue(object) :

    def __init__(self, value, regtype=None) :
        self._value = value
        self.regtype = regtype or self.detect_regtype()

    def __str__(self) :
        return reg_str(self.value)

    def __repr__(self) :
        return '{}({}, {})'.format(
            self.__class__.__name__,
            self,
            self.regtype
        )
        
    @property
    def value(self) :
        if self.regtype in ('REG_SZ', 'REG_EXPAND_SZ') :
            return reg_unicode(self._value)

        if self.regtype in ('REG_MULTI_SZ') :
            self._value[:] = map(reg_unicode, self._value)

        return self._value

    def detect_regtype(self) :
        if isinstance(self._value, (''.__class__, u''.__class__)) :
            return 'REG_SZ'

        if isinstance(self._value, list) :
            return 'REG_MULTI_SZ'

        if isinstance(self._value, int) :
            return 'REG_DWORD'

        return 'REG_NONE'
    
# --------------------------------------------------------------------

class Registry(object) :

    def __init__(self, hkey='HKEY_CURRENT_USER') :
        self._hkey = hkey
        self._root = HKEYS[self._hkey]

    def __getitem__(self, key) :
        return RegistryNode(self, key)

    def __repr__(self) :
        return '{}({})'.format(
            self.__class__.__name__,
            self
        )

    def __str__(self) :
        return '[{}]\\{}'.format(
            self._hkey,
            reg_str(self.path)
        )

    def __len__(self) :
        return self.nb_keys

    @property
    def node(self) :
        return getattr(self, '_node', self._root)

    @property
    def path(self) :
        return getattr(self, '_path', '')

    @property
    def parent(self) :
        parent_path = os.path.dirname(self.path)
        return Registry(self._hkey)[parent_path]

    @property
    def last_modified(self) :
        keys, values, modified = winreg.QueryInfoKey(self.node)
        return reg_datetime(modified)

    @property
    def nb_keys(self) :
        nb_keys, _, _ = winreg.QueryInfoKey(self.node)
        return nb_keys

    @property
    def nb_values(self) :
        _, nb_values, _ = winreg.QueryInfoKey(self.node)
        return nb_values

    @property
    def iter_keys(self) :
        indice = 0
        while True :
            try :
                key = winreg.EnumKey(self.node, indice)
                yield reg_unicode_iso(key)
                indice += 1
            except WindowsError as e :
                break

    @property
    def keys(self) :
        return list(self.iter_keys)
 
    @property
    def valid_keys(self) :
        return list(
            filter(
                lambda key :
                    isinstance(self.validate_key(key), RegistryKeyOk),
                self.iter_keys
            )
        )

    @property
    def dead_keys(self) :
        return list(
            filter(
                lambda key :
                    isinstance(self.validate_key(key), RegistryKeyError),
                self.iter_keys
            )
        )

    def validate_key(self, key) :
        try :
            RegistryNode(self, key)
            return RegistryKeyOk()
        except Exception as e :
            return RegistryKeyError(*e.args)

    def create_key(self, key) :
        uni_key = reg_unicode(key)
        reg_key = reg_str_iso(uni_key)
        winreg.CreateKey(self.node, reg_key)
        return RegistryNode(self, key)

    def delete_key(self, key, force=False) :
        uni_key = reg_unicode(key)
        reg_key = reg_str_iso(uni_key)
        str_key = reg_str(uni_key)
        
        # Vérifier la validité de la clé avant toute chose
        if uni_key not in self.keys :
            raise RegistryKeyError(
                '{} : {}'.format('key not found', str_key)
            )            

        # doit-on nettoyer les sous-clés d'abord ?
        if force :
            deletion_point = self[key]
            for subkey in deletion_point.keys :
                deletion_point.delete_key(subkey, force)

        # nettoie la clef, ne marche pas si elle contient des sous-clés
        try :
            winreg.DeleteKey(self.node, reg_key)
        except WindowsError as e :
            raise RegistryKeyError('{} : {}'.format(e, str_key))

    @property
    def iter_values(self) :
        indice = 0
        while True :
            try :
                name, value, reg_type = winreg.EnumValue(self.node, indice)
                reg_name = reg_unicode_iso(name)
                yield reg_name, value, REG_TYPES_ID[reg_type]
                indice += 1
            except WindowsError as e :
                break

    @property
    def values(self) :
        return dict((name, value) for name, value, _ in self.iter_values)

    @property
    def typed_values(self) :
        return dict(
            (name, (value, reg_type))
            for name, value, reg_type in self.iter_values
        )

    def get_value(self, name=None, default=None, expand=False) :
        name = name or ''
        uni_name = reg_unicode(name)
        try :
            value, regtype = self.typed_values.get(uni_name)
        except TypeError :
            return default

        if expand :
            if regtype in ('REG_SZ', 'REG_EXPAND_SZ',) :
                value = winreg.ExpandEnvironmentStrings(value)
            if regtype in ('REG_MULTI_SZ',) :
                value[:] = map(winreg.ExpandEnvironmentStrings, value)

        return value

    def set_value(self, name, value, regtype=None) :
        name = name or ''
        uni_name = reg_unicode(name)
        reg_name = reg_str_iso(uni_name)

        v = RegValue(value, regtype)
        key = winreg.OpenKey(self.node, '', 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, reg_name, 0, REG_TYPES[v.regtype], v.value)

    def delete_value(self, name) :
        name = name or ''
        uni_name = reg_unicode(name)
        reg_name = reg_str_iso(uni_name)
        
        try :
            key = winreg.OpenKey(self.node, '', 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, reg_name)
            winreg.CloseKey(key)
        except Exception as e :
            raise RegistryValueError(*e.args)

    def clear_values(self) :
        for value in self.values :
            self.delete_value(value)

# --------------------------------------------------------------------

class RegistryNode(Registry) :

    def __init__(self, node, key) :
        super(RegistryNode, self).__init__(node._hkey)

        uni_key = reg_unicode(key)
        reg_key = reg_str_iso(uni_key)

        if node.path :
            self._path = node.path + u'\\' + uni_key
        else :
            self._path = node.path + uni_key
        self._node = winreg.OpenKey(node.node, reg_key)

# --------------------------------------------------------------------

