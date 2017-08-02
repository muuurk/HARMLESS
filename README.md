# HARMLESS

Recently, Software-Defined Networking has grown out of being an “intriguing approach” and turned into a “must-have” for communication networks to overcome many long-standing problems of traditional networking. However, there are still some obstacles on the way to the widespread adoption. Current commodity-off-the-shelf (COTS) SDN offerings are still in their infancy and are notorious for lacking standards compliance, scalability, and unpredictable performance indicators compared to their legacy counterparts. On the other hand, recent software-based solutions might mitigate these shortcomings, but in terms of cost-efficiency and port density they are in a lower league.
Here, we present HARMLESS, a novel SDN switch design that combines the rapid innovation and upgrade cycles of software switches with the port density of hardware-based appliances into a fully data plane-transparent, vendor-neutral and cost-effective solution for smaller enterprises to gain a foothold in this era. The demo showcases the SDN migration of a dumb legacy Ethernet switch to a powerful, fully recongurable, OpenFlow-enabled network device without incurring any major performance and latency penalty, nor any substantial price tag enabling to realize many use cases that would have otherwise needed standalone hardware appliances.

## Requirements

In order to use HARMLESS, you need to the following components:

 * legacy switch
 * virtual switch running on a server (e.g. OVS)
 * software requirements:
 	* [Napalm](https://github.com/napalm-automation/napalm) for communicating legacy switches
 	* [OpenvSwitch](http://openvswitch.org/) as virtual SDN switch

## How to use HARMLESS

### Connect the HARMLESS server to the legacy switch

### Start HARMLESS

Firstly fill in the configuration_file.ini file.


## Tutorial: HARMLESS with OVS

In this tutorial we used the components below:

* Juniper EX2200 blade switch as legacy switch
* Notebook which contains 2 interfaces (for management and trunk links)
* Open vSwitch 2.5.2
* Floodlight




First of all run an update on your system:
```bash
sudo apt-get update
```


You will need to install [OVS](http://openvswitch.org/):
```bash
sudo apt install openvswitch-switch
```

Napalm install:
```bash
sudo apt install python-pip
pip install napalm
```

Clone the harmless git repository:
```bash
git clone https://github.com/muuurk/harmless.git
```

Fill in the configuration_file.ini:
```bash
[Hardware device]
#Driver of the device. e.g. Juniper - junos, Arista - eos
Driver = junos
#Management IP address of the legacy switch
Host_IP = 10.2.1.6
#User and pass of the legacy switch
Username = ****
Password = ****
#TCP port number for connection
Port =

#Device interfaces as SDN interfaces
Used_ports_for_vlan=ge-0/0/0,ge-0/0/1
#Device interfaces for trunk links between the legacy and the virtual switch
Used_ports_for_trunk=ge-0/0/2

[HARMLESS]
#Set true if using OVS with dpdk
DPDK = false
#CPU core number
Cores = 1
#Server interfaces for trunk connection to the legacy switch
Interfaces_for_trunk= veth1
#Set trus if using active SDN controller connection mode
Active_OF_controller = false
#IP address of the SDN controller
Contoller_listener_ip = 192.168.41.44
#Listening TCP port number of the SDN controller
Contoller_listener_port = 6633
```

Start harmless_manager.py:
```bash
python harmless_manager.py --configuration-file=configuration_file.ini
```
The output should be something like this:
```bash
################################################
### Configuring Hardware device for HARMLESS ###
###########################################################################################################
Connecting to the Hardware Device...
Currently running config was saved. Configuration file name: junos_2017-08-02_13:25:09_original.cfg
Remove already existing vlans...

Used vlan ports: 3
Used trunk ports: 1
Number of ports for one trunk: 3

Create new configuration file
Trying to commit...
Commit was successfull 🙂
Configuring Hardware Device was successfull!
------------------------------------------------------------------------------------------------------------
###############################################
### Creating Software switches for HARMLESS ###
###########################################################################################################
Stop previously started virtual switch if it is alive
Killing the whole process tree of OVS
			[DONE]
Removing openvswitch module...
			[DONE]
Check the following ps aux output:

------------------------------------------------------------------------------------------------------------
Create and start virtual switches
Delete preconfigured ovs data
Create ovs database structure
Start ovsdb-server...
2017-08-02T13:25:41Z|00001|vlog|INFO|opened log file /var/log/openvswitch/ovsdb-server.log
Initializing
exporting environmental variable
start vswitchd...
2017-08-02T13:25:41Z|00001|vlog|INFO|opened log file /var/log/openvswitch/ovs-vswitchd.log
2017-08-02T13:25:41Z|00002|ovs_numa|INFO|Discovered 2 CPU cores on NUMA node 0
2017-08-02T13:25:41Z|00003|ovs_numa|INFO|Discovered 1 NUMA nodes and 2 CPU cores
2017-08-02T13:25:41Z|00004|reconnect|INFO|unix:/var/run/openvswitch/db.sock: connecting...
2017-08-02T13:25:41Z|00005|reconnect|INFO|unix:/var/run/openvswitch/db.sock: connected
Create dpdk-bridges (dpdk_br)
Delete flows from dpdk_br
Add logical patch ports
Add physical trunk ports
Add passive controller listener port on 6633
Adding forwarding rules to SoftSW_1
Pin OVS to the right cores (cm: 4) and set up RSS (1
			 Creating Virtual switches: done 🙂
###########################################################################################################
###                  Configuring HW Switch and Creating Software switches: Done                         ###
###########################################################################################################
```
