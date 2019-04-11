# -*- coding: utf-8 -*-
"""
Holds misc. utility methods which prove to be
useful throughout this library.
"""
__title__ = 'newspaper'
__author__ = 'Lucas Ou-Yang'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014, Lucas Ou-Yang'

import codecs
import os
import re
import sys
import threading
import time


class StringSplitter(object):
    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def split(self, string):
        if not string:
            return []
        return self.pattern.split(string)


class StringReplacement(object):
    def __init__(self, pattern, replaceWith):
        self.pattern = pattern
        self.replaceWith = replaceWith

    def replaceAll(self, string):
        if not string:
            return ''
        return string.replace(self.pattern, self.replaceWith)


class ReplaceSequence(object):
    def __init__(self):
        self.replacements = []

    def create(self, firstPattern, replaceWith=None):
        result = StringReplacement(firstPattern, replaceWith or '')
        self.replacements.append(result)
        return self

    def append(self, pattern, replaceWith=None):
        return self.create(pattern, replaceWith)

    def replaceAll(self, string):
        if not string:
            return ''

        mutatedString = string
        for rp in self.replacements:
            mutatedString = rp.replaceAll(mutatedString)
        return mutatedString


def timelimit(timeout):
    """Borrowed from web.py, rip Aaron Swartz
    """
    def _1(function_):
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function_(*args, **kw)
                    except:
                        self.error = sys.exc_info()
            c = Dispatch()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError()
            if c.error:
                raise c.error[0](c.error[1])
            return c.result
        return _2
    return _1


def domain_to_filename(domain):
    """All '/' are turned into '-', no trailing. schema's
    are gone, only the raw domain + ".txt" remains
    """
    filename = domain.replace('/', '-')
    if filename[-1] == '-':
        filename = filename[:-1]
    filename += ".txt"
    return filename


def filename_to_domain(filename):
    """[:-4] for the .txt at end
    """
    return filename.replace('-', '/')[:-4]


def is_ascii(word):
    """True if a word is only ascii chars
    """
    def onlyascii(char):
        if ord(char) > 127:
            return ''
        else:
            return char
    for c in word:
        if not onlyascii(c):
            return False
    return True



def print_duration(method):
    """Prints out the runtime duration of a method in seconds
    """
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print('%r %2.2f sec' % (method.__name__, te - ts))
        return result
    return timed


def chunks(l, n):
    """Yield n successive chunks from l
    """
    newn = int(len(l) / n)
    for i in range(0, n - 1):
        yield l[i * newn:i * newn + newn]
    yield l[n * newn - newn:]


class FileHelper(object):
    @staticmethod
    def loadResourceFile(filename):
        if not os.path.isabs(filename):
            dirpath = os.path.abspath(os.path.dirname(__file__))
            path = os.path.join(dirpath, 'resources', filename)
        else:
            path = filename
        try:
            f = codecs.open(path, 'r', 'utf-8')
            content = f.read()
            f.close()
            return content
        except IOError:
            raise IOError("Couldn't open file %s" % path)

