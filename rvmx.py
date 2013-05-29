#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Remote control command for multiple ESX HVs.
#
# Requires
#  - sshpass
#  - VMware-ovf-tools
#

import re
import sys
import threading
import commands
import subprocess


hvlist = [
    { 'name' : 'hv1',
      'addr' : '172.16.0.1',
      'user' : 'username',
      'pass' : 'password'
      },
    { 'name' : 'hv2',
      'addr' : '172.16.0.1',
      'user' : 'username',
      'pass' : 'password'
      },
    { 'name' : 'hv3',
      'addr' : '172.16.0.1',
      'user' : 'username',
      'pass' : 'password'
      },
    ]

# VM staructure template. it's reference for myself.
vmtemplate = {
    'hv' : 'hv1',
    'name' : 'VM Name',
    'vmid' : 'VM id (HV internal)'
}

def error_exit (estr, code) :
    print estr
    sys.exit (code)

def usage () :
    print ""
    print " Remote control command for multiple ESX HVs."
    print
    print "  rvmx [cmd] [options]"
    print ""
    print " - VM related oprerations."
    print "  vmlist (HVname) : display VM list on HVs"
    print "  vmid   [VMname] : display VMid"
    print "  getmac [VMname] : get mac address of VM"
    print "  getnet [VMname] : get network of VM"
    print "  setnet [VMname] [ethX] [Net] : set VM network (stopped VM only)"
    print "  power  [VMname] [on/off/status] : change VM power state"
    print ""
    print " - Network related operations."
    print "  vslist  (HVname)                 : display vSwitch list"
    print "  addpg   [HVname] [VSname] [Name] : add new portgroup to vSwitch"
    print "  delpg   [HVname] [VSname] [Name] : delete portgroup from vSwitch"
    print "  setvlan [HVname] [VSname] [Name] [VlanID] : set vlan to portgroup"
    print ""
    print " - VM template operations."
    print "  import  [OVA] [VMname] [HVname]   : import new ova file"
    print "  export  [HVname] [VMname] [OVA]   : export VM to ova file"
    print "  destroy [VMname]                  : destroy VM"
    
    print 
    sys.exit (0)


def fill_space (string, maxnum) :

    n = maxnum - len (string)
    s = ""
    for x in range (n) :
        s = s + " "

    return s

def search_hv_by_name (name) :
    
    for hv in hvlist :
        if hv['name'] == name :
            return hv

    return None

"""
instance = {
  "command" : "COMMAND",
  "description" : "DESCRIPTION",
  "stdin" : "DATA TO STDIN",
}
"""
def multiexec (instances, debug = False) :
    class thread_worker (threading.Thread) :
        def __init__ (self, description, command) :
            self.description = description
            self.command = command
            self.result = ""
            threading.Thread.__init__ (self)
            self.setDaemon
            
        def exec_worker (self) :
            if debug :
                print "exec multi command : %s" % self.description
                print self.command

            res = commands.getoutput (self.command)

            self.result = res
            if debug :
                print "==== RESULT ===="
                print self.result

        def run (self) :
            self.exec_worker ()

    workers = []
    for instance in instances :
        if not instance.has_key ("stdin") :
            instance["stdin"] = ""
            
        worker = thread_worker (instance["description"],
                                instance["command"])
        workers.append (worker)
        worker.start ()

    result = []
    for worker in workers :
        worker.join ()
        result.append ({"description" : worker.description, 
                        "result" : worker.result})
        
    return result


# Remote vim-cmd class
class rvmx () :

    def __init__ (self) :
        self.hvlist = []
        self.commands = {}
        self.hvlist = hvlist
        self.install_commands ()
        
    def install_commands (self) :
        self.commands = {
            "vmlist" : rvmx_vmlist,
            "vmid"   : rvmx_vmid,
            "getmac" : rvmx_getmac,
            "getnet" : rvmx_getnet,
            "power"  : rvmx_power,
            "setnet" : rvmx_setnet,
            "vslist" : rvmx_vslist,
            "addpg" : rvmx_addpg,
            "delpg" : rvmx_delpg,
            "setvlan" : rvmx_setvlan,
            "import" : rvmx_import,
            "export" : rvmx_export,
            "destroy" : rvmx_destroy,
            }

    def exec_rvmx (self, args) :
        
        if len (args) == 0 :
            usage ()

        if not self.commands.has_key (args[0]) :
            error_exit ("invalid command \"%s\"" % args[0], -1)

        cmd = args.pop (0)
        self.commands[cmd] (args)
        sys.exit (0)


def get_all_vm () :

    instances = []
    for hv in hvlist :
        cmdstr = ("sshpass -p '%s' ssh -l %s %s vim-cmd vmsvc/getallvms" % 
                  (hv['pass'], hv['user'], hv['addr']))
        instances.append ({"description" : hv, "command" : cmdstr})

    results = multiexec (instances)
    
    vmlist = []
    for result in results :
        hv = search_hv_by_name (result["description"]["name"])
        if hv == None :
            error_warn ("unknown Hypver Visor \"%s\"" % 
                        result["description"]["name"])
            continue
        vmlist += rvmx_vmlist_parse_getallvms (hv, result["result"])
        
    return vmlist


def search_vm_by_name (vmname) :
    # [VMname]

    vmlist = get_all_vm ()
        
    for vm in vmlist :
        if vm['name'] == vmname :
            return vm

    return None


def rvmx_vmlist_parse_getallvms (hv, output) :

    vmlist = []
    o = re.sub (r' +', ' ', output)
    s = o.split ('\n')
    s.pop (0)
    
    for line in s :
        ls = line.split (' ')
        vmid = int (ls.pop (0))
        name = ls.pop (0)
        ls.pop (0)  # [datastore1]
        vmx = ls.pop (0)
        vmx = "/vmfs/volumes/datastore1/" + vmx
        vmlist.append ({'hv' : hv, 'name' : name, 
                        'vmid' : vmid, 'vmx' : vmx })

    return vmlist


def rvmx_vmlist (args) :
    # (HVname)
    
    h_flag = False
    hvname = ""
    if len (args) > 0 :
        hvname = args[0]
        h_flag = True
    
    print "HyperVisor",
    print fill_space ("HyperVisor", 12),
    print "Address",
    print fill_space ("Address", 16),
    print "VMname",
    print fill_space ("VMname", 32),
    print "VMid"

    vmlist = get_all_vm ()

    for vm in vmlist :
        if h_flag :
            if vm['hv']['name'] != hvname :
                continue

        print vm['hv']['name'],
        print fill_space (vm['hv']['name'], 12),
        print vm['hv']['addr'],
        print fill_space (vm['hv']['addr'], 16),
        print vm['name'],
        print fill_space (vm['name'], 32),
        print vm['vmid']


def rvmx_vmid (args) :
    # [VMname]
    if len (args) != 1 :
        error_exit ("invalid commands \"%s\"" % ' '.join (args), -1)
    
    print "HyperVisor",
    print fill_space ("HyperVisor", 12),
    print "Address",
    print fill_space ("Address", 16),
    print "VMname",
    print fill_space ("VMname", 12),
    print "VMid"

    vmlist = get_all_vm ()

    for vm in vmlist :
        if vm['name'] != args[0] :
            continue
        print vm['hv']['name'],
        print fill_space (vm['hv']['name'], 12),
        print vm['hv']['addr'],
        print fill_space (vm['hv']['addr'], 16),
        print vm['name'],
        print fill_space (vm['name'], 12),
        print vm['vmid']


def rvmx_getmac (args) :
    # [VMname]

    if len (args) < 1 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    vmname =  args.pop (0)
    e_flag = False
    try :
        aeth = args.pop (0)
        e_flag = True
    except :
        pass

    matched_vmlist = []
    vmlist = get_all_vm ()

    for vm in vmlist :
        if vm['name'] == vmname :
            matched_vmlist.append (vm)

    if not e_flag :
        print "HyperVisor",
        print fill_space ("HyperVisor", 10),
        print "Address",
        print fill_space ("Address", 16),
        print "VMname",
        print fill_space ("VMname", 12),
        print "Interface",
        print fill_space ("Interface", 12),
        print "MAC"

    for vm in matched_vmlist :
        cmdstr = ("sshpass -p %s ssh -l %s %s " % 
                  (vm['hv']['pass'], vm['hv']['user'], vm['hv']['addr'])+
                  "cat %s | grep ethernet | grep generatedAddress | grep :"
                  % (vm['vmx']))
        output = commands.getoutput (cmdstr)
        lines = output.split ('\n')
        
        for line in lines :
            try :
                (ethaddr, strmac) = line.split (' = ')
            except :
                continue
            (eth, gaddr) = ethaddr.split ('.')
            mac = strmac[1:18]
            if e_flag :
                if eth == aeth :
                    print mac
            else :
                print vm['hv']['name'],
                print fill_space (vm['hv']['name'], 10),
                print vm['hv']['addr'],
                print fill_space (vm['hv']['addr'], 16),
                print vm['name'],
                print fill_space (vm['name'], 12),
                print eth,
                print fill_space (eth, 12),
                print mac


def rvmx_getnet (args) :
    # [VMname]

    if len (args) != 1 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    vmname =  args.pop (0)

    matched_vmlist = []
    vmlist = get_all_vm ()

    for vm in vmlist :
        if vm['name'] == vmname :
            matched_vmlist.append (vm)

    print "HyperVisor",
    print fill_space ("HyperVisor", 12),
    print "Address",
    print fill_space ("Address", 16),
    print "VMname",
    print fill_space ("VMname", 12),
    print "Interface",
    print fill_space ("Interface", 12),
    print "Network"

    for vm in matched_vmlist :
        cmdstr = ("sshpass -p %s ssh -l %s %s " % 
                  (vm['hv']['pass'], vm['hv']['user'], vm['hv']['addr']) +
                  "cat %s | grep ethernet | grep networkName"
                  % (vm['vmx']))
        output = commands.getoutput (cmdstr)
        lines = output.split ('\n')
        
        for line in lines :
            (ethnet, strnet) = line.split (' = ')
            (eth, net) = ethnet.split ('.')
            net = re.sub (r'"', '', strnet)
            print vm['hv']['name'],
            print fill_space (vm['hv']['name'], 12),
            print vm['hv']['addr'],
            print fill_space (vm['hv']['addr'], 16),
            print vm['name'],
            print fill_space (vm['name'], 12),
            print eth,
            print fill_space (eth, 12),
            print net


def rvmx_power (args) :
    # [VMname] [on/off/status]

    if len (args) != 2 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (vmname, state) = args

    if state == "status" :
        state = "getstate"

    vm = search_vm_by_name (vmname)
    if vm == None :
        error_exit ("VMname \"%s\" does not exist" % vmname, -1)

    cmdstr = ("sshpass -p %s ssh -l %s %s " % 
              (vm['hv']['pass'], vm['hv']['user'], vm['hv']['addr']) +
              "vim-cmd vmsvc/power.%s %d" % (state, vm['vmid'])
              )

    output = commands.getoutput (cmdstr)
    print output
    return



def rvmx_setnet (args) :
    # [VMname] [ethX] [Net]

    if len (args) != 3 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (vmname, eth, netname) = args

    vm = search_vm_by_name (vmname)
    if vm == None :
        error_exit ("VMname \"%s\" does not exist" % vmname, -1)

    sedcmdstr = \
        ("\"sed -i 's/%s\.networkName = .*/%s\.networkName = \\\"%s\\\"/'\""
         % (eth, eth, netname))
    cmdstr = ("sshpass -p %s ssh -l %s %s " % 
              (vm['hv']['pass'], vm['hv']['user'], vm['hv']['addr']) +
              "%s %s" % (sedcmdstr, vm['vmx'])
              )

    output = commands.getoutput (cmdstr)
    return
    
def rvmx_vslist (args) :
    # (hvname)

    hv_f = False
    if len (args) > 0 :
        hvname = args.pop (0)
        hv_f = True

    for hv in hvlist :
        if hv_f :
            if hvname != hv['name'] :
                continue
        cmdstr = ("sshpass -p '%s' ssh -l %s %s esxcfg-vswitch -l" % 
                  (hv['pass'], hv['user'], hv['addr']))
        output = commands.getoutput (cmdstr)
        print "HyperVisor : %s (%s)" % (hv['name'], hv['addr'])
        print output
        print


def rvmx_addpg (args) :
    # HVname VSname PGname

    if len (args) != 3 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (hvname, vsname, pgname) = args

    hv = search_hv_by_name (hvname)
    if hv == None :
        error_exit ("HV \"%s\" does not exist" % hvname, -1)

    cmdstr = ("sshpass -p '%s' ssh -l %s %s esxcfg-vswitch " % 
              (hv['pass'], hv['user'], hv['addr']) +
              "-A %s %s" % (pgname, vsname))
    
    output = commands.getoutput (cmdstr)
    print output,
    return


def rvmx_delpg (args) :
    # HVname VSname PGname

    if len (args) != 3 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (hvname, vsname, pgname) = args

    hv = search_hv_by_name (hvname)
    if hv == None :
        error_exit ("HV \"%s\" does not exist" % hvname, -1)

    cmdstr = ("sshpass -p '%s' ssh -l %s %s esxcfg-vswitch " % 
              (hv['pass'], hv['user'], hv['addr']) +
              "-D %s %s" % (pgname, vsname))
    
    output = commands.getoutput (cmdstr)
    print output,
    return



def rvmx_setvlan (args) :
    # HVname VSname PGname VlanID

    if len (args) != 4 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (hvname, vsname, pgname, vlan) = args

    hv = search_hv_by_name (hvname)
    if hv == None :
        error_exit ("HV \"%s\" does not exist" % hvname, -1)

    cmdstr = ("sshpass -p '%s' ssh -l %s %s esxcfg-vswitch " % 
              (hv['pass'], hv['user'], hv['addr']) +
              "-p %s -v %s %s" % (pgname, vlan, vsname))
    
    output = commands.getoutput (cmdstr)
    print output,
    return

def rvmx_import (args) :
    # OVA VMname HVname

    if len (args) != 3 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (ovafile, vmname, hvname) = args

    hv = search_hv_by_name (hvname)
    if hv == None :
        error_exit ("HV \"%s\" does not exist" % hvname, -1)        

    cmdstr = ("ovftool --acceptAllEulas --name=%s %s vi://%s:%s@%s/" % 
              (vmname, ovafile, hv['user'], hv['pass'], hv['addr']))

    cmdarg = cmdstr.split (' ')
    subprocess.call (cmdarg)

    return

def rvmx_export (args) :
    # HVname VMname OVA

    if len (args) != 3 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    (hvname, vmname, ovafile) = args

    hv = search_hv_by_name (hvname)
    if hv == None :
        error_exit ("HV \"%s\" does not exist" % hvname, -1)        

    cmdstr = ("ovftool --acceptAllEulas vi://%s:%s@%s/%s %s" % 
              (hv['user'], hv['pass'], hv['addr'], vmname, ovafile))

    cmdarg = cmdstr.split (' ')
    subprocess.call (cmdarg)

    return

def rvmx_destroy (args) :
    # VMname

    if len (args) != 1 :
        error_exit ("invalid command syntax \"%s\"" % ' '.join (args), -1)

    vmname = args.pop (0)

    vm = search_vm_by_name (vmname)
    if vm == None :
        error_exit ("VM \"%s\" does not exist" % vmname, -1)

    hv = vm['hv']

    cmdstr = ("sshpass -p '%s' ssh -l %s %s vim-cmd vmsvc/destroy " % 
              (hv['pass'], hv['user'], hv['addr']) +
              "%d" % vm['vmid'])
    
    output = commands.getoutput (cmdstr)
    print output,
    return



def main () :
    
    args = sys.argv
    args.pop (0) # remove "rvmx"
    
    rv = rvmx ()

    rv.exec_rvmx (args)
    sys.exit (0)
    

if __name__ == "__main__" :
    main ()
