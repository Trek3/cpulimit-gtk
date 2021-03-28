class Process:

    def __init__(self, pid, cmd, cpu, mem, subproc = [], active = False):
        self._pid = pid
        self._cmd = cmd
        self._cpu = cpu
        self._mem = mem
        self._subproc = subproc
        self._active = active

    def get_active(self):
        return self._active

    def set_active(self, active):
        self._active = active

    def add_sub(self, proc):
        self._subproc.append(proc)
    
    def get_sub(self, index):
        return self._subproc[index]

    def get_subs(self):
        return self._subproc

    def to_list(self):
        return [self._pid, self._cmd, self._cpu, self._mem, "Yes" if self._active else "No"]