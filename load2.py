#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

import pprint
import sys
import re

import kicad_netlist_reader
netfile = kicad_netlist_reader.netlist(sys.argv[1])

from collections import namedtuple

def connected_pin(component, pin):
    part = component.part
    if part in ('R', 'C'):
        if pin == 1:
            return 2
        elif pin == 2:
            return 1
        else:
            raise IOError('Unknown pin! %s' % pin)
    elif part == 'RES_NET4':
        if pin == 1:
            return 2
        elif pin == 2:
            return 1
        elif pin == 3:
            return 4
        elif pin == 4:
            return 3
        elif pin == 5:
            return 6
        elif pin == 6:
            return 5
        elif pin == 7:
            return 8
        elif pin == 8:
            return 7
        else:
            raise IOError('Unknown pin! %s' % pin)

    elif part == 'IP4776CZ38':
        if pin < 1 or pin > 38:
            raise IOError('Unknown pin! %s' % pin)
        # 19 == 20
        # 18 == 21
        # 17 == 22
        if pin < 16 or pin > 23:
            return

        if pin < 20:
            return 20 + (19 - pin)
        else:
            return 39 - pin
    else:
        return


def format_pin(pin):
    try:
        pin = int(pin)
    except ValueError:
        pass
    try:
        letter, digits = re.match('([A-Z]+)([0-9]+)', pin).groups()
        pin = (letter, int(digits))
    except Exception:
        pass
    return pin


ComponentBase = namedtuple("Component", ['name', 'part'])
class Component(ComponentBase):
    @property
    def is_passive(self):
        return self.part in ('C', 'R')


assert connected_pin(Component('A', 'IP4776CZ38'), 16) == 23
assert connected_pin(Component('A', 'IP4776CZ38'), 17) == 22
assert connected_pin(Component('A', 'IP4776CZ38'), 18) == 21
assert connected_pin(Component('A', 'IP4776CZ38'), 19) == 20
assert connected_pin(Component('A', 'IP4776CZ38'), 20) == 19
assert connected_pin(Component('A', 'IP4776CZ38'), 21) == 18
assert connected_pin(Component('A', 'IP4776CZ38'), 22) == 17
assert connected_pin(Component('A', 'IP4776CZ38'), 23) == 16


ConnectionBase = namedtuple("Connection", ['component', 'pin', 'via'])
class Connection(ConnectionBase):
    def __new__(cls, component, pin, via=None):
        return ConnectionBase.__new__(cls, component=component, pin=pin, via=via)


NetBase = namedtuple("Net", ['name', 'connections'])
class Net(NetBase):
    def __new__(cls, name):
        return NetBase.__new__(cls, name=name, connections=set())

    def add_connection(self, c):
        assert isinstance(c, Connection)
        self.connections.add(c)

    @property
    def is_power(self):
        if "VCC" in self.name or "VDD" in self.name or "VTT" in self.name:
            return "VCC"
        elif "GND" in self.name:
            return "GND"
        else:
            return None


Pull = namedtuple('Pull', ['net', 'via', 'to'])


class Schematic(object):
    def __init__(self):
        self.nets = {}
        self.components = {}

        self.components2nets = {}

    def add_net(self, net):
        assert isinstance(net, Net)
        assert net.name not in self.nets
        for c in net.connections:
            assert c.component in self.components

            c2net = self.components2nets.setdefault(c.component, {})
            assert c.pin not in c2net
            c2net[c.pin] = net.name

        self.nets[net.name] = net

    def add_component(self, comp):
        assert isinstance(comp, Component)
        assert comp.name not in self.components
        self.components[comp.name] = comp

    def net_for_pin(self, component, pin):
        assert pin
        netname = self.components2nets[component.name][pin]
        return self.nets[netname]

# ---------------------------------

schematic = Schematic()

for node in netfile.getInterestingComponents():
    schematic.add_component(Component(
        name=node.getRef(),
        part=node.getPartName()))

for node in netfile.nets:
    new_net = Net(name=node.attributes['name'])
    for child in node.getChildren():
        new_net.add_connection(Connection(
            component=child.attributes['ref'],
            pin=format_pin(child.attributes['pin'])))

    schematic.add_net(new_net)

for net in sorted(schematic.nets.values()):
    if net.is_power:
        continue

    fake_name = [net.name]
    fake_connections = set()
    fake_pulls = set()

    to_search_connections = set(net.connections)
    searched_connections = set()
    while len(to_search_connections) > len(searched_connections):
        for connection in to_search_connections - searched_connections:
            break
        searched_connections.add(connection)

        component = schematic.components[connection.component]

        other_pin = connected_pin(component, connection.pin)
        assert other_pin != connection.pin
        if not other_pin:
            fake_connections.add(connection)
            continue
        
        other_net = schematic.net_for_pin(component, other_pin)
        assert net.name != other_net.name, "%s == %s" % (net.name, other_net.name)
        if other_net.is_power:
            fake_pulls.add(Pull(net=net.name, via=component.name, to=other_net.name))
            continue

        fake_name.append(other_net.name)
        for c in other_net.connections:
            if c.component == component.name:
                continue
            to_search_connections.add(Connection(c.component, c.pin, (component.name, other_net.name)))

    if fake_name[0].startswith('Net'):
        continue

    print fake_name
    pprint.pprint(sorted(fake_connections))
    pprint.pprint(fake_pulls)
    print

"""
for net in schematic.nets.values():
    if net.is_power:
        continue

    for connection in net.connections:
        component = schematic.components[connection.component]
        if not component.is_passive:
            continue

        other_net = schematic.net_other_pin(component, connection.pin)
        if other_net.is_power:
            schematic.add_pull_connection(net, component, other_net)
        else:
            schematic.add_passive_connection(net, component, other_net)
"""

