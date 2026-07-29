# Liest Gruppen inkl. rekursiver Mitglieder aus der Active Directory.
# Eingabe (vom Aufrufer vorbelegt): $Names = String-Array von Gruppennamen.
# Ausgabe: JSON-Array von Gruppen-Objekten (name, exists, distinguishedName, members).
Import-Module ActiveDirectory
$out = foreach ($n in $Names) {
    $g = Get-ADGroup -Identity $n -ErrorAction SilentlyContinue
    if (-not $g) {
        [pscustomobject]@{ name = $n; exists = $false; distinguishedName = $null; members = @() }
        continue
    }
    $members = foreach ($m in (Get-ADGroupMember -Identity $g -Recursive -ErrorAction SilentlyContinue)) {
        [pscustomobject]@{ name = $m.SamAccountName; objectClass = $m.objectClass }
    }
    [pscustomobject]@{
        name              = $g.Name
        exists            = $true
        distinguishedName = $g.DistinguishedName
        members           = @($members)
    }
}
@($out) | ConvertTo-Json -Depth 5
