import sys, os
from time import localtime, ctime


class LogFile:
    
    def __init__(self, filename=None, limitsize=9999):
        if filename is None:
            filename = sys.argv[0]
            if filename.endswith('.py'):
                filename = filename[:-3]
            filename += '.log'
        if not self._open(filename, limitsize):
            import tempfile
            filename = os.path.join(tempfile.gettempdir(),
                                    os.path.basename(filename))
            if not self._open(filename, limitsize):
                self.f = self.filename = None
        self.lasttime = None

    def close(self):
        if self.f is not None:
            self.f.close()
            self.f = None

    def __nonzero__(self):
        return self.f is not None

    def _open(self, filename, limitsize):
        mode = 'w'
        try:
            st = os.stat(filename)
        except OSError:
            pass
        else:
            if st.st_size <= limitsize:
                mode = 'a'
        try:
            self.f = open(filename, mode)
        except IOError:
            return 0
        else:
            self.filename = filename
            if mode == 'a':
                print >> self.f
                print >> self.f, '='*44
            return 1

    def _check(self):
        if self.f is None:
            return 0
        lt = localtime()
        if lt[:5] != self.lasttime:
            self.lasttime = lt[:5]
            self.f.write('========= %s =========\n' % ctime())
        return 1

    def write(self, data):
        if self._check():
            self.f.write(data)

    def writelines(self, data):
        if self._check():
            self.f.writelines(data)


class Logger:
    stdout_captured = 0
    stderr_captured = 0
    
    def __init__(self, f):
        self.targets = [f]

    def capture_stdout(self):
        if not Logger.stdout_captured:
            self.targets.append(sys.stdout)
            sys.stdout = self
            Logger.stdout_captured = 1

    def capture_stderr(self):
        if not Logger.stderr_captured:
            self.targets.append(sys.stderr)
            sys.stderr = self
            Logger.stderr_captured = 1

    def write(self, data):
        for f in self.targets:
            f.write(data)

    def writelines(self, data):
        for f in self.targets:
            f.writelines(data)
