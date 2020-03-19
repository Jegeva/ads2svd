# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from __future__ import with_statement
from ConfigParser import RawConfigParser
from tmp_file import makeTempFile

def _caseSensitiveIniFileReader():
    '''Make a parser for ini files which treats keys as case-sensitive'''
    parser = RawConfigParser()
    parser.optionxform = str
    return parser


# Take n elements at a time from a sequence.
# Example: _n_at_a_time([1, 2, 3, 4, 5, 6], 3)
# generates [1, 2, 3], [4, 5, 6]
def _n_at_a_time(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def retargetIniFile(path, *edits, **kwargs):
    '''Clone an ini file to a temporary file, and do the specified edits.
       (Keyword args 'tmpPrefix', 'tmpSuffix' set prefix, suffix for the
       temporary file name, if the caller cares).
       Edits are specified as triples of arguments: section, key, newValue.
       Return the path to the new file.  The file is cleaned up on
       process exit.'''
    config = _caseSensitiveIniFileReader()
    config.read(path)
    for section, key, newValue in _n_at_a_time(edits, 3):
        config.set(section, key, newValue)

    tmp =  makeTempFile(kwargs.get('tmpPrefix', 'ds_'),
                        kwargs.get('tmpSuffix', '.txt'))
    with open(tmp, 'w') as dest:
        config.write(dest)
    return tmp

