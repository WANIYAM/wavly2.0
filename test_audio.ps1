Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Speak("Hello, can you hear this audio test?")
Write-Host "PowerShell speech test done"
