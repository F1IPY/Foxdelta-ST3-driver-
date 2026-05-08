The Foxdelta ST3 interface (https://www.foxdelta.com/projects/st3.htm) is not compatible with software with TCPIP rotor control (like Gpredict). The hamlib Roctld daemon cannot be used.
The problem is that the interface doesnt respond for any command on the serial port so no answer on TCPIP port that is mandatory for many software. The script emulate answer on the TCPIP port. The script is a bridge from Foxdelta ST3 interface to sowtware like Gpredict.

