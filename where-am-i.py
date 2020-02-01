#!/usr/bin/env python

import sys
import dbus
import traceback

from gi.repository import Gtk
from gi.repository import GtkClutter
from gi.repository import GObject
from gi.repository import Champlain
from dbus.mainloop.glib import DBusGMainLoop


system_bus = None

GEOCLUE2_BUS_NAME = 'org.freedesktop.GeoClue2'
MANAGER_INTERFACE_NAME = GEOCLUE2_BUS_NAME + '.Manager'
CLIENT_INTERFACE_NAME = GEOCLUE2_BUS_NAME + '.Client'
LOCATION_INTERFACE_NAME = GEOCLUE2_BUS_NAME + '.Location'
PROPERTIES_INTERFACE_NAME = 'org.freedesktop.DBus.Properties'


def get_object(bus, name, object_path):
    '''
    This function returns a dbus proxy object located at the path
    provided in object_path
    '''
    try:
        return bus.get_object(name, object_path)
    except dbus.DBusException:
        traceback.print_exc()
        sys.exit(1)

def get_interface(proxy_object, interface_name):
    '''
    This function takes a proxy object and returns the interface whose name
    is provided in interface_name
    '''
    try:
        return dbus.Interface(proxy_object, interface_name)
    except dbus.DBusException:
        traceback.print_exc()
        sys.exit(1)

def get_property(properties_interface, interface_name, property_name):
    '''
    This function gets the value of a property. Parameters are -
    the property interface, interface name where the property is located,
    and the name of the property to be fetched
    '''
    try:
        return properties_interface.Get(interface_name, property_name)
    except dbus.DBusException:
        traceback.print_exc()
        sys.exit(1)

def set_property(properties_interface, interface_name, property_name, value):
    '''
    This function gets the value of a property. Parameters are -
    the property interface, interface name where the property is located,
    the name of the property to be fetched and the value to be set
    '''
    try:
        return properties_interface.Set(interface_name, property_name, value)
    except dbus.DBusException:
        traceback.print_exc()
        sys.exit(1)

def location_updated(old_path, new_path):
    '''
    When 'LocationUpdated' signal gets emitted, this function gets called
    It fetches the location object located at the new path, and prints the
    location details
    '''
    location_object = get_object(system_bus, GEOCLUE2_BUS_NAME, new_path)
    location_properties = get_interface(location_object,
                               PROPERTIES_INTERFACE_NAME)
    latitude = get_property(location_properties, LOCATION_INTERFACE_NAME,
                            'Latitude')
    longitude = get_property(location_properties, LOCATION_INTERFACE_NAME,
                            'Longitude')
    accuracy = get_property(location_properties, LOCATION_INTERFACE_NAME,
                            'Accuracy')
    description = get_property(location_properties, LOCATION_INTERFACE_NAME,
                            'Description')
    print("Latitude = " + str(latitude))
    print("Longitude = " + str(longitude))
    print("Accuracy = " + str(accuracy))
    print("Description = " + str(description))

    show_position_on_map(latitude, longitude)

def show_position_on_map(latitude, longitude):
    GtkClutter.init([])
    window = Gtk.Window()
    window.connect("delete-event", Gtk.main_quit)
    window.set_default_size(500, 350)

    map_to_show = get_map(latitude, longitude)

    window.add(map_to_show)
    window.show_all()
    Gtk.main()

def get_map(latitude, longitude):
    view = Champlain.View()
    view.set_kinetic_mode(True)
    view.set_property("zoom-level", 12)
    view.set_reactive(True)
    view.set_size(500, 350)
    view.center_on(latitude, longitude)

    embed = GtkClutter.Embed.new()
    embed.realize()
    stage = embed.get_stage()
    stage.add_actor(view)

    return embed

def main():
    print("This code will print your location and exit after 10 seconds")

    global system_bus

    # In order to make asynchronous calls, we need to setup an event loop
    # Go ahead and try removing this, the 'connect_to_signal' method
    # at the bottom won't work
    dbus_loop = DBusGMainLoop(set_as_default = True)

    # We connect to the system bus as GeoClue2 is located there
    system_bus = dbus.SystemBus(mainloop = dbus_loop)

    # We get the proxy object and then the interface
    manager_object = get_object(system_bus, GEOCLUE2_BUS_NAME,
                                '/org/freedesktop/GeoClue2/Manager')
    manager = get_interface(manager_object, MANAGER_INTERFACE_NAME)

    # GetClient() returns the path to the newly created client object
    client_path = manager.GetClient()
    client_object = get_object(system_bus, GEOCLUE2_BUS_NAME, client_path)

    # We set the 'DistanceThreshold' property before starting client.
    # This property decides how often 'LocationUpdated' signal is emitted
    # If the distance moved is below threshold, the signal won't be emitted
    # We have set this to 1000 meters
    client_properties = get_interface(client_object, PROPERTIES_INTERFACE_NAME)
    set_property(client_properties, CLIENT_INTERFACE_NAME,
                 'DistanceThreshold', dbus.UInt32(1000))
    set_property(client_properties, CLIENT_INTERFACE_NAME,
                 'DesktopId', 'GeoClue2-Locator-python')

    client = get_interface(client_object, CLIENT_INTERFACE_NAME)

    # Connect to the 'LocationUpdated' signal before starting the client
    client.connect_to_signal('LocationUpdated', location_updated)

    # Start receiving events about current location
    client.Start()

    loop = GObject.MainLoop()

    # Quit after 10 seconds
    GObject.timeout_add(10000, loop.quit)
    loop.run()
    client.Stop()
    print("If no location was printed, run geoclue as root in another terminal -")
    print("Path to the executable is in 'org.freedesktop.GeoClue2.service' file")

main()
