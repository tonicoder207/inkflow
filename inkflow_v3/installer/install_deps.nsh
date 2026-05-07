; InkFlow — NSIS Post-Install Hook
; Runs after files are copied to install dir
; Installs Python dependencies using embedded Python

!macro customInstall
  DetailPrint "Installiere Python-Abhängigkeiten..."
  
  ; Path to embedded python and pip
  StrCpy $0 "$INSTDIR\resources\python\python.exe"
  StrCpy $1 "$INSTDIR\resources\backend\requirements.txt"
  
  ; Check if python exists
  IfFileExists "$0" 0 NoPython
  
  ; Run pip install
  nsExec::ExecToLog '"$0" -m pip install -r "$1" --quiet --no-warn-script-location'
  Pop $2
  ${If} $2 != 0
    MessageBox MB_OK "Hinweis: Abhängigkeiten konnten nicht installiert werden.$\nApp startet trotzdem, aber OneNote-Integration funktioniert möglicherweise nicht."
  ${EndIf}
  Goto Done
  
  NoPython:
  DetailPrint "Embedded Python nicht gefunden - überspringe pip install"
  
  Done:
  DetailPrint "Installation abgeschlossen"
!macroend

!macro customUnInstall
  ; Nothing special needed on uninstall
!macroend
