from setuptools import setup

APP = ['mac_client.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'Life Companion Lauburu',
        'CFBundleDisplayName': 'Life Companion Lauburu',
        'CFBundleGetInfoString': "Lauburu Mesh VLA",
        'CFBundleIdentifier': "com.lauburu.lifecompanion",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0",
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
