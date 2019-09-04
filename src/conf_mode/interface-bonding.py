#!/usr/bin/env python3
#
# Copyright (C) 2019 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import os

from copy import deepcopy
from sys import exit
from netifaces import interfaces

from vyos.ifconfig import BondIf, EthernetIf
from vyos.config import Config
from vyos import ConfigError

default_config_data = {
    'address': [],
    'address_remove': [],
    'arp_mon_intvl': 0,
    'arp_mon_tgt': [],
    'description': '',
    'deleted': False,
    'dhcp_client_id': '',
    'dhcp_hostname': '',
    'dhcpv6_prm_only': False,
    'dhcpv6_temporary': False,
    'disable': False,
    'disable_link_detect': 1,
    'hash_policy': 'layer2',
    'ip_arp_cache_tmo': 30,
    'ip_proxy_arp': 0,
    'ip_proxy_arp_pvlan': 0,
    'intf': '',
    'mac': '',
    'mode': '802.3ad',
    'member': [],
    'mtu': 1500,
    'primary': '',
    'vif_s': [],
    'vif_s_remove': [],
    'vif': [],
    'vif_remove': []
}

def diff(first, second):
    second = set(second)
    return [item for item in first if item not in second]

def get_bond_mode(mode):
    if mode == 'round-robin':
        return 'balance-rr'
    elif mode == 'active-backup':
        return 'active-backup'
    elif mode == 'xor-hash':
        return 'balance-xor'
    elif mode == 'broadcast':
        return 'broadcast'
    elif mode == '802.3ad':
        return '802.3ad'
    elif mode == 'transmit-load-balance':
        return 'balance-tlb'
    elif mode == 'adaptive-load-balance':
        return 'balance-alb'
    else:
        raise ConfigError('invalid bond mode "{}"'.format(mode))

def get_ethertype(ethertype_val):
    if ethertype_val == '0x88A8':
        return '802.1ad'
    elif ethertype_val == '0x8100':
        return '802.1q'
    else:
        raise ConfigError('invalid ethertype "{}"'.format(ethertype_val))


def vlan_to_dict(conf):
    """
    Common used function which will extract VLAN related information from config
    and represent the result as Python dictionary.

    Function call's itself recursively if a vif-s/vif-c pair is detected.
    """
    vlan = {
        'id': conf.get_level().split()[-1], # get the '100' in 'interfaces bonding bond0 vif-s 100'
        'address': [],
        'address_remove': [],
        'description': '',
        'dhcp_client_id': '',
        'dhcp_hostname': '',
        'dhcpv6_prm_only': False,
        'dhcpv6_temporary': False,
        'disable': False,
        'disable_link_detect': 1,
        'mac': '',
        'mtu': 1500
    }
    # retrieve configured interface addresses
    if conf.exists('address'):
        vlan['address'] = conf.return_values('address')

    # Determine interface addresses (currently effective) - to determine which
    # address is no longer valid and needs to be removed from the bond
    eff_addr = conf.return_effective_values('address')
    act_addr = conf.return_values('address')
    vlan['address_remove'] = diff(eff_addr, act_addr)

    # retrieve interface description
    if conf.exists('description'):
        vlan['description'] = conf.return_value('description')

    # get DHCP client identifier
    if conf.exists('dhcp-options client-id'):
        vlan['dhcp_client_id'] = conf.return_value('dhcp-options client-id')

    # DHCP client host name (overrides the system host name)
    if conf.exists('dhcp-options host-name'):
        vlan['dhcp_hostname'] = conf.return_value('dhcp-options host-name')

    # DHCPv6 only acquire config parameters, no address
    if conf.exists('dhcpv6-options parameters-only'):
        vlan['dhcpv6_prm_only'] = conf.return_value('dhcpv6-options parameters-only')

    # DHCPv6 temporary IPv6 address
    if conf.exists('dhcpv6-options temporary'):
        vlan['dhcpv6_temporary'] = conf.return_value('dhcpv6-options temporary')

    # ignore link state changes
    if conf.exists('disable-link-detect'):
        vlan['disable_link_detect'] = 2

    # disable bond interface
    if conf.exists('disable'):
        vlan['disable'] = True

    # Media Access Control (MAC) address
    if conf.exists('mac'):
        vlan['mac'] = conf.return_value('mac')

    # Maximum Transmission Unit (MTU)
    if conf.exists('mtu'):
        vlan['mtu'] = int(conf.return_value('mtu'))

    # ethertype is mandatory on vif-s nodes and only exists here!
    # check if this is a vif-s node at all:
    if conf.get_level().split()[-2] == 'vif-s':
        vlan['vif_c'] = []
        vlan['vif_c_remove'] = []

        # ethertype uses a default of 0x88A8
        tmp = '0x88A8'
        if conf.exists('ethertype'):
             tmp = conf.return_value('ethertype')
        vlan['ethertype'] = get_ethertype(tmp)

        # get vif-c interfaces (currently effective) - to determine which vif-c
        # interface is no longer present and needs to be removed
        eff_intf = conf.list_effective_nodes('vif-c')
        act_intf = conf.list_nodes('vif-c')
        vlan['vif_c_remove'] = diff(eff_intf, act_intf)

        # check if there is a Q-in-Q vlan customer interface
        # and call this function recursively
        if conf.exists('vif-c'):
            cfg_level = conf.get_level()
            # add new key (vif-c) to dictionary
            for vif in conf.list_nodes('vif-c'):
                # set config level to vif interface
                conf.set_level(cfg_level + ' vif-c ' + vif)
                vlan['vif_c'].append(vlan_to_dict(conf))

    return vlan


def apply_vlan_config(vlan, config):
    """
    Generic function to apply a VLAN configuration from a dictionary
    to a VLAN interface
    """

    if type(vlan) != type(EthernetIf("lo")):
        raise TypeError()

    # Configure interface address(es)
    for addr in config['address_remove']:
        vlan.del_addr(addr)
    for addr in config['address']:
        vlan.add_addr(addr)

    # update interface description used e.g. within SNMP
    vlan.ifalias = config['description']
    # ignore link state changes
    vlan.link_detect = config['disable_link_detect']
    # Maximum Transmission Unit (MTU)
    vlan.mtu = config['mtu']
    # Change VLAN interface MAC address
    if config['mac']:
        vlan.mac = config['mac']

    # enable/disable VLAN interface
    if config['disable']:
        vlan.state = 'down'
    else:
        vlan.state = 'up'


def get_config():
    # initialize kernel module if not loaded
    if not os.path.isfile('/sys/class/net/bonding_masters'):
        import syslog
        syslog.syslog(syslog.LOG_NOTICE, "loading bonding kernel module")
        if os.system('modprobe bonding max_bonds=0 miimon=250') != 0:
            syslog.syslog(syslog.LOG_NOTICE, "failed loading bonding kernel module")
            raise ConfigError("failed loading bonding kernel module")

    bond = deepcopy(default_config_data)
    conf = Config()

    # determine tagNode instance
    try:
        bond['intf'] = os.environ['VYOS_TAGNODE_VALUE']
    except KeyError as E:
        print("Interface not specified")

    # check if bond has been removed
    cfg_base = 'interfaces bonding ' + bond['intf']
    if not conf.exists(cfg_base):
        bond['deleted'] = True
        return bond

    # set new configuration level
    conf.set_level(cfg_base)

    # retrieve configured interface addresses
    if conf.exists('address'):
        bond['address'] = conf.return_values('address')

    # ARP link monitoring frequency in milliseconds
    if conf.exists('arp-monitor interval'):
        bond['arp_mon_intvl'] = int(conf.return_value('arp-monitor interval'))

    # IP address to use for ARP monitoring
    if conf.exists('arp-monitor target'):
        bond['arp_mon_tgt'] = conf.return_values('arp-monitor target')

    # retrieve interface description
    if conf.exists('description'):
        bond['description'] = conf.return_value('description')
    else:
        bond['description'] = bond['intf']

    # get DHCP client identifier
    if conf.exists('dhcp-options client-id'):
        bond['dhcp_client_id'] = conf.return_value('dhcp-options client-id')

    # DHCP client host name (overrides the system host name)
    if conf.exists('dhcp-options host-name'):
        bond['dhcp_hostname'] = conf.return_value('dhcp-options host-name')

    # DHCPv6 only acquire config parameters, no address
    if conf.exists('dhcpv6-options parameters-only'):
        bond['dhcpv6_prm_only'] = conf.return_value('dhcpv6-options parameters-only')

    # DHCPv6 temporary IPv6 address
    if conf.exists('dhcpv6-options temporary'):
        bond['dhcpv6_temporary'] = conf.return_value('dhcpv6-options temporary')

    # ignore link state changes
    if conf.exists('disable-link-detect'):
        bond['disable_link_detect'] = 2

    # disable bond interface
    if conf.exists('disable'):
        bond['disable'] = True

    # Bonding transmit hash policy
    if conf.exists('hash-policy'):
        bond['hash_policy'] = conf.return_value('hash-policy')

    # ARP cache entry timeout in seconds
    if conf.exists('ip arp-cache-timeout'):
        bond['ip_arp_cache_tmo'] = int(conf.return_value('ip arp-cache-timeout'))

    # Enable proxy-arp on this interface
    if conf.exists('ip enable-proxy-arp'):
        bond['ip_proxy_arp'] = 1

    # Enable private VLAN proxy ARP on this interface
    if conf.exists('ip proxy-arp-pvlan'):
        bond['ip_proxy_arp_pvlan'] = 1

    # Media Access Control (MAC) address
    if conf.exists('mac'):
        bond['mac'] = conf.return_value('mac')

    # Bonding mode
    if conf.exists('mode'):
        bond['mode'] = get_bond_mode(conf.return_value('mode'))

    # Maximum Transmission Unit (MTU)
    if conf.exists('mtu'):
        bond['mtu'] = int(conf.return_value('mtu'))

    # determine bond member interfaces (currently configured)
    if conf.exists('member interface'):
        bond['member'] = conf.return_values('member interface')

    # get interface addresses (currently effective) - to determine which
    # address is no longer valid and needs to be removed from the bond
    eff_addr = conf.return_effective_values('address')
    act_addr = conf.return_values('address')
    bond['address_remove'] = diff(eff_addr, act_addr)

    # Primary device interface
    if conf.exists('primary'):
        bond['primary'] = conf.return_value('primary')

    # re-set configuration level and retrieve vif-s interfaces
    conf.set_level(cfg_base)
    # get vif-s interfaces (currently effective) - to determine which vif-s
    # interface is no longer present and needs to be removed
    eff_intf = conf.list_effective_nodes('vif-s')
    act_intf = conf.list_nodes('vif-s')
    bond['vif_s_remove'] = diff(eff_intf, act_intf)

    if conf.exists('vif-s'):
        for vif_s in conf.list_nodes('vif-s'):
            # set config level to vif-s interface
            conf.set_level(cfg_base + ' vif-s ' + vif_s)
            bond['vif_s'].append(vlan_to_dict(conf))

    # re-set configuration level and retrieve vif-s interfaces
    conf.set_level(cfg_base)
    # Determine vif interfaces (currently effective) - to determine which
    # vif interface is no longer present and needs to be removed
    eff_intf = conf.list_effective_nodes('vif')
    act_intf = conf.list_nodes('vif')
    bond['vif_remove'] = diff(eff_intf, act_intf)

    if conf.exists('vif'):
        for vif in conf.list_nodes('vif'):
            # set config level to vif interface
            conf.set_level(cfg_base + ' vif ' + vif)
            bond['vif'].append(vlan_to_dict(conf))

    return bond


def verify(bond):
    if len (bond['arp_mon_tgt']) > 16:
        raise ConfigError('The maximum number of targets that can be specified is 16')

    if bond['primary']:
        if bond['mode'] not in ['active-backup', 'balance-tlb', 'balance-alb']:
            raise ConfigError('Mode dependency failed, primary not supported in this mode.'.format())

        if bond['primary'] not in bond['member']:
            raise ConfigError('Interface "{}" is not part of the bond'.format(bond['primary']))

    for vif_s in bond['vif_s']:
        for vif in bond['vif']:
            if vif['id'] == vif_s['id']:
                raise ConfigError('Can not use identical ID on vif and vif-s interface')


    conf = Config()
    for intf in bond['member']:
        # we can not add disabled slave interfaces to our bond
        if conf.exists('interfaces ethernet ' + intf + ' disable'):
            raise ConfigError('can not add disabled interface {} to {}'.format(intf, bond['intf']))

        # can not add interfaces with an assigned address to a bond
        if conf.exists('interfaces ethernet ' + intf + ' address'):
            raise ConfigError('can not add interface {} with an assigned address to {}'.format(intf, bond['intf']))

        # bond members are not allowed to be bridge members, too
        for bridge in conf.list_nodes('interfaces bridge'):
            if conf.exists('interfaces bridge ' + bridge + ' member interface ' + intf):
                raise ConfigError('can not add interface {} that is part of bridge {} to {}'.format(intf, bridge, bond['intf']))

        # bond members are not allowed to be vrrp members, too
        for vrrp in conf.list_nodes('high-availability vrrp group'):
            if conf.exists('high-availability vrrp group ' + vrrp + ' interface ' + intf):
                raise ConfigError('can not add interface {} which belongs to a VRRP group to {}'.format(intf, bond['intf']))

        # bond members are not allowed to be underlaying psuedo-ethernet devices
        for peth in conf.list_nodes('interfaces pseudo-ethernet'):
            if conf.exists('interfaces pseudo-ethernet ' + peth + ' link ' + intf):
                raise ConfigError('can not add interface {} used by pseudo-ethernet {} to {}'.format(intf, peth, bond['intf']))

    if bond['primary']:
        if bond['primary'] not in bond['member']:
            raise ConfigError('primary interface must be a member interface of {}'.format(bond['intf']))

        if bond['mode'] not in ['active-backup', 'balance-tlb', 'balance-alb']:
            raise ConfigError('primary interface only works for mode active-backup, transmit-load-balance or adaptive-load-balance')

    if bond['arp_mon_intvl'] > 0:
        if bond['mode'] in ['802.3ad', 'balance-tlb', 'balance-alb']:
            raise ConfigError('ARP link monitoring does not work for mode 802.3ad, transmit-load-balance or adaptive-load-balance')

    return None


def generate(bond):
    return None


def apply(bond):
    b = BondIf(bond['intf'])

    if bond['deleted']:
        # delete bonding interface
        b.remove()
    else:
        # Some parameters can not be changed when the bond is up.
        # Always disable the bond prior changing anything
        b.state = 'down'

        # The bonding mode can not be changed when there are interfaces enslaved
        # to this bond, thus we will free all interfaces from the bond first!
        for intf in b.get_slaves():
            b.del_port(intf)

        # Configure interface address(es)
        for addr in bond['address_remove']:
            b.del_addr(addr)
        for addr in bond['address']:
            b.add_addr(addr)

        # ARP link monitoring frequency
        b.arp_interval = bond['arp_mon_intvl']
        # reset miimon on arp-montior deletion
        if bond['arp_mon_intvl'] == 0:
            # reset miimon to default
            b.bond_miimon = 250

        # ARP monitor targets need to be synchronized between sysfs and CLI.
        # Unfortunately an address can't be send twice to sysfs as this will
        # result in the following exception:  OSError: [Errno 22] Invalid argument.
        #
        # We remove ALL adresses prior adding new ones, this will remove addresses
        # added manually by the user too - but as we are limited to 16 adresses
        # from the kernel side this looks valid to me. We won't run into an error
        # when a user added manual adresses which would result in having more
        # then 16 adresses in total.
        cur_addr = list(map(str, b.arp_ip_target.split()))
        for addr in cur_addr:
            b.arp_ip_target = '-' + addr

        # Add configured ARP target addresses
        for addr in bond['arp_mon_tgt']:
            b.arp_ip_target = '+' + addr

        # update interface description used e.g. within SNMP
        b.ifalias = bond['description']

        #
        # missing DHCP/DHCPv6 options go here
        #

        # ignore link state changes
        b.link_detect = bond['disable_link_detect']
        # Bonding transmit hash policy
        b.xmit_hash_policy = bond['hash_policy']
        # configure ARP cache timeout in milliseconds
        b.arp_cache_tmp = bond['ip_arp_cache_tmo']
        # Enable proxy-arp on this interface
        b.proxy_arp = bond['ip_proxy_arp']
        # Enable private VLAN proxy ARP on this interface
        b.proxy_arp_pvlan = bond['ip_proxy_arp_pvlan']

        # Change interface MAC address
        if bond['mac']:
            b.mac = bond['mac']

        # Bonding policy
        b.mode = bond['mode']
        # Maximum Transmission Unit (MTU)
        b.mtu = bond['mtu']

        # Primary device interface
        if bond['primary']:
            b.primary = bond['primary']

        # Add (enslave) interfaces to bond
        for intf in bond['member']:
            b.add_port(intf)

        # remove no longer required service VLAN interfaces (vif-s)
        for vif_s in bond['vif_s_remove']:
            b.del_vlan(vif_s)

        # create service VLAN interfaces (vif-s)
        for vif_s in bond['vif_s']:
            s_vlan = b.add_vlan(vif_s['id'], ethertype=vif_s['ethertype'])
            apply_vlan_config(s_vlan, vif_s)

            # remove no longer required client VLAN interfaces (vif-c)
            # on lower service VLAN interface
            for vif_c in vif_s['vif_c_remove']:
                s_vlan.del_vlan(vif_c)

            # create client VLAN interfaces (vif-c)
            # on lower service VLAN interface
            for vif_c in vif_s['vif_c']:
                c_vlan = s_vlan.add_vlan(vif_c['id'])
                apply_vlan_config(c_vlan, vif_c)

        # remove no longer required VLAN interfaces (vif)
        for vif in bond['vif_remove']:
            b.del_vlan(vif)

        # create VLAN interfaces (vif)
        for vif in bond['vif']:
            vlan = b.add_vlan(vif['id'])
            apply_vlan_config(vlan, vif)

        # As the bond interface is always disabled first when changing
        # parameters we will only re-enable the interface if it is not
        # administratively disabled
        if not bond['disable']:
            b.state = 'up'

    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)