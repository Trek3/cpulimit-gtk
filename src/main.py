from configparser import ConfigParser
from process import Process

import gi
import subprocess
import re

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

current_selected_process = None

processes = dict()
limited = dict()

def scrape(out):

    procs = []
    current_valid_pids = []
    lines = out.decode("utf-8").split('\n')[1:]
    for line in lines:
        line = line.strip()
        line = line.split()
        if len(line) == 5:
            ppid, pid, cpu, mem, cmd = line
            ppid = int(ppid)
            pid = int(pid)
            cpu = float(cpu)
            mem = float(mem)
            procs.append(Process(ppid, pid, cmd, cpu, mem))
            current_valid_pids.append(pid)
    
    return procs, current_valid_pids

def visit_all(procs):
    res = []
    def aux(start, d, root):
        if root:
            for pid in d:
                res.append(d[pid])
                aux(pid, d, False)
        else:
            if start in d:
                for pid in d[start].get_subs():
                    res.append(d[start].get_subs()[pid])
                    aux(pid, d[start].get_subs()[pid].get_subs(), False)
    aux(None, procs, True)

    return res

def visit_process_tree(start, end, d, root = False):
    if root:
        if end in d:
            return True, d[end]
        else:
            for pid in d:
                return visit_process_tree(pid, end, d, False)
    else:
        if start in d:
            if end in d[start].get_subs():
                return True, d[start].get_subs()[end]
            for pid in d[start].get_subs():
                return visit_process_tree(pid, end, d[start].get_subs()[pid].get_subs(), False)

    return False, None

def check_process_validity(current_valid_pids):

    global processes

    zombie_pids = []
    all_procs = visit_all(processes)
    for process in all_procs:
        if process.get_pid() not in current_valid_pids:
            zombie_pids.append(process.get_pid())


    for pid in zombie_pids:
        ret, proc = visit_process_tree(None, pid, processes, True)
        if ret:
            print('deleting', proc.to_list())
            del processes[proc.get_pid()]

def build_process_tree(ls, current_valid_pids):

    global processes

    for p in ls:
        ppid, pid = p.get_ppid(), p.get_pid()
        ret, proc = visit_process_tree(None, ppid, processes, True)
        if ret:
            if pid not in proc.get_subs():
                proc.add_sub(p)
            else:
                proc.update(p)
        else:
            if pid not in processes:
                processes[pid] = p
            else:
                processes[pid].update(p)


    check_process_validity(current_valid_pids)

def populate_list():

    cmd1 = "ps o ppid,pid,pcpu,pmem,comm"
    out, _ = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

    procs, valids = scrape(out)

    build_process_tree(procs, valids)

class LimiterWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="CPU limit")
        self.set_border_width(10)
        self.set_default_size(600, 800)

        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        self.add(self.grid)

        populate_list()

        # creating the treeview, making it use the filter as a model, and adding the columns
        self.treeview = Gtk.TreeView(model=self.populate_treeview())
        self.select = self.treeview.get_selection()
        self.select.connect("changed", self.on_tree_selection_changed)

        for i, column_title in enumerate(
            ["PID", "Command", "CPU usage", "Memory usage", "Active", "Percentage"]
        ):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.treeview.append_column(column)

        self.activate = Gtk.Button(label="Activate")
        self.activate.connect("clicked", self.on_activate_button_clicked)

        self.update = Gtk.Button(label="Refresh")
        self.update.connect("clicked", self.on_update_button_clicked)

        self.percentage = Gtk.Entry()
        self.percentage.set_placeholder_text(text="percentage of CPU")
        self.percentage.set_margin_top(10)
        self.percentage.set_margin_bottom(10)
        self.limit_label = Gtk.Label.new(str="Insert max percentage:")

        self.box = Gtk.Box(spacing=10)
        self.box.pack_start(self.limit_label, True, True, 0)
        self.box.pack_start(self.percentage, True, True, 0)
        self.box.set_sensitive(False)

        # setting up the layout, putting the treeview in a scrollwindow, and the buttons in a row
        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)
        self.grid.attach(self.scrollable_treelist, 10, 10, 10, 10)
        self.scrollable_treelist.add(self.treeview)

        self.grid.attach_next_to(self.box, self.scrollable_treelist, Gtk.PositionType.BOTTOM, 10, 1)
        self.grid.attach_next_to(self.update, self.scrollable_treelist, Gtk.PositionType.TOP, 10, 1)
        self.grid.attach_next_to(self.activate, self.box, Gtk.PositionType.BOTTOM, 10, 1)
        self.show_all()

    def populate_treeview(self):
        global processes

        process_tree = Gtk.TreeStore(int, str, float, float, str, str)

        def aux(start, d, parent, root):
            if root:
                for pid in d:
                    par = process_tree.append(None, d[pid].to_list())
                    aux(pid, d, par, False)
            else:
                if start in d:
                    for pid in d[start].get_subs():
                        par = process_tree.append(parent, d[start].get_subs()[pid].to_list())
                        aux(pid, d[start].get_subs()[pid].get_subs(), par, False)
                
        aux(None, processes, None, True)
        return process_tree

    def on_update_button_clicked(self, widget):
        populate_list()
        self.treeview.set_model(self.populate_treeview())

    def on_activate_button_clicked(self, widget):

        global processes, limited

        if current_selected_process is not None:
            ret, proc = visit_process_tree(None, current_selected_process, processes, True)
            if ret:
                active = proc.get_active()

                if not active:
                    cmd1 = "cpulimit -i -l {} -p {}".format(int(self.percentage.get_text()), current_selected_process)
                    proc.set_percentage(self.percentage.get_text())
                    print(cmd1)
                    limited[current_selected_process] = subprocess.Popen(cmd1, shell=True)
                else:
                    if current_selected_process in limited:
                        limited[current_selected_process].terminate()
                        del limited[current_selected_process]

                proc.set_active(not active)
                self.treeview.set_model(self.populate_treeview())

    def on_tree_selection_changed(self, selection):

        global current_selected_process

        model, treeiter = selection.get_selected()
        if treeiter is not None:
            current_selected_process = model[treeiter][0]
            ret, proc = visit_process_tree(None, current_selected_process, processes, True)
            if ret:
                if proc.get_active():
                    self.activate.set_label("Stop")
                    self.box.set_sensitive(False)
                else:
                    self.activate.set_label("Limit")
                    self.box.set_sensitive(True)

def main(config):
    window = LimiterWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()

    Gtk.main()

if __name__ == '__main__':

    config = ConfigParser()
    config.read('conf/config.ini')

    main(config)