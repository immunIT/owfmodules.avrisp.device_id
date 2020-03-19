# -*- coding:utf-8 -*-

# Octowire SPI flash id module
# Copyright (c) Jordan Ovrè / Paul Duncan
# License: GPLv3
# Paul Duncan / Eresse <eresse@dooba.io>
# Jordan Ovrè / Ghecko <ghecko78@gmail.com


import codecs

from octowire.spi import SPI
from octowire.gpio import GPIO
from octowire_framework.module.AModule import AModule


class DeviceID(AModule):
    def __init__(self, owf_config):
        super(DeviceID, self).__init__(owf_config)
        self.meta.update({
            'name': 'AVR device ID',
            'version': '1.0.0',
            'description': 'Module getting the ID of an AVR device using the SPI interface along with a Reset line '
                           '(GPIO).',
            'author': 'Jordan Ovrè <ghecko78@gmail.com> / Paul Duncan <eresse@dooba.io>'
        })
        self.options = [
            {"Name": "spi_bus", "Value": "", "Required": True, "Type": "int",
             "Description": "The octowire SPI bus (0=SPI0 or 1=SPI1)", "Default": 0},
            {"Name": "reset_line", "Value": "", "Required": True, "Type": "int",
             "Description": "The octowire GPIO used as the Reset line", "Default": 0},
            {"Name": "spi_baudrate", "Value": "", "Required": True, "Type": "int",
             "Description": "set SPI baudrate (1000000 = 1MHz) maximum = 50MHz", "Default": 1000000},
        ]

    def manage_resp(self, msg, resp):
        if resp is not None:
            self.logger.handle("{}: {}".format(msg, codecs.encode(resp, 'hex').decode().upper()), self.logger.RESULT)
        else:
            self.logger.handle("Unable to get a response while reading the device response", self.logger.ERROR)

    def process(self, spi_interface, reset):
        read_device_id_base_cmd = b'\x30\x00'

        # Asking vendor ID
        spi_interface.transmit(read_device_id_base_cmd + b'\x00\x00')
        vendor_id = spi_interface.receive(1)
        self.manage_resp(msg="Vendor ID", resp=vendor_id)

        # Asking Part Family and Flash size
        spi_interface.transmit(read_device_id_base_cmd + b'\x01\x00')
        part_family_and_size = spi_interface.receive(1)
        self.manage_resp(msg="Part Family and Flash Size", resp=part_family_and_size)

        # Asking Part Number
        spi_interface.transmit(read_device_id_base_cmd + b'\x02\x00')
        part_number = spi_interface.receive(1)
        self.manage_resp(msg="Part Family and Flash Size", resp=part_number)

        # Todo: print human readable part here (AT90S1200) and check for invalid response
        # http://www.oocities.org/ve2olm/doc0943.pdf


    def device_id(self):
        bus_id = self.get_option_value("spi_bus")
        reset_line = self.get_option_value("reset_line")
        spi_baudrate = self.get_option_value("spi_baudrate")

        enable_mem_access_cmd = b'\xac\x53\x00\x00'

        spi_interface = SPI(serial_instance=self.owf_serial, bus_id=bus_id)
        reset = GPIO(serial_instance=self.owf_serial, gpio_pin=reset_line)

        reset.direction = GPIO.OUTPUT
        # Active Reset is low
        reset.status = 1
        # Configure SPI with default phase and polarity
        spi_interface.configure(baudrate=spi_baudrate)

        self.logger.handle("Enable Memory Access...", self.logger.INFO)
        # Drive reset low
        reset.status = 0
        # Enable Memory Access
        spi_interface.transmit(enable_mem_access_cmd)

        self.logger.handle("Read device ID...", self.logger.INFO)
        self.process(spi_interface, reset)

        # Drive reset high
        reset.status = 1

    def run(self, return_value=False):
        """
        Main function.
        Print/return the ID of an AVR device.
        :return: Nothing or bytes, depending of the 'return_value' parameter.
        """
        # If detect_octowire is True then Detect and connect to the Octowire hardware. Else, connect to the Octowire
        # using the parameters that were configured. It sets the self.owf_serial variable if the hardware is found.
        self.connect()
        if not self.owf_serial:
            return None
        try:
            device_id = self.device_id()
            if return_value:
                return device_id
            return None
        except (Exception, ValueError) as err:
            self.logger.handle(err, self.logger.ERROR)
