# Copyright 2017 Mark Szalay

import ConfigParser
import napalm
import sys, getopt
import os
import math
import copy
import subprocess
import time

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

    with open('tmp_config.conf', 'w') as f:
        f.write(conf_str)
    lines = open('tmp_config.conf').readlines()
    temp_cfg_name = 'junos_without_vlan.conf'
    open(temp_cfg_name, 'w').writelines(lines[3:])
    os.remove('tmp_config.conf')

    return "junos_without_vlan.conf"

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
        for i in trunk_vlans:
            configuration += " " + i['vlan_name'] + " "
        configuration += " ];\n                }\n            }\n        }\n    }\n"
    configuration += "\n}\nvlans {"
    for vlan in vlans:
        configuration += "\n    " + vlan['vlan_name'] + " {\n        vlan-id " + vlan[
            'vlan_id'] + ";\n        interface {\n            " + vlan['interface'] + ".0;\n        }\n    }"
    configuration += "\n}"

    with open("junos_with_vlan.cfg", 'w') as f:
        f.write(configuration)

    return "junos_with_vlan.cfg"

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

    conf_name = "arista.conf"
    with open(conf_name, 'w') as f:
        f.write(config_str)

    return conf_name

def reset_device(device,orig_cfg):
    print "Reset HW device to " +orig_cfg + " state"
    try:
        device.load_replace_candidate(filename=orig_cfg)
        device.commit_config()
        os.remove(orig_cfg)
        print "DONE"
    except Exception as e:
        print "ERROR: " + str(e)
        os.remove(orig_cfg)
        sys.exit(1)

def load_driver(config):

    try:
        driver_name = config.get('Hardware device', 'Driver')
        driver = napalm.get_network_driver(driver_name)
    except Exception as e:
        print "ERROR: "+str(e)
        print "ERROR: Probably napalm does not support the given '" + str(driver_name) + "' driver. Check this website: http://napalm.readthedocs.io/en/latest/support/"
        sys.exit(1)

    return driver, driver_name

def delete_vlans(device,driver_name):
    try:
        device_config = device.get_config()
        old_config_name = str(driver_name) + "_" + time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()) + "_original.cfg"
        with open(old_config_name, 'w') as f:
            f.write(device_config['running'])
        print "Currently running config was saved. Configuration file name: " + old_config_name
    except Exception as e:
        print "ERROR: "+str(e)
        sys.exit(1)


    # TODO: create for more driver
    if driver_name == "junos":
        temp_cfg_name = delete_vlans_from_juniper(device_config['running'])

    elif driver_name == "eos":
        temp_cfg_name = delete_vlans_from_arista("old_config_name")


    print "Remove already existing vlans..."
    try:
        device.load_replace_candidate(filename=temp_cfg_name)
        device.commit_config()
        os.remove(temp_cfg_name)
    except Exception as e:
        print "ERROR: " + str(e)
        os.remove(temp_cfg_name)
        sys.exit(1)

def upload_new_config(config,driver_name,device,backup_config_name):
    # Information about vlan and trunk ports
    vlan_if = config.get('Hardware device', 'Used_ports_for_vlan').split(',')
    trunks_if = config.get('Hardware device', 'Used_ports_for_trunk').split(',')
    vlan_ports_count = len(vlan_if)
    print "\nUsed vlan ports: " + str(vlan_ports_count)
    trunk_ports_count = len(trunks_if)
    print "Used trunk ports: " + str(trunk_ports_count)
    handled_ports_count = math.ceil(float(vlan_ports_count) / float(trunk_ports_count))
    print "Number of ports for one trunk: " + str(int(handled_ports_count))

    # Create vlan and trunk interfaces
    # TODO: create for more driver
    print "\nCreate new configuration file"
    if driver_name == "junos":
        file_name = create_cfgfile_for_juniper(vlan_if, trunks_if, handled_ports_count)
    elif driver_name == "eos":
        file_name = create_cfgfile_for_arista(vlan_if, trunks_if, handled_ports_count)
    print "Trying to commit..."
    try:
        device.load_merge_candidate(filename=file_name)
        device.commit_config()
    except Exception as e:
        print "ERROR: " + str(e)
        os.remove(file_name)
        reset_device(device, backup_config_name)
        sys.exit(1)
    print "Commit was successfull :)"
    os.remove(file_name)

def connect_to_device(config,driver):
    if (config.get('Hardware device', 'Port') is not ""):

        device = driver(hostname=config.get('Hardware device', 'Host_IP'),
                        username=config.get('Hardware device', 'Username'),
                        password=config.get('Hardware device', 'Password'),
                        optional_args={'port': config.get('Hardware device', 'Port')})
    else:
        device = driver(hostname=config.get('Hardware device', 'Host_IP'),
                        username=config.get('Hardware device', 'Username'),
                        password=config.get('Hardware device', 'Password'))

    print 'Connecting to the Hardware Device...'
    try:
        device.open()
    except Exception as e:
        print "ERROR: " + str(e)
        sys.exit(1)

    return device

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

def backup_mode(new_cfg, config):
    """ UpLoad a backup configuration to the hardware device."""

    #Init used driver:
    driver, driver_name = load_driver(config)

    #Connecting to the device:
    device = connect_to_device(config,driver)

    #Reset device with an older cfg
    reset_device(device, new_cfg)

    device.close()
    print 'Reset Hardware Device to earlier state was successfull!'
    print '------------------------------------------------------------------------------------------------------------'

def offline_mode(config):
    """ UpLoad the HARMLESS configuration to the hardware device."""

    #Init used driver:
    driver, driver_name = load_driver(config)

    #Connecting to the device:
    device = connect_to_device(config,driver)

    #Deleting existing vlans
    backup_config_name = delete_vlans(device, driver_name)

    #Creating and uploading new configuration
    upload_new_config(config, driver_name, device, backup_config_name)

    # close the session with the device.
    device.close()
    print 'Configuring Hardware Device was successfull!'
    print '------------------------------------------------------------------------------------------------------------'

def start_virtual_switches(patch_port_num,trunk_port_num):
    print "Stop previously started virtual switch if it's alive"
    subprocess.call("./stop_ovs.sh " + str(patch_port_num) + " " + str(trunk_port_num), shell=True,stderr=False)
    print '------------------------------------------------------------------------------------------------------------'
    
    print "Create and start virtual switches"
    subprocess.call("./virtual_switch_starter_U16.sh " + str(patch_port_num) + " " + str(trunk_port_num),shell=True,stderr=False)
    #subprocess.call("./star_virtual_switch.sh " + str(patch_port_num) + " " + str(trunk_port_num), shell=True)

    #TODO: Create a picture about the connections (wiring)

def main(argv):

    running_mode = None
    config_file = None

    try:
        opts, args = getopt.getopt(argv,"", ["help", "configuration-file=","upload-cfg="])
    except getopt.GetoptError:
        print "Bad parameter!\nUse 'python harmless_manager.py --help'"
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--help":
            print "Usage: python harmless_manager.py <params>\nParams:\n\t--configuration-file=<config file>\n\t--upload-cfg=<config_file>"
            sys.exit(1)
        elif opt in ("--configuration-file="):
            config_file = arg
        elif opt in ("--upload-cfg="):
            new_cfg = arg
            running_mode = "backup_device"
        elif opt in ("--online-mode"):
            running_mode = "online"
        else:
            print 'Bad parameters! Use python harmless_manager.py --help'
            sys.exit(1)

    try:
        config = ConfigParser.ConfigParser()
        config.read(config_file)
    except Exception as e:
        print "ERROR: " + str(e)
        print "ERROR: Probably the configuration file name '" + str(
            config_file) + "' is not correct! Please use: python harmless_manager.py --help"
        sys.exit(1)

    if running_mode == "online":
        print "Online mode currently is not implemented yet."
        sys.exit(1)

    elif running_mode == "backup_device":
        backup_mode(new_cfg, config)

    else:

        print '################################################'
        print "### Configuring Hardware device for HARMLESS ###"
        print '###########################################################################################################'
        offline_mode(config)
        print '###############################################'
        print "### Creating Software switches for HARMLESS ###"
        print '###########################################################################################################'
        patch_port_num = len(config.get('Hardware device', 'Used_ports_for_vlan').split(','))
        trunk_port_num = len(config.get('Hardware device', 'Used_ports_for_trunk').split(','))
        start_virtual_switches(patch_port_num, trunk_port_num)
        print '###########################################################################################################'
        print "###                  Configuring HW Switch and Creating Software switches: Done                         ###"
        print '###########################################################################################################'


if __name__ == '__main__':
    main(sys.argv[1:])
