# Findet Gruppennamen ueber einen AD-Name-Filter (Wildcard).
# Eingabe (vom Aufrufer vorbelegt): $Pattern = Wildcard, z.B. 'App-XYZ-*'.
# Ausgabe: JSON-Array von Gruppennamen.
Import-Module ActiveDirectory
@(Get-ADGroup -Filter "Name -like '$Pattern'" | Select-Object -ExpandProperty Name) | ConvertTo-Json
