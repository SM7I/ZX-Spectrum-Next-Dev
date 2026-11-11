# ZX-Spectrum-Next-Dev
Here you´ll find my own developments and contributions for the magnificent ZX Spectrum Next platform. These are binaries (dot commands) that you can download and put in your dot folder on the SD card.
Syntax is shown if you run the dot command without switches.
Please not that Python scripts / tools can *not* be run on the ZX Spectrum Next, only on platforms supporting Python language, such as Linux, Windows and Mac.

<li>TCPPING
<li>SSH Client (DietPi and AlpineNext)
<li>The classic PING command
<li>NXIVIEW (python)
<li>BMP2NXI (python)
<li>HDFmonkey (python)
<li>ALPWIFI
<li>C64.NXI
<p><p>
  
| Filename  | Description | Additional information | Year |
| ------------- | ------------- | ------------- | ------------- |
| TCPPING | Command to ping a remote host on a known TCP port that will answer | Takes IP or FQDN as argument as well as TCP port. Syntax: .TCPPING <IPaddress or FQDN> | 2022 |
| SSH | SSH client that makes use of the rpi0 or rpi0w to do the heavy lifting with encryption | If using rpi0, attach microusb to Ethernet dongle in one of the microusb ports of the rpi0 and connect cable to network switch. Microusb ports are exposed on the back of the computer. Syntax: .SSHDIET (or .SSHALPIN) <user host port>| 2025 |
| PING | The classic PING command in the form of DOT command using the rpi0 or rpi0w. | Same requirements as for the SSH client. It takes IP or FQDN as argument to the command. Syntax: .PING <IPaddress or FQDN> | 2025 |
| NXIVIEW | Viewing NXI files | Platform independent Python script that allows for viewing NXI files, such as the images for the cores in ZX Spectrum Next. Syntax: python nxiview.py | 2026 |
| BMP2NXI | Convert BMP to NXI | Platform independent Python script that allows for converting BMP to NXI. Syntax: python bmp2nxi.py <-t RRGGBB none> <-d> <-n> <-k N> in.bmp out.nxi | 2026 |
| HDFMONKEY | Manipulate HDF files | Platform independent Python script that allows for manipulating HDF images. Syntax: python hdfmonkey_gui.py | 2026 |
| ALPWIFI | WiFi setup rpi0w | WiFi setup tool for rpi0w. Syntax: .ALPWIFI | 2026 |
| C64.NXI | NXI image for C64 core | NXI image to accompany the C64 core. Put in C64 folder and rename to 'core.nxi'. This is actually a photo of my own C64 that I converted using my own Python tools | 2026 |
