# ZX-Spectrum-Next-Dev
Here you´ll find my own developments and contributions for the magnificent ZX Spectrum Next platform. These are binaries (dot commands) that you can download and put in your dot folder on the SD card.
Syntax is shown if you run the dot command without switches.

<li>TCPPING
<li>SSH Client (DietPi and AlpineNext)
<li>The classic PING command
<li>NXIVIEW (python)
<li>BMP2NXI (python)
<li>HDFmonkey (python)
<p><p>
  
| Filename  | Description | Additional information | Year |
| ------------- | ------------- | ------------- | ------------- |
| TCPPING | Command to ping a remote host on a known TCP port that will answer | Takes IP or FQDN as argument as well as TCP port. | 2022 |
| SSH | SSH client that makes use of the rpi0 or rpi0w to do the heavy lifting with encryption | If using rpi0, attach microusb to Ethernet dongle in one of the microusb ports of the rpi0 and connect cable to network switch. Microusb ports are exposed on the back of the computer. | 2025 |
| PING | The classic PING command in the form of DOT command using the rpi0 or rpi0w. | Same requirements as for the SSH client. It takes IP or FQDN as argument to the command. | 2025 |
| NXIVIEW | Viewing NXI files | Platform independent Python script that allows for viewing NXI files, such as the images for the cores in ZX Spectrum Next. Syntax: python nxiview.py | 2026 |
| BMP2NXI | Convert BMP to NXI | Platform independent Python script that allows for converting BMP to NXI. Syntax: python bmp2nxi.py [-t RRGGBB|none] in.bmp out.nxi | 2026 |
| HDFMONKEY | Manipulate HDF files | Platform independent Python script that allows for manipulating HDF images. Syntax: python hdfmonkey_gui.py | 2026 |
