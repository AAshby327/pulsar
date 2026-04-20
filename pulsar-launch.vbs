' Pulsar Launch Script for Windows
' This VBScript launches WezTerm invisibly and brings it to the foreground

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
activateScript = scriptDir & "\activate.ps1"
weztermPath = scriptDir & "\bin\wezterm.exe"

' Check if WezTerm is already installed
Dim windowStyle
If objFSO.FileExists(weztermPath) Then
    ' WezTerm is installed - run hidden
    windowStyle = 0
Else
    ' WezTerm not installed - show window so user can see installation prompt
    windowStyle = 1
End If

' Build PowerShell command to activate and launch
' Setting PULSAR_PWSH_LAUNCHED prevents nested PowerShell sessions
psCommand = "powershell.exe -NoLogo -Command """ & _
            "$env:PULSAR_PWSH_LAUNCHED='1'; " & _
            ". '" & activateScript & "'; " & _
            "pulsar launch" & _
            """"

' Run the command (windowStyle: 0=hidden, 1=normal, False=don't wait)
objShell.Run psCommand, windowStyle, False

' Clean up
Set objShell = Nothing
Set objFSO = Nothing
