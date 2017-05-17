# Copyright 2017 Mark Szalay

import ConfigParser
import napalm
import sys
import os
import math
import copy

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


def main(config):
    """Load a config for the hardware device."""
    # Driver:
    driver = napalm.get_network_driver(config.get('Hardware device', 'Driver'))

    # Connection:
    device = driver(hostname=config.get('Hardware device', 'Host_IP'), username=config.get('Hardware device', 'Username'),
                    password=config.get('Hardware device', 'Password'), optional_args={'port': config.get('Hardware device', 'Port')})
    print 'Connecting to the Hardware Device...'
    device.open()

    # Deleting vlans
    #TODO:rename running.conf
    print 'Currently running config was saved. Configuration file name: running.conf'
    device_config = device.get_config()
    with open('running.conf', 'w') as f:
        f.write(device_config['running'])

    del_vlans_cfg = delete_vlans_from_juniper(device_config['running'])

    with open('tmp_without_vlan.conf', 'w') as f:
        f.write(del_vlans_cfg)
    lines = open('tmp_without_vlan.conf').readlines()
    open('junos_without_vlan.conf', 'w').writelines(lines[3:])

    print "Upload new configuration..."
    device.load_replace_candidate(filename='tmp_without_vlan.conf')
    device.commit_config()

    #Get interfaces
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
    print "Selected interfaces:\n" + str(vlan_if)

    print "\nAdd trunk interfaces: (interface1,interface2,...)"
    trunks = []
    input_if = raw_input('')
    while input_if != "":
        trunks.append(input_if)
        input_if = raw_input('')

    print "Selected trunk interfaces:\n"+str(trunks)

    #vlans and trunks connection
    vlan_ports = len(vlan_if)
    print "vlan ports: "+str(vlan_ports)
    trunk_ports = len(trunks)
    print "trunk ports: " + str(trunk_ports)
    handled_ports = float(vlan_ports)/float(trunk_ports)
    print "handled ports: " + str(handled_ports)
    handled_ports = math.ceil(float(vlan_ports)/float(trunk_ports))
    print "handled ports: " +str(handled_ports)


    # Create vlan
    print '\nCreate configuration file...'

    configuration = "interfaces {"
    vlan_id = 1
    vlans = []
    for interface in vlan_if:
        configuration += "\n    " + interface + " {\n        unit 0 {\n            family ethernet-switching {\n                vlan {\n                    members vlan" + str(vlan_id) + ";\n                }\n            }\n        }\n    }"
        vlan_entry = {'interface': interface, 'vlan_name': "vlan" + str(vlan_id), 'vlan_id': str(100+vlan_id)}
        vlans.append(vlan_entry)
        vlan_id += 1
    vlans_temp = copy.copy(vlans)
    for trunk in trunks:
        configuration += "\n    "+trunk+" {\n        unit 0 {\n            family ethernet-switching {\n                port-mode trunk;\n                vlan {\n                    members "
        configuration += "[ "
        try:
            trunk_vlans = vlans_temp[:int(handled_ports)]
            vlans_temp = vlans_temp[int(handled_ports):]
        except:
            print "except"
            trunk_vlans = vlans_temp
        print trunk_vlans
        for i in trunk_vlans:
            configuration += " " + i['vlan_name'] + " "
        configuration += " ];\n                }\n            }\n        }\n    }\n"
    configuration += "\n}\nvlans {"
    for vlan in vlans:
        configuration += "\n    "+vlan['vlan_name'] + " {\n        vlan-id "+vlan['vlan_id']+";\n        interface {\n            "+vlan['interface']+".0;\n        }\n    }"
    configuration += "\n}"

    with open('junos.conf', 'w') as f:
        f.write(configuration)

    print("Create configuration file DONE:")



    device.load_merge_candidate(filename='junos.conf')

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

    # close the session with the device.
    device.close()

    #-----------------------------------------------------------------------------------------

    print 'Done.'

if __name__ == '__main__':
    """
    if len(sys.argv) < 2:
        print 'Please supply the full path to your configuration file'
        sys.exit(1)
    """

    config = ConfigParser.ConfigParser()
    config.read("configuration_file.ini")
    #config_file = sys.argv[1]
    main(config)