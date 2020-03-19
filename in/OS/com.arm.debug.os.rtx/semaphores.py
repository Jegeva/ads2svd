# Copyright (C) 2013,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class Semaphores(RtxInterTaskCommTable):

    def __init__(self):
        id = "semaphores"

        fields = [createField(id, "addr", ADDRESS),
                  createField(id, "tokens", DECIMAL),
                  createField(id, "tasks", TEXT)]

        functions = [lambda members, prlnk: createAddressCell(prlnk.readAsAddress()),
                     lambda members, prlnk: makeNumberCell(members,  "tokens"),
                     lambda members, prlnk: makeTaskWaitersCell(members,"thread_list")]

        RtxInterTaskCommTable.__init__(self, id, fields, functions, "Semaphore")
