rvmx : Remote control command for multiple ESX HVs
==================================================

rvmx is remote control command for multiple VMware ESX 5.1 hypervisors.
rvmx focuses basic operations and network operations for VMs. It does
not include commands for HV's operation.


It requires _sshpass_ and _ovftool_. ovftool is provided by VMware.
I tested rvmx on Linux environment only.

 
	 % ./rvmx.py 
	  
	   Remote control command for multiple ESX HVs.
	  
	    rvmx [cmd] [options]
 
	   - VM related oprerations.
	    vmlist (HVname) : display VM list on HVs
	    vmid   [VMname] : display VMid
	    getmac [VMname] : get mac address of VM
	    getnet [VMname] : get network of VM
	    setnet [VMname] [ethX] [Net] : set VM network (stopped VM only)
	    power  [VMname] [on/off/status] : change VM power state
	  
	   - Network related operations.
	    vslist  (HVname)                 : display vSwitch list
	    addpg   [HVname] [VSname] [Name] : add new portgroup to vSwitch
	    delpg   [HVname] [VSname] [Name] : delete portgroup from vSwitch
	    setvlan [HVname] [VSname] [Name] [VlanID] : set vlan to portgroup
	  
	   - VM template operations.
	    import  [OVA] [VMname] [HVname]   : import new ova file
	    export  [HVname] [VMname] [OVA]   : export VM to ova file
	    destroy [VMname]                  : destroy VM
	 

Contact
-------
upa@haeena.net


This script is written for makuhari.
