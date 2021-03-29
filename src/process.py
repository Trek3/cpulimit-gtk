class Process:

    def __init__(self, ppid, pid, cmd, cpu, mem, subproc = dict(), active = False):
        self._ppid = ppid
        self._pid = pid
        self._cmd = cmd
        self._cpu = cpu
        self._mem = mem
        self._subproc = subproc
        self._active = active

    def get_pid(self):
        return self._pid

    def get_ppid(self):
        return self._ppid

    def get_active(self):
        return self._active

    def set_active(self, active):
        self._active = active

    def add_sub(self, proc):
        self._subproc[proc.get_pid()] = proc

    def remove_sub(self, pid):
        del self._subproc[pid]
    
    def get_sub(self, pid):
        return self._subproc[pid]

    def get_subs(self):
        return self._subproc

    def to_list(self):
        return [self._pid, self._cmd, self._cpu, self._mem, "Yes" if self._active else "No"]

    def __repr__(self):
        return "[{}/{}] {} ({})".format(self._pid, self._ppid, self._cmd, self._subproc)