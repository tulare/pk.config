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
    'Registry', 'RegKey', 'RegValue',
]

import sys
PY3 = sys.version_info > (3,)

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

# --------------------------------------------------------------------

class RegKey(object) :

    def __init__(self, key) :
        self._key = key
        self.unicode = reg_unicode(self._key)

    def __str__(self) :
        if PY3 :
            return self._key
        return self.unicode.encode(sys.stdout.encoding)

    def __repr__(self) :
        return '{}({})'.format(
            self.__class__.__name__,
            self
        )

    def __eq__(self, other) :
        if isinstance(other, self.__class__) :
            return self.unicode == other.unicode
        return NotImplemented        

    @property
    def string(self) :
        if PY3 :
            return self._key
        return self.unicode.encode('ISO-8859-1')

    @property
    def iso(self) :
        if PY3 :
            return self._key
        return self._key.decode('ISO-8859-1')

# --------------------------------------------------------------------

class RegValue(object) :

    def __init__(self, value, regtype=None) :
        self._value = value
        self.regtype = regtype or self.detect_regtype()

    def __str__(self) :
        return reg_str(self.value)

    def __repr__(self) :
        return '{}({!r}, {!r})'.format(
            self.__class__.__name__,
            self.value,
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
            self.path.encode(sys.stdout.encoding)
        )

    @property
    def node(self) :
        return getattr(self, '_node', self._root)

    @property
    def path(self) :
        return getattr(self, '_path', '')

    @property
    def iter_keys(self) :
        indice = 0
        while True :
            try :
                key = winreg.EnumKey(self.node, indice)
                k = RegKey(key)
                yield k.iso
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
        k = RegKey(key)
        winreg.CreateKey(self.node, k.string)
        return RegistryNode(self, key)

    def delete_key(self, key, force=False) :
        # Vérifier la validité de la clé avant toute chose
        try :
            RegistryNode(self, key)
        except Exception as e :
            raise RegistryKeyError('{} : {}'.format(e, key))            

        k = RegKey(key)

        # doit-on nettoyer les sous-clés d'abord ?
        if force :
            deletion_point = self[key]
            for subkey in deletion_point.keys :
                deletion_point.delete_key(subkey, force)

        # nettoie la clef, ne marche pas si elle contient des sous-clés
        try :
            winreg.DeleteKey(self.node, k.string)
        except WindowsError as e :
            raise RegistryKeyError('{} : {}'.format(e, key))

    @property
    def iter_values(self) :
        indice = 0
        while True :
            try :
                name, value, reg_type = winreg.EnumValue(self.node, indice)
                k = RegKey(name)
                yield k.iso, value, REG_TYPES_ID[reg_type]
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
        k = RegKey(name)
        try :
            value, regtype = self.typed_values.get(k.unicode, default)
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
        k = RegKey(name)
        v = RegValue(value, regtype)
        key = winreg.OpenKey(self.node, '', 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, k.string, 0, REG_TYPES[v.regtype], v.value)

    def delete_value(self, name) :
        name = name or ''
        k = RegKey(name)
        try :
            key = winreg.OpenKey(self.node, '', 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, k.string)
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

        k = RegKey(key)

        if node.path :
            self._path = node.path + '\\' + k.unicode
        else :
            self._path = node.path + k.unicode
        self._node = winreg.OpenKey(node.node, k.string)

# --------------------------------------------------------------------

