# User interface DDC264EVM_UI for DDC264EVM board

This software was created to record data from board [DDC264EVM](https://www.mouser.com/datasheet/2/405/sbau186-124984.pdf?srsltid=AfmBOorEEgAYgOaRBD1N2l7HP0iqDXy_jllDeBUeok_HDVKO7DB86BW0) automatically. USB communication was established via [USB_IO_for_VB6.dll](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/73/0216.USB_5F00_IO_5F00_for_5F00_VB6_5F00_DLL_5F00_User_5F00_Guide.pdf) (It is important to mention that it was written for 32bit compilator). As UI tool it uses framework PyQt5.

## Installation and usage
Install 32-bit python on Windows and run the following commands with it:

```powershell
python -m venv env
.\env\Scripts\Activate
```
Install necessary modules:
```powershell
pip install -r requirements.txt 
```
Run app:

```powershell
python main.py
```