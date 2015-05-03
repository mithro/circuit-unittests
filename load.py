#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

import sys
import kicad_netlist_reader
netfile = kicad_netlist_reader.netlist(sys.argv[1])

# ---------------------------------

def getpins(comp):
    pins = []
    for node in comp.getLibPart().element.getChild('pins').getChildren():
        pin = node.attributes['num']
        try:
            pin = int(pin)
        except ValueError:
            pass

        pins.append(pin)
    pins.sort()
    return pins

def power_type(netname):
    if "VCC" in netname:
        return "VCC"
    if "GND" in netname:
        return "GND"
    return None

# ---------------------------------

nets = {}
for node in netfile.nets:
    netname = node.attributes['name']
    assert netname not in nets 
    nets[netname] = node

# ---------------------------------
# Associate nets with components
# ---------------------------------

components_nets = {}
for netname, node in nets.items():
    for child in node.getChildren():
        comp_ref = child.attributes['ref']

        comp_pin = child.attributes['pin']
        try:
            comp_pin = int(comp_pin)
        except ValueError:
            pass

        component_pins = components_nets.setdefault(comp_ref, {})
        if comp_pin in component_pins:
            assert netname == component_pins[comp_pin], "%s %s %s" % (comp_pin, component_pins[comp_pin], netname)
        else:
            component_pins[comp_pin] = netname

# ---------------------------------
# Sort the components into types
# ---------------------------------

# Find the FPGA component
passives = {}
components = {}
fpga = None
for component in netfile.getInterestingComponents():
    if component.getPartName().startswith('XC6SLX'):
        if fpga:
            raise IOError("Duplicate FPGA found.")
        fpga = component
    elif component.getPartName() in ('R', 'C'): #, 'RES_NET4'):
        assert len(getpins(component)) == 2
        passives[component.getRef()] = component
    else:
        components[component.getRef()] = component

if not fpga:
    raise IOError("FPGA part not found")

# ---------------------------------
# Work out connections through passive components
# ---------------------------------

from collections import namedtuple
Pull = namedtuple('Pull', ['net', 'by', 'to', 'type'])
Connection = namedtuple('Connection', ['by', 'to'])

connected_nets = {}
pulled = {}
for netname, node in nets.items():
    if power_type(netname):
        continue

    # Work out the passives connected to this net and the other nets these
    # passives are connected too.
    net_passives = {}
    for node in node.getChildren():
        ref = node.attributes['ref']
        if ref not in passives:
            continue
        net_passives[ref] = set(components_nets[ref].values())

    if not net_passives:
        continue

    # Work out if these are connected to a power plane or another signal net.
    net_pullups = []
    net_pulldowns = []
    connections = []
    for ref, all_nets in net_passives.items():
        # Exclude the current net
        other_nets = all_nets - set([netname])
        assert netname not in other_nets

        # Passives connected to power nets should only have one other
        # connection.
        if len(other_nets) == 1:
            other_net = list(other_nets)[0]
            pulltype = power_type(other_net)
            if pulltype:
                pulled.setdefault(netname, set()).add(Pull(net=netname, by=ref, to=other_net, type=pulltype))
                continue

        for other_net in other_nets:
            assert not power_type(other_net)
            assert netname != other_net
            connected_nets.setdefault(netname, set()).add(Connection(by=ref, to=other_net))

# Reduce the connected nets
def full_path(path):
    last_net = path[-1]

    for connection in connected_nets.get(last_net, []):
        if connection.to in path:
            continue

        path.append(connection.to)
        full_path(path)

full_connections = set()
for net in connected_nets:
    path = []
    path.append(net)
    full_path(path)
    path.sort()
    full_connections.add(tuple(path))

connections = {}
for connection in full_connections:
    for netname in connection:
        connections[netname] = connection

# ---------------------------------

class NC(object):
    pass

Connected = namedtuple("Connected", ['net', 'component', 'pin'])
ConnectedVia = namedtuple("ConnectedVia", ['net', 'component', 'path'])

component_annotated = {}
for comp_ref, comp_node in components.items():
    comp_pins = getpins(comp_node)
    comp_nets = components_nets[comp_ref]

    annotated = {}
    for pin in comp_pins:
        if pin not in comp_nets:
            annotated[pin] = NC()
            continue

        pin_netname = comp_nets[pin]
        pin_nets = [pin_netname]
        if pin_netname in connections:
            pin_nets = connections[pin_netname]
        
        connections = set()
        for net in pin_nets:
            net_node = nets[net]
            for child in net_node.getChildren():
                connections.add(Connected(net=netname, component=child.attributes['ref'], pin=child.attributes['pin']))

        assert connections, pin_nets
        assert pin not in annotated
        annotated[pin] = connections
        continue

        print comp_ref, pin, connections

        pin_netname = comp_nets[pin]
        if pin_netname in pulled:
            annotated[pin] = pulled[pin_netname]
            continue
        elif pin_netname in connections:
            annotated[pin] = [ConnectedVia(net=pin_netname, components=[], path=[])]
        else:
            annotated[pin] = Connected(net=pin_netname, components=[])

    component_annotated[comp_ref] = annotated

import pprint
pprint.pprint(component_annotated)

"""


import pprint
pprint.pprint(connections)

def simple_nets():
    for netname, node in nets.items():
        if power_type(netname):
            continue

        if netname in connected_nets:
            continue
        yield [node]

    for netnames in connections:
        yield [nets[netname] for netname in netnames]


FPGAConnection = namedtuple("FPGAConnection", ['pins', 'netnames', 'pulls'])

components_info = {}
for nodes in simple_nets():
    children = []
    for net_node in nodes:
        for child in net_node.getChildren():
            children.append((net_node, child))

    for net_node, comp_node in children:
        comp_ref = comp_node.attributes['ref']
        comp_pin = comp_node.attributes['pin']
        if comp_ref in passives:
            continue

        component_info = components_info.setdefault(comp_ref, {})
        pin_info = component_info.setdefault(comp_pin, set())
        pin_info.append(net_node)

component_to_nets = {}

fgpa_to_components = {}
    fpga_nodes = []
    component_nodes = []
    for net_node, comp_node in children:
        comp_ref = comp_node.attributes['ref']
        if comp_ref in passives:
            continue

        if comp_ref == fpga_ref:
            fpga_nodes.append((net_node, comp_node))
        else:
            component_nodes.append((net_node, comp_node))
    del net_node, comp_node

    # Net isn't connected to the FPGA
    if not fpga_nodes:
        continue

    #for net_node, child in fpga_nodes:
    #    if net_node.attributes['name'] in pulled:
    for comp_netnode, comp_node in component_nodes:
        comp_ref = comp_node.attributes['ref']

        comp_pin = comp_node.attributes['pin']
        try:
            comp_pin = int(comp_pin)
        except ValueError:
            pass

        component_pins_to_fpga = components_to_fpga.setdefault(comp_ref, {})
        pin_to_fpga = component_pins_to_fpga.setdefault(comp_pin, set())
        for fpga_netnode, fpga_node in fpga_nodes:
            pin_to_fpga.add(((comp_netnode.attributes['name'], fpga_netnode.attributes['name']), fpga_node.attributes['pin']))

for ref, component_pins_to_fpga in components_to_fpga.items():
    component = components[ref]

    print component.getRef(), component.getPartName()

    for pin in getpins(component):
        if pin not in component_pins_to_fpga:
            print "    %s not connected to the FPGA" % pin
        else:
            print "    %s is connected to the following FPGA pins" % pin
            for (comp_net, fpga_net), fpga_pin in sorted(component_pins_to_fpga[pin]):
                print "        ", fpga_pin,
                if comp_net == fpga_net:
                    print comp_net
                else:
                    print comp_net, "->", fpga_net

    print

    for node in fpga_nodes:
        pin = node.attributes['pin']
        fpga_pin_names[pin] = netname

        # Power planes are connected to a lot of different things, so lets just
        # ignore them.
        if "VCC" in netname or "GND" in netname:
            fpga_pin_connects[pin] = []
        else:
            fpga_pin_connects[pin] = component_nodes

    for comp_node in component_nodes:
        netname = net.attributes['name']
        for fpga_node in fpga_nodes:
            pin = node.attributes['pin']
            components_to_fpga[comp_node.component.getRef()].append((net, pin))



for pin in sorted(fpga_pin_names.keys()):
    print pin, fpga_pin_names[pin]
    for node in fpga_pin_connects[pin]:
        if node.component.getPartName() in ('R', 'C'):
            continue
        print "    ", node.component.getPartName(), node.attributes['ref'], node.attributes['pin']


print(fpga.getFieldNames())
print(fpga.getDescription())

"""
