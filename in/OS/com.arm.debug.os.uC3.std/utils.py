# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

def make_reg_list(offset, size, *reg_names):
    result = [("%s" % reg_names[x], long(offset + x*size)) for x in xrange(len(reg_names))]
    return result

def make_reg_range(offset, size, prefix, start, count):
    result = [("%s%d" % (prefix, x+start), long(offset + x*size)) for x in xrange(0, count)]
    return result

