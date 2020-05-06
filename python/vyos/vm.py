# references from virt-what
# http://dmo.ca/blog/detecting-virtualization-on-linux/
# http://blogs.msdn.com/b/sqlosteam/archive/2010/10/30/is-this-real-the-metaphysics-of-hardware-virtualization.aspx
# http://www.freedesktop.org/wiki/Software/systemd/ContainerInterface

import re
from os.path import join
from os.path import exists

BARE = 'bare metal'
AWS = 'aws'
BHYVE = 'bhyve'
DOCKER = 'docker'
HYPERV = 'hyperv'
KVM = 'kvm'
QEMU = 'qemu'
LXC = 'lxc'
OVIRT = 'ovirt'
PARALLELS = 'parallels'
POWERVM = 'powervm'
UML = 'uml'
RHEV = 'rhev'
VIRTUALBOX = 'virtualbox'
VIRTUALPC = 'virtualpc'
VIRTUOZZO = 'virtuozzo'
VMWARE = 'vmware'
XEN = 'xen'
VSERVER = 'vserver'

# hypervisor, regex?, string/regex

_msg = [
    (KVM, False, 'Hypervisor detected: KVM'),
    (KVM, False, 'Booting paravirtualized kernel on KVM'),
    (QEMU, False, 'QEMU Virtual CPU'),
    (VMWARE, False, 'VMware vmxnet virtual NIC driver'),
    (VMWARE, False, 'Virtual HD, ATA DISK drive'),
    (XEN, False, 'Xen virtual console')
]

_dmi = [
    (KVM, False, 'Product Name: KVM'),
    (QEMU, False, 'Manufacturer: QEMU'),
    (AWS, False, 'Vendor: Amazon EC2'),
    (VIRTUALPC, False, 'Manufacturer: Microsoft Corporation'),
    (VMWARE, False, 'VMwareVMware'),
    (VMWARE, False, 'Product Name: VMware Virtual Platform'),
    (VIRTUALBOX, False, 'Manufacturer: innotek GmbH'),
    (PARALLELS, False, 'Vendor: Parallels'),
    (OVIRT, False, 'Manufacturer: oVirt'),
    (RHEV, False, 'Product Name: RHEV Hypervisor'),
    (AWS, True, re.compile(r'Version: [0-9]\.[0-9]\.amazon')),
]

_cpu = [
   (KVM, False, 'KVMKVMKVM'),
   (QEMU, False, 'TCGTCGTCGTCG'),
   (BHYVE, False, 'bhyve bhyve '),
   (UML, False, 'UML'),
   (POWERVM, False, 'PowerVM Lx86'),
]

_env = [
    (VIRTUALBOX, False, 'GmbHVirtualBox'),
    (LXC, False, 'container='),
]


def check(matches, fname):
    with open(fname, 'rb') as f:
        content = f.read(4*1024).decode(errors='ignore')

    for hypervisor, regex, string in matches:
        if regex:
            if string.match(content):
                yield hypervisor
            continue
        if string in content:
            yield hypervisor


def _add(aset, iterator):
    for r in iterator:
        aset.add(r)


def detect(root='/', _detected=[None]):
    if _detected[0] is None:
        _detected.pop()
        _detected.append(_detect(root))
    return _detected[0]

def _detect(root='/'):
    found = list()

    found.extend(check(_msg, join(root, 'dev/kmsg')))
    found.extend(check(_msg, join(root, 'var/log/dmesg')))
    found.extend(check(_dmi, join(root, 'sys/firmware/dmi/tables/DMI')))
    found.extend(check(_cpu, join(root, 'proc/cpuinfo'), ))
    found.extend(check(_env, join(root, 'proc/1/environ'), ))

    if exists(join(root, '/proc/vz')) or \
       exists(join(root, '/dev/vzfs')) or \
       exists(join(root, '/proc/bc')):
        found.add(VIRTUOZZO)

    if exists(join(root, '/proc/xen')) or \
       exists(join(root, '/sys/hypervisor/type')):
        found.add(XEN)

    if exists(join(root, '.dockerinit')):
        found.add(DOCKER)

    if not found:
        found.append(BARE)

    return set(found)
