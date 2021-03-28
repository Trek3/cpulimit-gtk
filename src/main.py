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

    currpid = []
    lines = out.decode("utf-8").split('\n')[1:]
    for line in lines:
        line = line.strip()
        line = line.split()
        if len(line) == 4:
            pid, cpu, mem, cmd = line
            p = Process(int(pid), cmd, float(cpu), float(mem), False)
            currpid.append(int(pid))
            if int(pid) not in processes:
                processes[int(pid)] = p

    temp = []
    for pid in processes:
        if pid not in currpid:
            temp.append(pid)

    for pid in temp:
        print('deleting', processes[pid].to_list())
        del processes[pid]

def populate_list():

    cmd1 = "ps o pid,pcpu,pmem,comm"
    out, _ = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

    return scrape(out)

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
            ["PID", "Command", "CPU usage", "Memory usage", "Active"]
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

        process_list = Gtk.ListStore(int, str, float, float, str)
        for process in processes:
            process_list.append(processes[process].to_list())

        return process_list

    def on_update_button_clicked(self, widget):
        populate_list()
        self.treeview.set_model(self.populate_treeview())

    def on_activate_button_clicked(self, widget):

        global processes, limited

        if current_selected_process is not None:
            active = processes[current_selected_process].get_active()

            if not active:
                cmd1 = "cpulimit -l {} -p {}".format(int(self.percentage.get_text()), current_selected_process)
                print(cmd1)
                limited[current_selected_process] = subprocess.Popen(cmd1, shell=True)

                model, treeiter = self.treeview.get_selection().get_selected()
                model[treeiter].modify_bg(Gtk.StateType.NORMAL, Gdk.Color(6400, 6400, 6440))
            else:
                if current_selected_process in limited:
                    limited[current_selected_process].terminate()
                    del limited[current_selected_process]

            processes[current_selected_process].set_active(not active)
            self.treeview.set_model(self.populate_treeview())

    def on_tree_selection_changed(self, selection):

        global current_selected_process

        model, treeiter = selection.get_selected()
        if treeiter is not None:
            current_selected_process = model[treeiter][0]
            if processes[current_selected_process].get_active():
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