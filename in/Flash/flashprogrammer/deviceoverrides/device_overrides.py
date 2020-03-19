# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.

import flashprogrammer.deviceoverrides.LPCxxx as LPCxxx

def performVerifyByReadOverride(vendor, device, data):

    modifiedData = data

    # Some NXP devices require a checksum to be embedded into the vector table
    if vendor.startswith("NXP"):
        if LPCxxx.requiresChecksum(device) == True:
            modifiedData = LPCxxx.generateChecksum(data)

    return modifiedData