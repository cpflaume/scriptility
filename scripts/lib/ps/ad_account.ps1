# Liest ein Service-/gMSA- bzw. User-Konto aus der Active Directory.
# Eingabe (vom Aufrufer vorbelegt): $Id  = SamAccountName des Kontos.
# Ausgabe: JSON-Objekt mit Konto-Details, oder '{}' wenn nicht gefunden.
Import-Module ActiveDirectory
$props = 'ServicePrincipalNames', 'Enabled', 'MemberOf'
$type = 'gMSA'
$a = Get-ADServiceAccount -Identity $Id -Properties $props -ErrorAction SilentlyContinue
if (-not $a) {
    $a = Get-ADUser -Identity $Id -Properties $props -ErrorAction SilentlyContinue
    $type = 'user'
}
if (-not $a) { Write-Output '{}'; exit 0 }
[pscustomobject]@{
    exists                = $true
    type                  = $type
    enabled               = [bool]$a.Enabled
    distinguishedName     = $a.DistinguishedName
    servicePrincipalNames = @($a.ServicePrincipalNames)
    memberOf              = @($a.MemberOf)
} | ConvertTo-Json -Depth 4
