# Copyright 2017 Mark Szalay

import ConfigParser
import napalm
import sys
import os
import math
import copy
import subprocess

def delete_vlans_from_juniper(conf_str):

    try:
        start_index = conf_str.index("vlans {")
        opening_parenthesis = 0
        end_index = 0
        for i in range(start_index+7,len(conf_str)):
            if conf_str[i] == "{":
                opening_parenthesis += 1
            if conf_str[i] == "}" and opening_parenthesis != 0:
                opening_parenthesis -= 1
            elif conf_str[i] == "}" and opening_parenthesis == 0:
                end_index = i+1
                break

        if end_index != 0:
            starting_str = conf_str[0:start_index]
            ending_str = conf_str[end_index:]
            conf_str = starting_str+ending_str
    except:
        pass

    while "vlan {" in conf_str:
        start_index = conf_str.index("vlan {")
        opening_parenthesis = 0
        for i in range(start_index + 6, len(conf_str)):
            if conf_str[i] == "{":
                opening_parenthesis += 1
            elif conf_str[i] == "}" and opening_parenthesis != 0:
                opening_parenthesis -= 1
            elif conf_str[i] == "}" and opening_parenthesis == 0:
                end_index = i + 1
                break
        starting_str = conf_str[0:start_index]
        ending_str = conf_str[end_index:]
        conf_str = starting_str + ending_str

    while "port-mode trunk;" in conf_str:
        start_index = conf_str.index("port-mode trunk;")
        starting_str = conf_str[0:start_index]
        ending_str = conf_str[start_index+16:]
        conf_str = starting_str + ending_str
    return conf_str
def delete_vlans_from_arista(running_config):

    new_lines = []
    lines = open(running_config).readlines()

    for line in lines:
        if ("vlan" not in line) and ("trunk" not in line):
            if line.find("Vlan") == -1:
                new_lines.append(line)

    new_lines = new_lines[4:]
    temp_cfg_name = 'arista_without_vlan.conf'
    open(temp_cfg_name, 'w').writelines(new_lines)

    return temp_cfg_name

def create_cfgfile_for_juniper(vlan_if, trunks_if,handled_ports_count):
    print '\nCreate new configuration file...'

    configuration = "interfaces {"
    vlan_id = 1
    vlans = []
    for interface in vlan_if:
        configuration += "\n    " + interface + " {\n        unit 0 {\n            family ethernet-switching {\n                vlan {\n                    members vlan" + str(
            vlan_id) + ";\n                }\n            }\n        }\n    }"
        vlan_entry = {'interface': interface, 'vlan_name': "vlan" + str(vlan_id), 'vlan_id': str(100 + vlan_id)}
        vlans.append(vlan_entry)
        vlan_id += 1
    vlans_temp = copy.copy(vlans)
    for trunk in trunks_if:
        configuration += "\n    " + trunk + " {\n        unit 0 {\n            family ethernet-switching {\n                port-mode trunk;\n                vlan {\n                    members "
        configuration += "[ "
        try:
            trunk_vlans = vlans_temp[:int(handled_ports_count)]
            vlans_temp = vlans_temp[int(handled_ports_count):]
        except:
            print "except"
            trunk_vlans = vlans_temp
        print trunk_vlans
        for i in trunk_vlans:
            configuration += " " + i['vlan_name'] + " "
        configuration += " ];\n                }\n            }\n        }\n    }\n"
    configuration += "\n}\nvlans {"
    for vlan in vlans:
        configuration += "\n    " + vlan['vlan_name'] + " {\n        vlan-id " + vlan[
            'vlan_id'] + ";\n        interface {\n            " + vlan['interface'] + ".0;\n        }\n    }"
    configuration += "\n}"

    #TODO: timestamp for conf file name
    with open('junos.conf', 'w') as f:
        f.write(configuration)
    print("Create configuration file DONE:")

    return "junos.conf"
def create_cfgfile_for_arista(vlans_if, trunks_if,handled_ports_count):

    print '\nCreate new configuration file...'
    config_str = ""

    vlan_id = 101
    config_str += "!\nvlan " + str(vlan_id) + "-" + str(vlan_id+len(vlans_if)-1) + "\n!\n"
    for i in vlans_if:
        config_str += "interface " + str(i) + "\n"
        config_str += "    switchport access vlan " + str(vlan_id) + "\n!\n"
        vlan_id += 1

    vlan = 101
    for trunk in trunks_if:
        config_str += "interface " + str(trunk) + "\n"
        config_str += "    switchport trunk allowed vlan " + str(vlan) + "-" + str(int(vlan+handled_ports_count-1)) + "\n"
        config_str += "    switchport mode trunk"  + "\n!\n"
        vlan += handled_ports_count

    # TODO: timestamp for conf file name
    conf_name = "arista.conf"
    with open(conf_name, 'w') as f:
        f.write(config_str)

    return conf_name

def online_mode():
    """Load a config for the hardware device."""
    #TODO

    # Driver:
    driver = napalm.get_network_driver(config.get('Hardware device', 'Driver'))

    # Connection:
    device = driver(hostname=config.get('Hardware device', 'Host_IP'),
                    username=config.get('Hardware device', 'Username'),
                    password=config.get('Hardware device', 'Password'),
                    optional_args={'port': config.get('Hardware device', 'Port')})
    print 'Connecting to the Hardware Device...'
    device.open()

    # Get interfaces
    device_facts = device.get_facts()
    print "Device: "
    print "\t Vendor: " + device_facts['vendor']
    print "\t Model: " + device_facts['model']
    print "\t OS version : " + device_facts['os_version']

    print "\nInterfaces: "
    for interface in device_facts['interface_list']:
        print "\t" + interface

    print "\nWhat ports do you want to use to harmless?"
    vlan_if = []
    input_if = raw_input('')
    while input_if != "":
        vlan_if.append(input_if)
        input_if = raw_input('')

def offline_mode(config):
    """Load a config for the hardware device."""
    print '################################################'
    print "### Configuring Hardware device for HARMLESS ###"
    print '###########################################################################################################'

    # Driver:
    driver_name = config.get('Hardware device', 'Driver')
    driver = napalm.get_network_driver(driver_name)

    # Connection:

    # Connect:

    if(config.get('Hardware device', 'Port') is not ""):

        device = driver(hostname=config.get('Hardware device', 'Host_IP'), username=config.get('Hardware device', 'Username'),
                        password=config.get('Hardware device', 'Password'), optional_args={'port': config.get('Hardware device', 'Port')})
    else:
        device = driver(hostname=config.get('Hardware device', 'Host_IP'),
                        username=config.get('Hardware device', 'Username'),
                        password=config.get('Hardware device', 'Password'))

    print 'Connecting to the Hardware Device...'
    device.open()


    # Deleting vlans
    #TODO:rename running.conf
    print 'Currently running config was saved. Configuration file name: running.conf'
    device_config = device.get_config()
    with open('running.conf', 'w') as f:
        f.write(device_config['running'])

    # TODO: create for more driver
    if driver_name == "junos":
        tmp_vlans_cfg = delete_vlans_from_juniper(device_config['running'])
        with open('tmp_config.conf', 'w') as f:
            f.write(tmp_vlans_cfg)
        lines = open('tmp_config.conf').readlines()
        temp_cfg_name = 'junos_without_vlan.conf'
        open(temp_cfg_name, 'w').writelines(lines[3:])
        os.remove('tmp_config.conf')

    elif driver_name == "eos":
        temp_cfg_name = delete_vlans_from_arista("running.conf")


    print "Remove already existing vlans..."
    device.load_replace_candidate(filename=temp_cfg_name)
    device.commit_config()
    os.remove(temp_cfg_name)

    #Information about vlan and trunk ports
    vlan_if = config.get('Hardware device', 'Used_ports_for_vlan').split(',')
    trunks_if = config.get('Hardware device', 'Used_ports_for_trunk').split(',')
    vlan_ports_count = len(vlan_if)
    print "\nUsed vlan ports: "+str(vlan_ports_count)
    trunk_ports_count = len(trunks_if)
    print "Used trunk ports: " + str(trunk_ports_count)
    handled_ports_count = math.ceil(float(vlan_ports_count)/float(trunk_ports_count))
    print "Number of ports for one trunk: " +str(int(handled_ports_count))


    # Create vlan and trunk interfaces
    #TODO: create for more driver
    if driver_name == "junos":
        file_name = create_cfgfile_for_juniper(vlan_if, trunks_if, handled_ports_count)
    elif driver_name == "eos":
        file_name = create_cfgfile_for_arista(vlan_if, trunks_if, handled_ports_count)
    print "Trying to commit..."
    device.load_merge_candidate(filename=file_name)
    device.commit_config()
    print "Commit was successfull :)"
    os.remove(file_name)
    # close the session with the device.
    device.close()


    """
    # Note that the changes have not been applied yet. Before applying
    # the configuration you can check the changes:
    print '\nDiff:'
    print device.compare_config()


    # You can commit or discard the candidate changes.
    choice = raw_input("\nWould you like to commit these changes? [yN]: ")
    if choice == 'y':
      print 'Committing ...'
      device.commit_config()
    else:
      print 'Discarding ...'
      device.discard_config()
    """

    #-----------------------------------------------------------------------------------------

    print 'Configuring Hardware Device was successfull!'
    print '-----------------------------------------------------------------------------------'

def start_virtual_switches(patch_port_num,trunk_port_num):
    print "Create and start virtual switches"
    subprocess.call("./virtual_switch_starter.sh " + str(patch_port_num) + " " + str(trunk_port_num),shell=True)

    #cmd = "xterm -hold -e /home/szalay/harmless/virtual_switch_starter.sh 2 2"
    # no block, it start a sub process.
    #p = subprocess.Popen(cmd , shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # and you can block util the cmd execute finish
    #p.wait()

    #TODO: Create a picture about the connections (wiring)


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print "Start online mode"
        sys.exit(1)

    else:
        config = ConfigParser.ConfigParser()
        config.read("configuration_file.ini")
        patch_port_num = len(config.get('Hardware device', 'Used_ports_for_vlan').split(','))
        trunk_port_num = len(config.get('Hardware device', 'Used_ports_for_trunk').split(','))
        #config_file = sys.argv[1]
        offline_mode(config)
        print '###############################################'
        print "### Creating Software switches for HARMLESS ###"
        print '###########################################################################################################'
        #start_virtual_switches(patch_port_num, trunk_port_num)
        print "DONE"