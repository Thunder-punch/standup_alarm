import os
import sys
import winshell
from win32com.client import Dispatch

# 실행파일 경로
exe_path = os.path.abspath('dist/alarm_gui.exe')
# 윈도우 시작프로그램 폴더 경로
startup = winshell.startup()
shortcut_path = os.path.join(startup, '플랩시계알람.lnk')

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(shortcut_path)
shortcut.Targetpath = exe_path
shortcut.WorkingDirectory = os.path.dirname(exe_path)
shortcut.IconLocation = exe_path
shortcut.save()

print(f'시작프로그램에 바로가기 등록 완료: {shortcut_path}') 