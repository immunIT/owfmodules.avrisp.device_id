# -*- coding:utf-8 -*-

# Octowire Framework
# Copyright (c) ImmunIT - Jordan Ovrè / Paul Duncan
# License: Apache 2.0
# Paul Duncan / Eresse <pduncan@immunit.ch>
# Jordan Ovrè / Ghecko <jovre@immunit.ch>

import codecs

from octowire.spi import SPI
from octowire.gpio import GPIO
from octowire_framework.module.AModule import AModule
from owfmodules.avrisp.avrisp_devices import avr_device


class DeviceID(AModule):
    def __init__(self, owf_config):
        super(DeviceID, self).__init__(owf_config)
        self.meta.update({
            'name': 'AVR device identification',
            'version': '1.0.2',
            'description': 'Identify AVR microcontrollers',
            'author': 'Jordan Ovrè <jovre@immunit.ch> / Paul Duncan <pduncan@immunit.ch>'
        })
        self.options = {
            "spi_bus": {"Value": "", "Required": True, "Type": "int",
                        "Description": "SPI bus (0=SPI0 or 1=SPI1)", "Default": 0},
            "reset_line": {"Value": "", "Required": True, "Type": "int",
                           "Description": "GPIO used as the Reset line", "Default": 0},
            "spi_baudrate": {"Value": "", "Required": True, "Type": "int",
                             "Description": "SPI frequency (1000000 = 1MHz). Minimum:240kHz - Maximum: 60MHz",
                             "Default": 1000000}
        }

    def check_signature(self, vendor_id, part_family, part_number):
        if vendor_id == b"\x00" and part_family == b"\x01" and part_number == b"\x02":
            self.logger.handle("Device Locked (Lock bits have been set). This prevents the memory from being read. "
                               "To erase the Lock bits, it is necessary to perform a valid 'Chip Erase'.",
                               self.logger.ERROR)
            return False
        elif vendor_id in [b"\x00", b"\xFF"]:
            self.logger.handle("The device is locked or not ready", self.logger.ERROR)
            return False
        if part_family == b"\xFF" and part_number == b"\xFF":
            self.logger.handle("Device Code Erased (or Target Missing)", self.logger.ERROR)
            return False
        return True

    def get_device_info(self, signature):
        for device_signature, device_info in avr_device.items():
            if device_signature == signature:
                self.logger.handle("Device name: {}".format(device_info["name"]), self.logger.RESULT)
                self.logger.handle("Device flash size: {}".format(device_info["flash_size"]), self.logger.RESULT)
                self.logger.handle("Device flash page size: {}".format(device_info["flash_pagesize"]),
                                   self.logger.RESULT)
                self.logger.handle("Device EEPROM size: {}".format(device_info["eeprom_size"]), self.logger.RESULT)
                return device_info
        else:
            self.logger.handle("Device ID not found.")
            return None

    def manage_resp(self, msg, resp):
        if resp is not None:
            self.logger.handle("{}: {}".format(msg, codecs.encode(resp, 'hex').decode().upper()), self.logger.SUCCESS)
        else:
            raise Exception("Unable to get a response from the device")

    def process(self, spi_interface, reset):
        read_device_id_base_cmd = b'\x30\x00'
        enable_mem_access_cmd = b'\xac\x53\x00\x00'

        self.logger.handle("Enabling Memory Access...", self.logger.INFO)
        # Drive reset low
        reset.status = 0
        # Enable Memory Access
        spi_interface.transmit(enable_mem_access_cmd)

        # Asking vendor ID
        spi_interface.transmit(read_device_id_base_cmd + b'\x00')
        vendor_id = spi_interface.receive(1)
        self.manage_resp(msg="Vendor ID", resp=vendor_id)

        # Asking Part Family and Flash size
        spi_interface.transmit(read_device_id_base_cmd + b'\x01')
        part_family_and_size = spi_interface.receive(1)
        self.manage_resp(msg="Part Family and Flash Size", resp=part_family_and_size)

        # Asking Part Number
        spi_interface.transmit(read_device_id_base_cmd + b'\x02')
        part_number = spi_interface.receive(1)
        self.manage_resp(msg="Part number", resp=part_number)

        # Drive reset high
        reset.status = 1

        # If the device signature is correct, return device information
        if self.check_signature(vendor_id=vendor_id, part_family=part_family_and_size, part_number=part_number):
            signature = codecs.encode(vendor_id + part_family_and_size + part_number, 'hex').decode()
            return self.get_device_info(signature)
        else:
            return None

    def device_id(self):
        bus_id = self.options["spi_bus"]["Value"]
        reset_line = self.options["reset_line"]["Value"]
        spi_baudrate = self.options["spi_baudrate"]["Value"]


        spi_interface = SPI(serial_instance=self.owf_serial, bus_id=bus_id)
        reset = GPIO(serial_instance=self.owf_serial, gpio_pin=reset_line)
        reset.direction = GPIO.OUTPUT

        # Reset is active-low
        reset.status = 1

        # Configure SPI with default phase and polarity
        spi_interface.configure(baudrate=spi_baudrate)

        self.logger.handle("Reading device ID...", self.logger.INFO)
        return self.process(spi_interface, reset)

    def run(self, return_value=False):
        """
        Main function.
        Print/return the ID of an AVR device.
        :return: Nothing or bytes, depending of the 'return_value' parameter.
        """
        # If detect_octowire is True then detect and connect to the Octowire hardware. Else, connect to the Octowire
        # using the parameters that were configured. This sets the self.owf_serial variable if the hardware is found.
        self.connect()
        if not self.owf_serial:
            return None
        try:
            device_info = self.device_id()
            if return_value:
                return device_info
            return None
        except (Exception, ValueError) as err:
            self.logger.handle(err, self.logger.ERROR)
