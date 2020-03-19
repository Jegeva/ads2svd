# Copyright (C) 2013,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class Mutexes(RtxInterTaskCommTable):

    def __init__(self):
        id = "mutexes"

        fields = [createField(id, "addr",     ADDRESS),
                  createField(id, "owner",    TEXT),
                  createField(id, "tasks",    TEXT),
                  createField(id, "priority", DECIMAL),
                  createField(id, "level",    DECIMAL)]

        functions = [lambda members, prlnk: createAddressCell(prlnk.readAsAddress()),
                     lambda members, prlnk: makeTaskCell(members, "owner_thread"),
                     lambda members, prlnk: makeTaskWaitersCell(members, "thread_list"),
                     lambda members, prlnk: makeNumberCell(members, "priority"),
                     lambda members, prlnk: makeNumberCell(members, "lock")]

        RtxInterTaskCommTable.__init__(self, id, fields, functions, "Mutex")
