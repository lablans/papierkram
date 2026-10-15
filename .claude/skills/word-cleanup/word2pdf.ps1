param([string]$In, [string]$Out)
$ErrorActionPreference = 'Stop'
if (Get-Process WINWORD -ErrorAction SilentlyContinue) {
  # COM could attach to the user's running Word and hide it
  [Console]::Error.WriteLine('Word is running - ask the user to close it first.')
  exit 2
}
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($In, $false, $true, $false)
  $doc.Fields.Update() | Out-Null
  foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
  # 0/0 = no markup, final view (as after Accept All); 17 = PDF
  $doc.ActiveWindow.View.RevisionsFilter.Markup = 0
  $doc.ActiveWindow.View.RevisionsFilter.View = 0
  $doc.ExportAsFixedFormat($Out, 17, $false, 0, 0, 1, 1, 0)
  $doc.Close(0)
} finally {
  if ($word.Documents.Count -eq 0) { $word.Quit() }
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
