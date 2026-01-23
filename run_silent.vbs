Set UAC = CreateObject("Shell.Application")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptPath = FSO.GetParentFolderName(WScript.ScriptFullName)
UAC.ShellExecute "pythonw.exe", """" & scriptPath & "\translator.py""", scriptPath, "runas", 0
