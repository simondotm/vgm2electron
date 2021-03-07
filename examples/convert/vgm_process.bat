@echo off


for %%x in (*.vgm) do c:\\python27\\python.exe vgmconverter.py "%%x" -t bbc -q 50 -o "beeb\%%~nx.vgm"




