' Pulsar Activation Script for Windows
' This VBScript launches PowerShell with execution policy bypass and sources activate.ps1

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
activateScript = scriptDir & "\activate.ps1"

' Check if activate.ps1 exists
If Not objFSO.FileExists(activateScript) Then
    MsgBox "Error: activate.ps1 not found in " & scriptDir, vbCritical, "Pulsar Activation Error"
    WScript.Quit 1
End If

' Build PowerShell command with ExecutionPolicy Bypass
' -NoExit keeps the PowerShell window open after sourcing activate.ps1
' -ExecutionPolicy Bypass bypasses the execution policy for this session
psCommand = "powershell.exe -NoExit -ExecutionPolicy Bypass -NoLogo -Command """ & _
            ". '" & activateScript & "'" & _
            """"

' Run the command
' windowStyle: 1 = normal window (visible)
' waitOnReturn: False = don't wait (let PowerShell stay open)
objShell.Run psCommand, 1, False

' Clean up
Set objShell = Nothing
Set objFSO = Nothing
