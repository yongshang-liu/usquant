import pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parents[1]
ext = '.dylib' if sys.platform == 'darwin' else '.so'
(root/'build').mkdir(exist_ok=True)
subprocess.run(['c++','-std=c++17','-O2','-Wall','-Wextra','-shared','-fPIC',str(root/'cpp/indicators.cpp'),'-o',str(root/'build'/('libindicators'+ext))],check=True)
print('Built C++ indicators')
