#!/bin/bash
DBR="SoftSW_1"
DBR2="SoftSW_2"

function print_help
{
  echo -e $1
  echo -e "Usage: ./virtual_switch_starter.sh <number_of_patch_ports> <number_of_trunk_ports>"
  exit -1
}

#Read from configuration file
config_file="configuration_file.ini"
num_cores=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Host_IP | cut -f2 -d'"'`
trunk_ports=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Interfaces_for_trunk | cut -f2 -d'"'`
listening_port=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Contoller_listener_port | cut -f2 -d'"'`
listening_ip=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Contoller_listener_ip | cut -f2 -d'"'`
is_active=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep Active_OF_controller | cut -f2 -d'"'`
#TODO: create tolower
is_dpdk=`awk -F ' *= *' '{ if ($1 ~ /^\[/) section=$1; else if ($1 !~ /^$/) print $1 section "=" "\"" $2 "\"" }' $config_file | grep DPDK | cut -f2 -d'"'`
#TODO: create tolower

patch_ports_count=$1
trunk_ports_count=$2

case $num_cores in
  1)
    c=4
    r=1
  ;;
  2)
    c=6
    r=2
  ;;
  3)
    c=e
    r=3
  ;;
  4)
    c=1e
    r=4
  ;;
  5)
    c=3e
    r=5
  ;;
  6)
    c=7e
    r=6
  ;;
  *)
    c=4
    r=1
  ;;
esac

sudo /sbin/modprobe openvswitch

echo "Delete preconfigured ovs data"
sudo rm -rf /usr/local/etc/openvswitch/conf.db

echo "Create ovs database structure"
sudo ovsdb-tool create /usr/local/etc/openvswitch/conf.db     /usr/share/openvswitch/vswitch.ovsschema

echo "Start ovsdb-server..."
sudo ovsdb-server /usr/local/etc/openvswitch/conf.db --remote=punix:/usr/local/var/run/openvswitch/db.sock     --remote=db:Open_vSwitch,Open_vSwitch,manager_options     --private-key=db:Open_vSwitch,SSL,private_key     --certificate=db:Open_vSwitch,SSL,certificate     --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert     --pidfile --detach --log-file

echo "Initializing"
sudo ovs-vsctl --no-wait init

echo "exporting environmental variable"
export DB_SOCK=/usr/local/var/run/openvswitch/db.sock

echo "start vswitchd..."
sudo ovs-vswitchd unix:$DB_SOCK --pidfile --detach --log-file

echo "Create dpdk-bridges (dpdk_br)"
sudo ovs-vsctl add-br $DBR -- set bridge $DBR datapath_type=netdev
sudo ovs-vsctl add-br $DBR2 -- set bridge $DBR2 datapath_type=netdev

echo "Delete flows from dpdk_br"
sudo ovs-ofctl del-flows $DBR
sudo ovs-ofctl del-flows $DBR2

echo "Add logical patch ports"

for pp in $(seq 1 $patch_ports_count)
do
  cmd="sudo ovs-vsctl add-port ${DBR} patch-ovs-${pp} -- set Interface patch-ovs-${pp} type=patch"
  $cmd
  vlan=$(expr 100 + $pp)
  cmd2="sudo ovs-vsctl add-port $DBR2 patch-ovs-${vlan} -- set Interface patch-ovs-${vlan} type=patch"
  $cmd2
  cmd3="sudo ovs-vsctl set Interface patch-ovs-${pp} options:peer=patch-ovs-${vlan}"
  $cmd3
  cmd4="sudo ovs-vsctl set Interface patch-ovs-${vlan} options:peer=patch-ovs-${pp}"
  $cmd4
done
echo "Add physical trunk ports"
for i in $(seq 1 $trunk_ports_count)
do
    trunk=`echo $trunk_ports | cut -f1 -d','`
    trunk_ports=`echo $trunk_ports | cut -f2 -d','`

    #TODO: start ovs without DPDK
    if [ "$is_dpdk" == "true" ]
    then
        cmd="sudo ovs-vsctl add-port $DBR $trunk -- set Interface $trunk type=dpdk"
        $cmd
    else
        #TODO: Read trunk ports from configFile
        sudo ovs-vsctl add-port $DBR $trunk
    fi

done

if [ "$is_active" == "false" ]
then
  echo "Add passive controller listener port on ${listening_port}"
  sudo ovs-vsctl set-controller $DBR2 ptcp:$listening_port
else
  echo "Add active controller listener port on ${listening_port}"
  sudo ovs-vsctl set-controller $DBR2 tcp:$listening_ip:$listening_port
fi


echo "Adding forwarding rules to ${DBR}"

phy_if_out=`expr $patch_ports_count + 1`
part_math=`expr $trunk_ports_count - 1`
part_math2=`expr $patch_ports_count + $part_math`
for_one_trunk=`expr $part_math2 / $trunk_ports_count`

for pp in $(seq 1 $patch_ports_count)
do
  vlan=$(expr 100 + $pp)
  add_port="sudo ovs-ofctl add-flow ${DBR} dl_vlan=${vlan},actions=strip_vlan,output:${pp}"
  $add_port

  next_if=`expr $patch_ports_count % $for_one_trunk`
  add_port2="sudo ovs-ofctl add-flow ${DBR} in_port=${pp},actions=mod_vlan_vid:${vlan},output:${phy_if_out}"

  if [ "$next_if" == 0 ]
  then
    phy_if_out=`expr $phy_if_out + 1`
  fi
  $add_port2
done

echo "Pin OVS to the right cores (cm: ${c}) and set up RSS (${r}"
sudo ovs-vsctl set Open_vSwitch . other_config:pmd-cpu-mask=$c
sudo ovs-vsctl set Open_vSwitch . other_config:n-dpdk-rxqs=$r

echo -e "\t\t\t Creating Virtual switches: done :)"

