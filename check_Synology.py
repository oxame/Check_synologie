#!/usr/bin/python3.6
# -*- encoding: utf-8 -*-

import getopt, sys,subprocess, re
from datetime import timedelta


# OID for hrStorageType
oid_hrStorageType = 'HOST-RESOURCES-MIB:hrStorageType'
# OID for hrStorageUsed
oid_hrStorageUsed = 'HOST-RESOURCES-MIB:hrStorageUsed'
# OID for hrStorageSize
oid_hrStorageSize = 'HOST-RESOURCES-MIB:hrStorageSize'
# OID for hrStorageTable
oid_hrStorageTable = 'HOST-RESOURCES-MIB:hrStorageTable'
# OID for UPTIME
oid_hrSystemUptime = 'HOST-RESOURCES-MIB::hrSystemUptime.0'
# IOD for Disk status
OID_DiskStatus = 'SNMPv2-SMI::enterprises.6574.2.1.1.5'
# IOD for Disk Name
OID_DiksName = 'SNMPv2-SMI::enterprises.6574.2.1.1.2'



# Exit Code
ExitOK = 0
ExitWarning = 1
ExitCritical = 2
ExitUNKNOWN = 3


# Function to convert bytes to GB
def octet_to_gb(bytes):
    return round(int(bytes) / (1024 ** 2), 2)



def snmp_walk(ip, community, oid):
    cmd = "snmpwalk -v 2c -c {} {} {}".format(community, ip, oid)
    try:
        output = subprocess.check_output(cmd, shell=True)
        return output.decode()
    except subprocess.CalledProcessError as e:
        return "Error occured: {}".format(e.output.decode())


def Get_Index_hrStorageDescr(snmpwalk,volume):
    index = None
    for S in snmpwalk.split('\n'):
        if re.search(volume,S):
            index = re.search('\D*::\D*(\d*)\s\D+',S)
            return index.group(1)
    return index

def Get_hrStorageDescrSize(snmpwalk):
    Size = re.search('\D*\d*\D*:\s(\d*)', snmpwalk)
    return Size.group(1)


def Get_hrStorageDescUsed(snmpwalk):
    Used = re.search('\D*\d*\D*:\s(\d*)', snmpwalk)
    return Used.group(1)


def Get_Volume(ip,community, volume, oid_hrStorageTable, oid_hrStorageSize, oid_hrStorageUsed):

    Used = None
    Size = None
    Index = Get_Index_hrStorageDescr(snmp_walk(ip,community,  oid_hrStorageTable), volume)
    if Index is None:
        return Used,Size, "{0} non trouver".format(volume)
    else:
        Size = Get_hrStorageDescrSize(snmp_walk(ip,community,  oid_hrStorageSize + '.' + Index))
        Used = Get_hrStorageDescUsed(snmp_walk(ip,community,  oid_hrStorageUsed + '.' + Index))
        return Used, Size, volume

def Check_Size(Used,Size,Warning,Critical):
    Pourcent = (int(Used) / int(Size)) * 100
    UsedGB = octet_to_gb(int(Used))

    if int(Pourcent) < int(Warning):
        Exit = 0
    elif int(Pourcent) >= int(Warning) and int(Pourcent) < int(Critical):
        Exit = 1
    elif int(Pourcent) >= int(Critical):
        Exit = 2
    else:
        Exit = 3

    ReturnNagios(Exit,"{0} Gb".format(UsedGB))

def CheckUptime(ip, community,oid_hrSystemUptime):
        Time = snmp_walk(ip, community,oid_hrSystemUptime).split(" ")
        return Time[-1].replace("\n", "")


def CheckDiskStatus(ip, community,OID_DiskStatus, OID_DiksName):

    Print = ""
    Exit = 0
    STAT = {'1': 'Normal', '2' : 'Initialized', '3' : 'NotInitialized', '4' : 'SystemPartitionFailed' , '5' : 'Crashed'}
    DiskUnNormal = []
    for DiskStatus in snmp_walk(ip, community,OID_DiskStatus).split('\n'):
        if DiskStatus.split(" ")[-1] != '1' and DiskStatus.split(" ")[-1] != '' :
            DiskUnNormal.append(DiskStatus.split(" ")[0].split('.')[-1] + ":" + STAT[DiskStatus.split(" ")[-1]])
        if DiskStatus.split(" ")[-1] == '2' or DiskStatus.split(" ")[-1] == '3':               
            Exit = 1
        elif DiskStatus.split(" ")[-1] == '4' or DiskStatus.split(" ")[-1] == '5':
            Exit = 2

    # On récupére le nom des disk en erreur
    if len(DiskUnNormal) > 0:
        for A in DiskUnNormal:            
            Diskname = snmp_walk(ip, community,OID_DiksName + '.' + "{0}".format(A.split(':')[0]) )
            Print = Print +  "{0} {1} ".format(Diskname.split(':')[-1].replace('"','').replace('\n',''), A.split(':')[1])

    ReturnNagios(Exit,Print)



def ReturnNagios(Exit,Print):
    # Exit Code
    ExitOK = 0
    ExitWarning = 1
    ExitCritical = 2
    ExitUNKNOWN = 3

    if Exit == 0:
        print("OK : {0}".format(Print))
        sys.exit(ExitOK)
    elif Exit == 1:
        print("WARNING : {0}".format(Print))
        sys.exit(ExitWarning)
    elif Exit == 2:
        print("CRITICAL : {0}".format(Print))
        sys.exit(ExitCritical)
    elif Exit == 3:
        print("UNKNOWN : {0}".format(Print))
        sys.exit(ExitUNKNOWN)

def parse_args(argv):
    ip = None
    community = None
    version = None
    volume = None
    warning = 80
    critical = 90
    check = None
    try:
        opts, args = getopt.getopt(argv, "i:c:v:V:W:C:s:", ["ip=", "community=", "version=", "warning=","critical=", "check="])
    except getopt.GetoptError:
        print("my_script.py -i <ip> -c <community> -v <version> -V <volume> -u <unit> -s <check>")
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-i", "--ip"):
            ip = arg
        elif opt in ("-c", "--community"):
            community = arg
        elif opt in ("-v", "--version"):
            version = arg
        elif opt in ("-V", "--volume"):
            volume = arg
        elif opt in ("-W", "--warning"):
            warning = arg
        elif opt in ("-C", "--critical"):
            critical = arg 
        elif opt in ("-s", "--check"):
            check = arg                  
    if not (ip and community and version):
            print("my_script.py -i <ip> -c <community> -v <version> [-V <volume>] [-W <warning>] [-C <critical>] [-s <check>]")
            sys.exit(2)
    return ip, community, version, volume, warning, critical, check


def main():

    ip, community, version, volume, warning, critical, check = parse_args(sys.argv[1:])

    if check == 'volume':
        Used, Size, Print  = Get_Volume(ip,community, volume,  oid_hrStorageTable, oid_hrStorageSize, oid_hrStorageUsed)

        if Used is None:
            ReturnNagios(3,"{0}".format(Print))
        else:
            Check_Size(Used,Size,warning,critical)
    elif check == 'uptime':
        ReturnNagios(0,"{0}".format(CheckUptime(ip, community,oid_hrSystemUptime)))
    elif check == 'diskstatus':
        CheckDiskStatus(ip, community,OID_DiskStatus, OID_DiksName)


if __name__ == '__main__':
    main()


