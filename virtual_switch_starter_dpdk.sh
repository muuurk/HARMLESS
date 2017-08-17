#!/bin/bash
DBR="SS_1"
DBR2="SS_2"

function print_help
{
  echo -e $1
  echo -e "Usage: ./virtual_switch_starter_dpdk.sh <number_of_patch_ports> <number_of_trunk_ports>"
  exit -1
}


patch_ports_count=$1
trunk_ports_count=$2
ptcp_port=16633

#Read from configuration file
config_file="configuration_file.ini"
OVS_PATH=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep OVS_PATH | cut -f2 -d'"'`
num_cores=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Host_IP | cut -f2 -d'"'`
trunk_lspci_addresses=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep LSPCI_address_of_Interfaces_for_trunk | cut -f2 -d'"'`
listening_port=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Contoller_listener_port | cut -f2 -d'"'`
listening_ip=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Contoller_listener_ip | cut -f2 -d'"'`
is_active=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Active_OF_controller | cut -f2 -d'"'`

is_dpdk=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep DPDK | cut -f2 -d'"'`


case $num_cores in
  1)
    c=2
    r=1
    pinning="0:1"
  ;;
  2)
    c=6
    r=2
    pinning="0:1,1:2"
  ;;
  3)
    c=e
    r=3
    pinning="0:1,1:2,2:3"
  ;;
  4)
    c=1e
    r=4
    pinning="0:1,1:2,2:3,3:4"
  ;;
  5)
    c=3e
    r=5
    pinning="0:1,1:2,2:3,3:4,4:5"
  ;;
  6)
    c=7e
    r=6
    pinning="0:1,1:2,2:3,3:4,4:5,5:6"
  ;;
  *)
    c=4
    r=1
    pinning="0:1"

  ;;
esac

sudo /sbin/modprobe openvswitch

echo "Delete preconfigured ovs data"
sudo rm -rf /usr/local/etc/openvswitch/conf.db

echo "Create ovs database structure"
sudo $OVS_PATH/ovsdb/ovsdb-tool create /usr/local/etc/openvswitch/conf.db  $OVS_PATH/vswitchd/vswitch.ovsschema

echo "Start ovsdb-server..."
sudo $OVS_PATH/ovsdb/ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock --remote=db:Open_vSwitch,Open_vSwitch,manager_options --pidfile --detach

echo "exporting environmental variable"
export DB_SOCK=/usr/local/var/run/openvswitch/db.sock

echo "Initializing"
sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=true
echo "Setup dpdk params..."
sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-lcore-mask=$c
#sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-socket-mem="1024,0"
#sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-hugepage-dir="/mnt/huge"
sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask=$c

echo "start vswitchd..."
sudo $OVS_PATH/vswitchd/ovs-vswitchd   unix:$DB_SOCK --pidfile --detach

echo "Create dpdk-bridges"
sudo $OVS_PATH/utilities/ovs-vsctl add-br $DBR -- set bridge $DBR datapath_type=netdev
sudo $OVS_PATH/utilities/ovs-vsctl add-br $DBR2 -- set bridge $DBR2 datapath_type=netdev

echo "Delete original flows from software switches"
sudo ovs-ofctl del-flows $DBR
sudo ovs-ofctl del-flows $DBR2

echo "Add logical patch ports"
for pp in $(seq 1 $patch_ports_count)
do
  cmd="sudo $OVS_PATH/utilities/ovs-vsctl add-port ${DBR} patch-ovs-${pp} -- set Interface patch-ovs-${pp} type=patch"
  $cmd
  vlan=$(expr 100 + $pp)
  cmd2="sudo $OVS_PATH/utilities/ovs-vsctl add-port $DBR2 patch-ovs-${vlan} -- set Interface patch-ovs-${vlan} type=patch"
  $cmd2
  cmd3="sudo $OVS_PATH/utilities/ovs-vsctl set Interface patch-ovs-${pp} options:peer=patch-ovs-${vlan}"
  $cmd3
  cmd4="sudo $OVS_PATH/utilities/ovs-vsctl set Interface patch-ovs-${vlan} options:peer=patch-ovs-${pp}"
  $cmd4
done

echo "Add physical dpdk trunk ports"
for i in $(seq 1 $trunk_ports_count)
do
    trunk=`echo $trunk_lspci_addresses | cut -f1 -d','`
    trunk_lspci_addresses=`echo $trunk_lspci_addresses | cut -f2 -d','`

    cmd="sudo $OVS_PATH/utilities/ovs-vsctl add-port $DBR $trunk -- set Interface $trunk type=dpdk options:dpdk-devargs=$trunk"
    $cmd
    
done

if [ "$is_active" == "false" ]
then
  echo "Add passive controller listener port on ${listening_port}"
  sudo $OVS_PATH/utilities/ovs-vsctl set-controller $DBR2 ptcp:$listening_port
else
  echo "Add active controller listener port on ${listening_port}"
  sudo $OVS_PATH/utilities/ovs-vsctl set-controller $DBR2 tcp:$listening_ip:$listening_port
fi

echo "Adding forwarding rules to ${DBR}"
phy_if_out=`expr $patch_ports_count + 1`
part_math=`expr $trunk_ports_count - 1`
part_math2=`expr $patch_ports_count + $part_math`
for_one_trunk=`expr $part_math2 / $trunk_ports_count`

cur_count=1
for pp in $(seq 1 $patch_ports_count)
do
  vlan=$(expr 100 + $pp)
  add_port="sudo ovs-ofctl add-flow ${DBR} dl_vlan=${vlan},actions=strip_vlan,output:${pp}"
  $add_port

  next_if=`expr $cur_count % $for_one_trunk`
  add_port2="sudo ovs-ofctl add-flow ${DBR} in_port=${pp},actions=mod_vlan_vid:${vlan},output:${phy_if_out}"

  if [ "$next_if" == 0 ]
  then
    phy_if_out=`expr $phy_if_out + 1`
    cur_count=0
  fi
  cur_count=`expr $cur_count + 1`
  $add_port2
done

echo "Pin OVS to the right cores (cm: ${c}) and set up RSS (${r}"
#sudo $OVS_PATH/utilities/ovs-vsctl set interface dpdk1 options:n_rxq=$r other_config:pmd-rxq-affinity=$pinning
sudo $OVS_PATH/utilities/ovs-vsctl set Open_vSwitch . other_config:n-dpdk-rxqs=$r

#echo "This is the pinning:"
#sudo $OVS_PATH/utilities/ovs-appctl dpif-netdev/pmd-rxq-show

echo -e "\t\t\t Creating DPDK Virtual switches: done :)"
