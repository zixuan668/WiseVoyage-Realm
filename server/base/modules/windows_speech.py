"""Offline Windows speech fallback, with explicit gender/language matching.

Speech text is JSON on stdin, never shell code. It does not change voices,
registry settings, default devices, system volume or installed languages.
"""
import asyncio
import json
import os
import subprocess
import shutil
from pathlib import Path
from loguru import logger

SCRIPT=r'''
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$ErrorActionPreference = 'Stop'
$job = [Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $voices = $speaker.GetInstalledVoices() | Where-Object {
    $_.Enabled -and $_.VoiceInfo.Gender.ToString().ToLowerInvariant() -eq $job.gender -and
    $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq $job.language
  }
  $voice = $voices | Select-Object -First 1
  if (-not $voice) { '{"available":false}'; exit 0 }
  $speaker.SelectVoice($voice.VoiceInfo.Name)
  $speaker.SetOutputToWaveFile($job.path)
  $text = [System.Security.SecurityElement]::Escape($job.text)
  $culture = $voice.VoiceInfo.Culture.Name
  $ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="' + $culture + '"><prosody rate="' + $job.rate + '">' + $text + '</prosody></speak>'
  $speaker.SpeakSsml($ssml)
  @{available=$true;name=$voice.VoiceInfo.Name} | ConvertTo-Json -Compress
} finally { $speaker.Dispose() }
'''


async def synthesize_windows(text: str, voice_style: str, speed: float, output_file: str, language: str) -> str:
    if os.name != 'nt' or not text:
        return ''
    path=Path(output_file).with_suffix('.wav')
    job={'text':text,'gender':'male' if voice_style.startswith('male_') else 'female',
         'language':'en' if language=='en' else 'zh','path':str(path.resolve()),
         'rate':f'{round((speed-1)*100):+d}%'}
    try:
        result=await asyncio.to_thread(subprocess.run,
            [shutil.which('pwsh') or 'powershell.exe','-NoProfile','-NonInteractive','-Sta','-Command',SCRIPT],
            input=json.dumps(job,ensure_ascii=False),capture_output=True,text=True,encoding='utf-8',
            timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            logger.warning('Offline speech synthesis unavailable')
        elif json.loads(result.stdout.strip()).get('available') and path.exists() and path.stat().st_size>44:
            logger.info('Offline speech synthesized (gender={}, language={}, rate={})',job['gender'],job['language'],job['rate'])
            return str(path)
    except (OSError,ValueError,subprocess.TimeoutExpired):
        logger.warning('Offline speech fallback unavailable')
    path.unlink(missing_ok=True)
    return ''
