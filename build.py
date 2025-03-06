import argparse
import os
import shutil
import platform
import subprocess
from pathlib import Path

import nicegui

DESCRIPTION = '''
Build a package of your NiceGUI app
-----------------------------------

NiceGUI apps can be bundled into an executable with PyInstaller.
This allows you to distribute your app as a single file that can be executed on any computer.
Use this script as a starting point to create a package for your app.

Important: Make sure to run your main script with

    ui.run(reload=False, port=native.find_open_port(), ...)

to disable the reload server and to automatically find an open port.

For more information and packaging tips, have a look into the NiceGUI documentation:
https://nicegui.io/documentation/section_configuration_deployment#package_for_installation.
'''.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--name', type=str, default='Your App Name', help='Name of your app.')
    parser.add_argument('--windowed', action='store_true', default=False, help=(
        'Prevent a terminal console from appearing.\n'
        'Only use with `ui.run(native=True, ...)`.\n'
        'It will create an `.app` file on Mac which runs without showing any console output.'
    ))
    parser.add_argument('--onefile', action='store_true', default=False, help=(
        'Create a single executable file.\n'
        'Whilst convenient for distribution, it will be slower to start up.'
    ))
    parser.add_argument('--add-data', type=str, action='append', default=[
        f'{Path(nicegui.__file__).parent}{os.pathsep}nicegui',
    ], help='Include additional data.')
    parser.add_argument('--dry-run', action='store_true', help='Dry run', default=False)
    parser.add_argument('main', default='main.py', help='Main file which calls `ui.run()`.')
    parser.add_argument('--icon', type=str, help='Icon file for the program. Must be a .ico file on Windows.')
    args = parser.parse_args()

    for directory in ['build', 'dist']:
        if Path(directory).exists():
            shutil.rmtree(Path(directory))

    command = ['pyinstaller'] if platform.system() == 'Windows' else ['python', '-m', 'PyInstaller']
    command.extend(['--name', args.name])
    if args.windowed:
        command.append('--windowed')
    if args.onefile:
        command.append('--onefile')
    if args.icon:
        command.extend(['-i', args.icon])
    for data in args.add_data:
        command.extend(['--add-data', data])
    command.extend([args.main])

    print('PyInstaller command:')
    print(' ', ' '.join(command))
    if args.dry_run:
        return

    subprocess.call(command)
    shutil.copytree("static", os.path.join("dist", "bili_travail", "static"))
    shutil.copy("config.example.json", os.path.join("dist", "bili_travail"))
    shutil.copy("selenium-manager.exe", os.path.join("dist", "bili_travail"))
    guard = {
            "舰长": "guard-level-3.png",
            "提督": "guard-level-2.png",
            "总督": "guard-level-1.png"
}
    for i in guard.values():
        save_path = os.path.join("dist", "bili_travail", "data")
        save_file = os.path.join(save_path, i)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        shutil.copy(os.path.join("data", i), save_file)

    # shutil.copytree("data/gifts", os.path.join("dist", "bili_travail", "data", "gifts"))

if __name__ == '__main__':
    main()