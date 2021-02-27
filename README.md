# CDC_C4D
_repository is not yet completed_

This repository provides software and hardware to build and operate a capacitance-to-digital converter (AD7745) based capacitively coupled contactless conductivity (C4D) for capillary electrophoresis.
The setup has the following features:
- performance comparable to other C4Ds
- automated measurements
- lightweight detection head
- wireless data transmission
- battery-powerd setups 
- multi detector setups
- trigger module for popular commercial CE-Systems

All important information is included in the CDCD_Manual.pdf 

The Folder [Hardware](https://github.com/AGHuhn/CDC_C4D/tree/main/Hardware) provides:
- A list of all needed parts
- Eagle Files for detection head
- Eagle Files for supply unit
- Eagle File for a Trigger Module for an Agilent CE 7100
- Inventor Files for 3D printed case for supply unit

The Folder [Arduino](https://github.com/AGHuhn/CDC_C4D/tree/main/Arduino) contains the Firmware for the Arduinos used

The Folder [Software](https://github.com/AGHuhn/CDC_C4D/tree/main/Software) contains a python 3 script with GUI (CDC_Viewer55.pyw) to acquire the data provides by the detector(s) 

Publication in [Electrophoresis](https://onlinelibrary.wiley.com/journal/15222683) in preparation
