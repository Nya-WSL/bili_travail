import argparse
import os
import platform
import subprocess
from pathlib import Path

import nicegui

def main() -> None:
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
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

if __name__ == '__main__':
    main()