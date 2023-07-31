#!/usr/bin/python3.6


import getopt, sys,subprocess, re, os
from datetime import timedelta

# Exit Code
ExitOK = 0
ExitWarning = 1
ExitCritical = 2
ExitUNKNOWN = 3

#OID Description interface
Desc = "IF-MIB::ifDescr"

#OID Out Octet
Out = 'IF-MIB::ifOutOctets'

#OID MIB In Octet
In = 'IF-MIB::ifInOctets'

# Function to convert bytes to GB
def octet_to_gb(bytes):
    return round(int(bytes) / (1024 ** 2), 2)

def GetValue(snmpret):
    return snmpret.split('=')[1].split(':')[-1].replace('"','').replace('\n','')

def snmp_walk(ip, community, oid):
    print("snmpwalk")        
    cmd = "snmpwalk -v 2c -c {} {} {}".format(community, ip, oid)
    try:
        output = subprocess.check_output(cmd, shell=True)
        return output.decode()
    except subprocess.CalledProcessError as e:
        ReturnNagios(3,"Error occured: {}".format("Output : {}".format(e.output)))

def snmp_get(ip, community, oid):
    cmd = "snmpget -v2c -c {} {} {}".format(community, ip, oid)
    try:
        output = subprocess.check_output(cmd, shell=True)
        return output.decode()
    except subprocess.CalledProcessError as e:
        ReturnNagios(3,"Error occured: {}".format("Output : {}".format(e.output)))

def GetValue(snmpret):
    return snmpret.split('=')[1].split(':')[-1].replace('"','').replace('\n','').replace(' ','')


def GetIndex(snmpret):
    print(snmpret)
    return snmpret.split('=')[0].split('.')[1].replace(' ','')


def CalculBdPass(NewValue, OldValue):
    Out = ""
    for Value in NewValue.keys():
        Data = "{}: In {} Ko, Out {} Ko".format(NewValue[Value][1], (int(NewValue[Value][2]) - int(OldValue[Value][2])) /1000, (int(NewValue[Value][2]) - int(OldValue[Value][2])) /1000 )
        if Out == "":
            Out = "{}".format(Data)
        else:
            Out = "{},{}".format(Out,Data)

    return Out

def TestFile(File):
    return os.path.exists(File)


def CollectValue(ip,community,Desc,Out,In, NewValue):
    
    for Walk in  snmp_walk(ip, community, Desc).split('\n'):
        if Walk:
            GetIndex(Walk)
            NewValue[GetIndex(Walk)] = [GetIndex(Walk), GetValue(Walk), "", ""]
    for Walk in  snmp_walk(ip, community, Out).split('\n'):
        if Walk:
            GetIndex(Walk)
            NewValue[GetIndex(Walk)] = [NewValue[GetIndex(Walk)][0], NewValue[GetIndex(Walk)][1], GetValue(Walk), ""]
    for Walk in  snmp_walk(ip, community, In).split('\n'):
        if Walk:
            GetIndex(Walk)
            NewValue[GetIndex(Walk)] = [NewValue[GetIndex(Walk)][0], NewValue[GetIndex(Walk)][1], NewValue[GetIndex(Walk)][2], GetValue(Walk)]
    return NewValue

def FileWrite(File,NewValue):
	try:
		with open(File, "w") as text_file:

			for i in NewValue.keys():
				text_file.write("{};{};{};{}\n".format(NewValue[i][0],NewValue[i][1],NewValue[i][2],NewValue[i][3]))
		text_file.close
	except IOError:
		ReturnNagios(2,"Error " + File)

def FileRead(File,OldValue):
	
	if TestFile(File):	
		with open(File) as file:
			for line in file:
				OldValue[line.split(';')[0]] = [line.split(';')[1],line.split(';')[2],line.split(';')[3]]
	else:
		ReturnNagios(3,"Fichier : {} erreur".format(File))
	return OldValue

def Interface(ip,community,Desc,Out,In):

    File = "/tmp/{}".format(ip)
    OldValue = {}
    NewValue = {}
    if TestFile(File) == False:
        NewValue = CollectValue(ip,community,Desc,Out,In, NewValue)
        FileWrite(File,NewValue)
        ReturnNagios(3,"Fichier : {} erreur".format(File))
    else:
        OldValue = FileRead(File,OldValue)
        NewValue = CollectValue(ip,community,Desc,Out,In, NewValue)
        FileWrite(File,NewValue)        
        ReturnNagios(1,CalculBdPass(NewValue, OldValue))

    

def Print_Help():
    print("Utilisation: check_livebox.py -i IP -c community -W warning -C critical -s check")
    print("Options:")
    print("-i, --ip		Adresse IP de votre Synology")
    print("-c, --community	Community SNMP de votre Synology")
    print("-W, --warning	Seuil d avertissement en pourcentage")
    print("-C, --critical	Seuil critique en pourcentage")
    print("Exemple: check_livebox.py -i 192.168.1.10 -c public -W 80 -C 90 ")

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
    warning = 80
    critical = 90
    check = None
    help = False
    try:
        opts, args = getopt.getopt(argv, "i:c:v:V:W:C:s:", ["ip=", "community=", "version=", "warning=","critical=", "check="])
    except getopt.GetoptError:
        print("check_livebox.py -i <ip> -c <community> -v <version> -u <unit> -s <check>")
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-i", "--ip"):
            ip = arg
        elif opt in ("-c", "--community"):
            community = arg
        elif opt in ("-v", "--version"):
            version = arg
        elif opt in ("-W", "--warning"):
            warning = arg
        elif opt in ("-C", "--critical"):
            critical = arg 
        elif opt in ("-s", "--check"):
            check = arg    
        elif opt in ("-h", "--help"):
            help = True                       
    if not (ip and community and version):
            print("check_livebox.py -i <ip> -c <community> -v <version> [-W <warning>] [-C <critical>] [-s <check>]")
            sys.exit(2)     
    return ip, community, version, warning, critical, check


def main():

	ip, community, version, warning, critical, check = parse_args(sys.argv[1:])

	if check == 'Interface':
		Interface(ip,community,Desc,Out,In)
	elif help:
		Print_Help()
	else:
		Print_Help()


if __name__ == '__main__':
    main()
