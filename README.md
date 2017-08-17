# HARMLESS

Recently, Software-Defined Networking has grown out of being an “intriguing approach” and turned into a “must-have” for communication networks to overcome many long-standing problems of traditional networking. However, there are still some obstacles on the way to the widespread adoption. Current commodity-off-the-shelf (COTS) SDN offerings are still in their infancy and are notorious for lacking standards compliance, scalability, and unpredictable performance indicators compared to their legacy counterparts. On the other hand, recent software-based solutions might mitigate these shortcomings, but in terms of cost-efficiency and port density they are in a lower league.
HARMLESS is a novel SDN switch design that combines the rapid innovation and upgrade cycles of software switches with the port density of hardware-based appliances into a fully data plane-transparent, vendor-neutral and cost-effective solution for smaller enterprises to gain a foothold in this era. Using HARMLESS you can transform your dumb legacy Ethernet switch to a powerful, fully reconfigurable, OpenFlow-enabled network device without incurring any major performance and latency penalty, nor any substantial price tag enabling to realize many use cases that would have otherwise needed standalone hardware appliances.

Video showcase is available at https://www.youtube.com/watch?v=XMxJzDcq6Hw&t

## HARMLESS architecture

![alt text](https://raw.githubusercontent.com/muuurk/harmless/master/HARMLESS.jpg)

There are three main components of HARMLESS architecture: Legacy switch, SS_1 (Software Switch 1) and SS_2 on the HARMLESS enabled server.
During operation the legacy switch is configured to tag each packet with a unique VLAN id that identifies the access port it was received from.
Then, the tagged packets are forwarded to the software switch SS_1 running on the HARMLESS-enabled-server along the trunk-port–soft-switch interconnect.
The SS_1 switch maps output ports to VLAN ids and vice versa. Since the SS_1 is connected to the SS_2 by as many patch ports as the number of managed access ports, therefore the packets are forwarded to the main OpenFlow switch (SS_2). The SS_2 is connected to the SDN controller which set up the OF pipeline. The packets go through it and finally they are sent back to the legacy switch tagged with the unique VLAN id of the proper outgoing port.

#### Example use-case:

As an example, consider the case of Host 1 and Host 2 (connected to access ports 1 and 2 identified by VLAN id 101, and 102) permitted to exchange traffic only with each other. When Host 1 sends a packet to Host 2, this is tagged with VLAN id 101 and forwarded to SS_1 via the trunk port. According to its flow table, SS_1 outputs the packet to patch port 1, through which the main OpenFlow switch (SS_2), managed directly by the SDN controller, receives it and processes it according to the OpenFlow pipeline. Based on the policy, SS 2 passes the packet back to SS 1 via patch port 2. SS 1 subsequently tags the packet with VLAN id 102 and immediately passes it towards the legacy switch which in turn removes the VLAN tag and sends the packet to Host 2 (see green dashed arrow).

## Requirements

In order to use HARMLESS, you need the following components:

 * legacy switch
 * server at least with 2 interface (for management and tunnel links)
 * virtual switch running on the server (e.g. OVS)
 * software requirements:
 	* [Napalm](https://github.com/napalm-automation/napalm) for communicating legacy switches
 	* [Open vSwitch](http://openvswitch.org/) as virtual SDN switch
 	* Python
 	* Pip

## How to use HARMLESS

1. Connect the HARMLESS server to the management port of the legacy switch
2. Fill the configuration_file.ini
	* Example configuration file is below!
3. Start harmless_manager.py
```bash
python harmless_manager.py --configuration-file=configuration_file.ini
```
4. If everything was successfull you can connect an SDN controller to the SS_2 software switch


## Tutorial: HARMLESS with OVS

In this tutorial we used the components below:

* Juniper EX2200 blade switch as legacy switch
* Acer Notebook with 2 ethernet interfaces (for management and trunk links) as HARMLESS enabled server
* Open vSwitch 2.5.2
* Floodlight as SDN controller

![alt text](https://raw.githubusercontent.com/muuurk/harmless/master/tutorial_pic.png)

We used Ubuntu 16.04.3 LTS on the notebook and 11.4R7.5 junos on the Juniper EX2200.

Prepare the switch to use HARMLESS:
* Connect it to the Notebook through the management port of the Juniper.

First of all update your system:
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

Floodlight SDN controller install:

https://floodlight.atlassian.net/wiki/display/floodlightcontroller/Installation+Guide

Clone the harmless git repository:
```bash
git clone https://github.com/muuurk/harmless.git
```

Fill in the configuration_file.ini:
```bash
[Hardware device]
#Driver of the device. e.g. Juniper - junos, Arista - eos
#Currently supported drivers: junos, eos.
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
Used_ports_for_trunk=ge-0/0/23

[HARMLESS]
#Set true if using OVS with dpdk
DPDK = false
#CPU core number
Cores = 1
#Server interfaces for trunk connection to the legacy switch
Interfaces_for_trunk= enp3s0
#Set true if using active SDN controller connection mode
Active_OF_controller = true
#IP address of the SDN controller
Contoller_listener_ip = 192.168.140.122
#Listening TCP port number of the SDN controller
Contoller_listener_port = 6653
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
Adding forwarding rules to SS_1
Pin OVS to the right cores (cm: 4) and set up RSS (1
			 Creating Virtual switches: done 🙂
###########################################################################################################
###                  Configuring HW Switch and Creating Software switches: Done                         ###
###########################################################################################################
```
After these steps the SS_2 virtual bridge had connected to the floodlight controller. You can check this on the web interface of the Floodlight:
http://127.0.0.1:8080/ui/pages/index.html

## Tutorial: HARMLESS with OVS-DPDK

This tutorial is similiar then the previos above, but here we use DPDK enabled OVS instead of the simple kernel version.

You will need to install a DPDK enabled OVS. Find the details of the installation from the link: http://docs.openvswitch.org/en/latest/intro/install/dpdk/ or follow the instructions below.

We used Open vSwitch 2.8.90.

Firstly, install DPDK:

```bash
cd /usr/src/
sudo wget http://fast.dpdk.org/rel/dpdk-17.05.1.tar.xz
sudo tar xf dpdk-17.05.1.tar.xz
export DPDK_DIR=/usr/src/dpdk-stable-17.05.1
cd $DPDK_DIR

export DPDK_TARGET=x86_64-native-linuxapp-gcc
export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET
sudo make install T=$DPDK_TARGET DESTDIR=install
```


Install OVS with DPDK:
```bash
git clone https://github.com/openvswitch/ovs.git
cd ovs

sudo apt-get install libtool
./boot.sh
./configure --with-dpdk=$DPDK_BUILD
make
```
Setup hugepages on your system. Follow the instructions in the 'Setup Hugepages' chapter:

http://docs.openvswitch.org/en/latest/intro/install/dpdk/#setup

Setup trunk interfaces to use DPDK. See details:

http://dpdk.org/doc/guides/tools/devbind.html

Fill the configuration_file.ini correctly. 
```bash
#Set true if using OVS with dpdk
DPDK = true

#If you use OVS with DPDK, fill lspci IDs of interfaces for trunk connection to the legacy switch
LSPCI_address_of_Interfaces_for_trunk =

#In case of OVS with DPDK, define here the path of the OVS
OVS_PATH=/home/user/ovs

```

Start harmless_manager.py:
```bash
python harmless_manager.py --configuration-file=configuration_file.ini
```

## Contacts

Mark Szalay - mark.szalay@tmit.bme.hu, 
Levente Csikor - csikor@tmit.bme.hu
