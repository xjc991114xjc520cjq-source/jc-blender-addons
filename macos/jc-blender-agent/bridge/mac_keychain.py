"""Scoped generic passwords using Security.framework, without shell/argv secrets.

Only this add-on's endpoint-specific item is accessed. macOS may request permission.
"""
import ctypes as c
import hashlib

PREFIX = 'JCBlenderAgent/API/'
ACCOUNT = b'JCBlenderAgent'
NOT_FOUND = -25300


def service(base, namespace):
    # local_api already validates and normalizes the endpoint before this call.
    return (namespace + hashlib.sha256(base.encode('utf-8')).hexdigest()).encode('utf-8')


def api():
    lib = c.CDLL('/System/Library/Frameworks/Security.framework/Security')
    lib.SecKeychainFindGenericPassword.argtypes = [c.c_void_p, c.c_uint32, c.c_void_p,
        c.c_uint32, c.c_void_p, c.POINTER(c.c_uint32), c.POINTER(c.c_void_p), c.POINTER(c.c_void_p)]
    lib.SecKeychainFindGenericPassword.restype = c.c_int32
    lib.SecKeychainAddGenericPassword.argtypes = [c.c_void_p, c.c_uint32, c.c_void_p,
        c.c_uint32, c.c_void_p, c.c_uint32, c.c_void_p, c.POINTER(c.c_void_p)]
    lib.SecKeychainAddGenericPassword.restype = c.c_int32
    lib.SecKeychainItemModifyAttributesAndData.argtypes = [c.c_void_p, c.c_void_p, c.c_uint32, c.c_void_p]
    lib.SecKeychainItemModifyAttributesAndData.restype = c.c_int32
    lib.SecKeychainItemDelete.argtypes = [c.c_void_p]
    lib.SecKeychainItemDelete.restype = c.c_int32
    lib.SecKeychainItemFreeContent.argtypes = [c.c_void_p, c.c_void_p]
    lib.SecKeychainItemFreeContent.restype = c.c_int32
    return lib


def release(item):
    if item:
        lib = c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        lib.CFRelease.argtypes = [c.c_void_p]; lib.CFRelease.restype = None
        lib.CFRelease(item)


def checked(status):
    if status:
        raise RuntimeError(f'macOS 钥匙串访问失败（{status}）；请检查登录钥匙串或临时输入 Key')


def lookup(lib, name):
    length, data, item = c.c_uint32(), c.c_void_p(), c.c_void_p()
    status = lib.SecKeychainFindGenericPassword(None, len(name), name, len(ACCOUNT), ACCOUNT,
                                               c.byref(length), c.byref(data), c.byref(item))
    if status == NOT_FOUND:
        return None, ''
    checked(status)
    try:
        value = c.string_at(data, length.value).decode('utf-8')
    except Exception:
        release(item)
        raise
    finally:
        if data:
            lib.SecKeychainItemFreeContent(None, data)
    return item, value


def read_key(base, namespace=PREFIX):
    lib = api(); item, value = lookup(lib, service(base, namespace))
    try:
        return value
    finally:
        release(item)


def save_key(base, key, namespace=PREFIX):
    raw = key.strip().encode('utf-8')
    if not raw or len(raw) > 2560 or b'\r' in raw or b'\n' in raw:
        raise ValueError('API Key 不能为空、包含换行或超过2560字节')
    name = service(base, namespace)
    lib = api(); item, _ = lookup(lib, name)
    buffer = c.create_string_buffer(raw)
    try:
        if item:
            checked(lib.SecKeychainItemModifyAttributesAndData(item, None, len(raw), buffer))
        else:
            checked(lib.SecKeychainAddGenericPassword(None, len(name), name,
                    len(ACCOUNT), ACCOUNT, len(raw), buffer, None))
    finally:
        c.memset(buffer, 0, len(buffer)); release(item)


def delete_key(base, namespace=PREFIX):
    lib = api(); item, _ = lookup(lib, service(base, namespace))
    try:
        if item:
            checked(lib.SecKeychainItemDelete(item))
    finally:
        release(item)
