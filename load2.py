#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

import pprint
import sys
import re

import kicad_netlist_reader
netfile = kicad_netlist_reader.netlist(sys.argv[1])

from collections import namedtuple


PinBase = namedtuple("Pin", ["name", "description", "type"])
class Pin(PinBase):
    @staticmethod
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


PartBase = namedtuple("Part", ["name", "pins"])
class Part(PartBase):
    def __new__(cls, name):
        return PartBase.__new__(cls, name, pins={})

    def add_pin(self, name, description, type):
        p = Pin(Pin.format_pin(name), description, type)
        assert p.name not in self.pins
        self.pins[p.name] = p

    def connected_pin(self, pin):
        if self.name in ('R', 'C', 'SW_PUSH'):
            if pin == 1:
                return 2
            elif pin == 2:
                return 1
            else:
                raise IOError('Unknown pin! %s' % pin)
        elif self.name == 'RES_NET4':
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

        elif self.name == 'IP4776CZ38':
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

    def io_standard(self, pin):
        desc = self.pins[pin].description

        if self.name == "HDMI":
            if desc.endswith('S') or desc == "DDC/CEC/HEC" or desc == "+5V":
                return
            # Data lines
            elif desc.startswith('D'):
                return 'TMDS_33'
            # Clock line
            elif desc.startswith('CLK'):
                return 'TMDS_33'
            elif desc in ("SCL", "SDA"):
                return 'I2C'
            elif desc in ('CEC', 'HPD'):
                return 'LVCMOS33'
            else:
                assert False, "%s pin had description %s" % (pin, desc)

        elif self.name == "DISPLAY_PORT":
            if desc.startswith('ML_Lane'):
                return 'LVDS_25'
            elif desc in ("GND", "RETURN", "DP_PWR"):
                return
            elif desc in ('HPD', 'CONFIG1', 'CONFIG2'):
                return 'LVCMOS33'
            elif desc in ('AUXCH_N', 'AUXCH_P'):
                return 'LVDS_33'
            else:
                assert False, "%s pin had description %s" % (pin, desc)

        return

    def net_name(self, pin):
        desc = self.pins[pin].description
        if self.name == "HDMI":
            data = re.match('D([0-9])([+-])', desc)
            if data:
                if data.group(2) == '+':
                    return "hdmi_{0}_p["+data.group(1)+"]"
                elif data.group(2) == '-':
                    return "hdmi_{0}_p["+data.group(1)+"]"
                else:
                    assert False, (pin, desc, data.group(1), data.group(2))
            elif desc == 'CLK+':
                return "hdmi_{0}_clk_p"
            elif desc == 'CLK-':
                return "hdmi_{0}_clk_n"
            elif desc in ('HPD', 'SCL', 'SDA', 'CEC'):
                return "hdmi_{0}_"+desc.lower()
            else:
                assert False, (pin, desc)
        elif self.name == "DISPLAY_PORT":
            if desc.startswith('ML_Lane'):
                return "dp_{0}_lnk_%s[%s]" % (desc[6].lower(), desc[7])
            elif desc == "AUXCH_P":
                return "dp_{0}_aux_p"
            elif desc == "AUXCH_N":
                return "dp_{0}_aux_n"
            elif desc == "CONFIG1":
                return "dp_{0}_config1"
            elif desc == "CONFIG2":
                return "dp_{0}_config2"
            elif desc == "HPD":
                return "dp_{0}_hpd"
            else:
                assert False, pin
            

part = Part('IP4776CZ38')
assert part.connected_pin(16) == 23
assert part.connected_pin(17) == 22
assert part.connected_pin(18) == 21
assert part.connected_pin(19) == 20
assert part.connected_pin(20) == 19
assert part.connected_pin(21) == 18
assert part.connected_pin(22) == 17
assert part.connected_pin(23) == 16


ComponentBase = namedtuple("Component", ['name', 'part'])
class Component(ComponentBase):
    @property
    def is_passive(self):
        return self.part in ('C', 'R')


ConnectionBase = namedtuple("Connection", ['component', 'pin', 'via'])
class Connection(ConnectionBase):
    def __new__(cls, component, pin, via=None):
        return ConnectionBase.__new__(cls, component=component, pin=pin, via=via)


NetBase = namedtuple("Net", ['name', 'connections', 'pulls'])
class Net(NetBase):
    def __new__(cls, name):
        return NetBase.__new__(cls, name=name, connections=set(), pulls=set())

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
        self.parts = {}
        self.nets = {}
        self.components = {}

        self.components2nets = {}

    def add_part(self, part):
        assert isinstance(part, Part)
        assert part.name not in self.parts
        self.parts[part.name] = part

    def add_component(self, comp):
        assert isinstance(comp, Component)
        assert comp.name not in self.components
        assert comp.part in self.parts, comp.part
        self.components[comp.name] = comp

    def add_net(self, net):
        assert isinstance(net, Net)
        assert net.name not in self.nets
        for c in net.connections:
            assert c.component in self.components

            c2net = self.components2nets.setdefault(c.component, {})
            assert c.pin not in c2net, "Found pin %r already in schematic\n\nNew net - %r\n%r\n\nExisting - %r\n%r\n)" % (
                c, 
                net.name, net,
                c2net[c.pin], self.nets[c2net[c.pin]],
                )
            c2net[c.pin] = net.name

        self.nets[net.name] = net

    def net_for_pin(self, component, pin):
        assert pin
        netname = self.components2nets[component.name][pin]
        return self.nets[netname]

    def get_fpga(self):
        try:
            return self._fpga
        except AttributeError:
            for component in self.components.values():
                if component.part.startswith('XC6SLX'):
                    self._fpga = component.name
                    return component.name

# ---------------------------------

schematic = Schematic()
connectivity = Schematic()

for node in netfile.libparts:
    part = Part(name=node.getPartName())
    for child in node.element.getChildren():
        if child.name != 'pins':
            continue

        for pinnode in child.getChildren():
            part.add_pin(
                name=pinnode.attributes['num'],
                description=pinnode.attributes['name'],
                type=pinnode.attributes['type'])
            
    schematic.add_part(part)
    connectivity.add_part(part)

for node in netfile.getInterestingComponents():
    component = Component(
        name=node.getRef(),
        part=node.getPartName())

    schematic.add_component(component)
    connectivity.add_component(component)

for node in netfile.nets:
    new_net = Net(name=node.attributes['name'])
    for child in node.getChildren():
        new_net.add_connection(Connection(
            component=child.attributes['ref'],
            pin=Pin.format_pin(child.attributes['pin'])))

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

        part = connectivity.parts[component.part]

        other_pin = part.connected_pin(connection.pin)
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

    #if fake_name[0].startswith('Net'):
    #    continue

    fake_net = Net(name=tuple(sorted(fake_name)))
    for c in fake_connections:
        fake_net.add_connection(c)
    for p in fake_pulls:
        fake_net.pulls.add(p)

    if fake_net.name in connectivity.nets:
        existing_net = connectivity.nets[fake_net.name]
        for ca, cb in zip(list(sorted(existing_net.connections)), list(sorted(fake_net.connections))):
            assert ca.component == cb.component, "%r != %r" % (ca.component, cb.component)
            assert ca.pin == cb.pin, "%r != %r" % (ca.pin, cb.pin)
        #assert fake_net == existing_net, "\n%r\n !=\n%r" % (fake_net, existing_net)
        continue

    connectivity.add_net(fake_net)


for component in connectivity.components.values():
    if not component.name.startswith('J') or component.name.startswith('JP'):
        continue

    print "# {1} - connector {0}".format(*component)
    part = connectivity.parts[component.part]
    pins2net = connectivity.components2nets[component.name]
    for pin in sorted(part.pins.values()):
        if pin.name not in pins2net:
            continue

        net = connectivity.nets[pins2net[pin.name]]
        for connection in net.connections:
            if connection.component == connectivity.get_fpga():
                netname = part.net_name(pin.name).format(component.name.lower())
                print """\
NET "%(netname)s"%(pad)s LOC = %(fpga_pin)s IOSTANDARD = %(io_standard)s;
""" % {
    'netname': netname,
    'pad':  " "*(20 - len(netname)),
    'fpga_pin': "%s%s" % connection.pin,
    'io_standard': part.io_standard(pin.name),
    },
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

