import os, md5, sys
#import common.debug


class FileCache:
    MAX_FILES = 8
    
    def __init__(self):
        self.cache = {}
        self.time = 0
    
    def access(self, filename, position, writing=0):
        if filename in self.cache:
            time, mode, f = self.cache[filename]
            if writing > mode:
                f.close()
                del self.cache[filename]
        if filename not in self.cache:
            if len(self.cache) >= FileCache.MAX_FILES:
                (time, mode, f), k = min([(v,k) for (k,v) in self.cache.items()])
                f.close()
                del self.cache[k]
            try:
                f = open(filename, ('rb', 'r+b')[writing])
            except (IOError, OSError):
                if not writing:
                    raise
                if not os.path.isdir(os.path.dirname(filename)):
                    os.mkdir(os.path.dirname(filename))
                f = open(filename, 'w+b')
            mode = writing
        self.time += 1
        self.cache[filename] = self.time, mode, f
        f.seek(position)
        return f


class MemoryBlock:
    def __init__(self, data):
        self.data = data
    def overwrite(self, newdata):
        self.data = newdata
    def read(self):
        return self.data

class FileBlock:
    def __init__(self, filename, position, length, readonly=1, complete=1):
        self.filename = filename
        self.position = position
        self.length = length
        self.readonly = readonly
        self.complete = complete
    def overwrite(self, newdata):
        self.memorydata = newdata
        if self.readonly:
            print >> sys.stderr, "cannot overwrite file", self.filename
            return
        try:
            f = Data.Cache.access(self.filename, self.position, writing=1)
            f.write(newdata)
        except (IOError, OSError):
            print >> sys.stderr, "cache write error:", self.filename
            return
        self.complete = 1
        del self.memorydata
    def read(self):
        if self.complete:
            f = Data.Cache.access(self.filename, self.position)
            return f.read(self.length)
        else:
            return self.memorydata

def maybe_unlink(file):
    try:
        os.unlink(file)
    except:
        pass


class Data:
    SafeChars = {}
    for c in ".abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        SafeChars[c] = c
    Translate = ''.join([SafeChars.get(chr(c), '_') for c in range(256)])
    del c, SafeChars
    Cache = FileCache()

    def __init__(self):
        self.content = {}
        self.backupfile = None
        self.readonly = 0

    clear = __init__

    ### Public interface ###

    def store(self, position, data, filename=None, readonly=1):
        """This class assumes that all accesses to block within the data
        are done for disjoint intervals: no overlapping writes !"""
        if self.content is not None:
            try:
                self.content[position].overwrite(data)
            except KeyError:
                if filename is None:
                    self.content[position] = MemoryBlock(data)
                else:
                    self.content[position] = FileBlock(filename, position,
                                                       len(data), readonly)
        if self.backupfile and not self.readonly:
            try:
                f = Data.Cache.access(self.backupfile, position, writing=1)
                f.write(data)
                f.flush()
            except (IOError, OSError):
                print >> sys.stderr, "cache write error:", self.backupfile

    def loadfrom(self, filename, position, length, checksum):
        """Try to load data from the given filename, with the given
        expected MD5 checksum.  The filename must be Unix-style, and is
        looked up both in the directory SOURCEDIR and with a mangled name
        in the cache directory CACHEDIR."""
        directname = os.path.join(self.SOURCEDIR, *filename.split('/'))
        mangledname = filename.translate(Data.Translate)
        cachename = os.path.join(self.CACHEDIR, mangledname)
        for name, readonly in ((directname, 1), (cachename, 0)):
            try:
                f = Data.Cache.access(name, position)
                data = f.read(length)
            except (IOError, OSError):
                pass
            else:
                if len(data) == length and md5.new(data).digest() == checksum:
                    # correct data
                    self.store(position, data, name, readonly)
                    return 1
        if self.content is not None and not self.content.has_key(position):
            self.content[position] = FileBlock(cachename, position, length,
                                               readonly=0, complete=0)
        elif self.readonly:
            print >> sys.stderr, "Note: the music data has changed. You can get"
            print >> sys.stderr, "the server's version by deleting", directname
            return 1   # incorrect data, but ignored
        return 0

    def read(self):
        """Return the data as built so far."""
        if self.content is not None:
            items = self.content.items()
            items.sort()
            result = ''
            for position, block in items:
                if len(result) < position:
                    result += '\x00' * (position-len(result))
                data = block.read()
                result = result[:position] + data + result[position+len(data):]
            return result
        else:
            f = Data.Cache.access(self.backupfile, 0)
            return f.read()

    def fopen(self):
        if self.content is not None:
            from cStringIO import StringIO
            return StringIO(self.read())
        else:
            return Data.Cache.access(self.backupfile, 0)

    def freezefilename(self, fileexthint='.wav'):
        """Return the name of a file from which the data can be read. If all
        the current data comes from the same file, it is assumed to be exactly
        the file that we want."""
        if not self.backupfile:
            files = {}
            for position, block in self.content.items():
                if not isinstance(block, FileBlock):
                    break
                if block.complete:
                    files[block.filename] = block
            else:
                if len(files) == 1:
                    self.backupfile, block = files.items()[0]
                    self.readonly = block.readonly
            if not self.backupfile:
                import atexit, tempfile
                self.backupfile = tempfile.mktemp(fileexthint)
                atexit.register(maybe_unlink, self.backupfile)
                f = Data.Cache.access(self.backupfile, 0, writing=1)
                for position, block in self.content.items():
                    f.seek(position)
                    f.write(block.read())
                f.flush()
            #print 'freezefilename ->', self.backupfile
            #print '                    readonly =', self.readonly
        self.content = None
        return self.backupfile
