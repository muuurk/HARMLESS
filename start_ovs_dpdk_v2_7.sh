#!/bin/bash
OVS_PATH="/home/user/ovs"
DBR="ovsbr"
num_cores=$1
ptcp_port=16633
if [ $# -ne 1 ]
then
  echo "No num cores was set!"
  echo "Usage: ./start_ovs_dpdk.sh [NUM_CORES]"
  exit -1
fi

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
sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-socket-mem="128,0"
#sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-hugepage-dir="/mnt/huge"
sudo $OVS_PATH/utilities/ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask=$c


echo "start vswitchd..."
sudo $OVS_PATH/vswitchd/ovs-vswitchd   unix:$DB_SOCK --pidfile --detach
sleep 5
echo "Create dpdk-bridge (${DBR})"
sudo $OVS_PATH/utilities/ovs-vsctl add-br $DBR -- set bridge $DBR datapath_type=netdev
sleep5
echo "Add dpdk ports for ${DBR}"
sudo $OVS_PATH/utilities/ovs-vsctl add-port $DBR dpdk0 -- set Interface dpdk0 type=dpdk options:dpdk-devargs=0000:03:00.0
#sudo $OVS_PATH/utilities/ovs-vsctl add-port $DBR dpdk1 -- set Interface dpdk1 type=dpdk options:dpdk-devargs=0000:0b:00.1
sleep 5
echo "Add ${num_cores} CPU to OVS and pin RX queues to the CPU cores"
sudo $OVS_PATH/utilities/ovs-vsctl set interface dpdk1 options:n_rxq=$r other_config:pmd-rxq-affinity=$pinning
sleep 5
echo "This is the pinning:"
sudo $OVS_PATH/utilities/ovs-appctl dpif-netdev/pmd-rxq-show

echo "Add passive controller listener port on ${ptcp_port}"
sudo $OVS_PATH/utilities/ovs-vsctl set-controller $DBR ptcp:$ptcp_port

echo "[DONE]"
