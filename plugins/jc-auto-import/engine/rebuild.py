"""Rebuild only; never downloads a proprietary SDK or publishes files."""
from pathlib import Path
import argparse, shutil, subprocess

parser=argparse.ArgumentParser()
for name in ('assimp','sdk','build','cmake'):
    parser.add_argument('--'+name,required=True)
args=parser.parse_args()
source=Path(args.assimp).resolve(); sdk=Path(args.sdk).resolve(); build=Path(args.build).resolve()
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
if commit!='392a658f9c271be965271f45e7521a1b80ea4392': raise RuntimeError('Use the pinned Assimp commit')
patch=Path(__file__).parent/'assimp-jc.patch'
subprocess.run(['git','-C',str(source),'apply','--check',str(patch)],check=True)
subprocess.run(['git','-C',str(source),'apply',str(patch)],check=True)
dest=source/'contrib/Cineware'
shutil.copytree(sdk/'includes',dest/'includes',dirs_exist_ok=True,ignore=shutil.ignore_patterns('._*'))
for library in ('cinewarelib','jpeglib'):
    shutil.copytree(sdk/f'libraries/win/{library}_2019_MT',dest/f'libraries/win/{library}_2019_MT',dirs_exist_ok=True,ignore=shutil.ignore_patterns('._*'))
subprocess.run([args.cmake,'-S',str(source),'-B',str(build),'-G','Visual Studio 17 2022','-A','x64',
 '-DASSIMP_BUILD_TESTS=OFF','-DASSIMP_BUILD_ASSIMP_TOOLS=ON','-DASSIMP_BUILD_SAMPLES=OFF',
 '-DBUILD_SHARED_LIBS=OFF','-DASSIMP_BUILD_ZLIB=ON','-DASSIMP_INSTALL=OFF',
 '-DASSIMP_BUILD_ALL_IMPORTERS_BY_DEFAULT=ON','-DASSIMP_BUILD_NONFREE_C4D_IMPORTER=ON',
 '-DASSIMP_BUILD_ALL_EXPORTERS_BY_DEFAULT=OFF','-DASSIMP_BUILD_GLTF_EXPORTER=ON',
 '-DASSIMP_BUILD_OBJ_EXPORTER=ON','-DASSIMP_BUILD_ASSBIN_EXPORTER=ON','-DASSIMP_BUILD_ASSXML_EXPORTER=ON',
 '-DASSIMP_WARNINGS_AS_ERRORS=OFF','-DUSE_STATIC_CRT=ON'],check=True)
subprocess.run([args.cmake,'--build',str(build),'--config','Release','--parallel','8'],check=True)
output=Path(__file__).resolve().parents[1]/'jc_auto_import/bin/jc_converter.exe'
shutil.copyfile(build/'bin/Release/assimp.exe',output)
print(output)
