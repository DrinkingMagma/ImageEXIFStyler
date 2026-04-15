# Packaging

The project is packaged from the `ies` conda environment with PyInstaller.

```powershell
conda activate ies
.\build_exe.ps1 -InstallPyInstaller -Clean
```

By default the script uses PyInstaller `onedir` mode. The main exe stays small, while Python, Qt, Pillow, and other runtime binaries are placed next to it as DLLs and support files:

```text
dist\
  ImageEXIFStyler\
    ImageEXIFStyler.exe
    _internal\
      *.dll
      ...
    config\
    UI\logo.svg
    UI\logo.ico
    UI\template_images\
    input\
    output\
    logs\
```

At runtime the exe reads `config`, `UI\logo.*`, `UI\template_images`, and other resource folders from the exe directory. This matches the project-root layout used by `python main.py`.

To produce the older single-file package, pass `-OneFile`:

```powershell
.\build_exe.ps1 -Clean -OneFile
```

`-OneFile` makes the exe much larger because the runtime archive is appended to the exe. The default `onedir` layout keeps the exe smaller by leaving runtime dependencies as DLLs/files in the package directory.

The build script also sets the executable icon from `UI\logo.ico` when present. If no `.ico` exists, it generates a temporary icon from `UI\logo.avg`, `UI\logo.svg`, `UI\logo.png`, `UI\logo.jpg`, or `UI\logo.jpeg` for PyInstaller.

HEIC support is excluded by default to keep the package smaller. To include `pillow_heif` and enable HEIC input in the packaged app:

```powershell
.\build_exe.ps1 -Clean -IncludeHeif
```

The packaged app also excludes optional enhancement modules such as `loguru` and uses the built-in logging fallback.

Existing packaged resource folders are overwritten on each build. Runtime folders such as `input`, `output`, and `logs` are created if missing.

To copy the packaged app to a target folder:

```powershell
.\build_exe.ps1 -InstallDir "D:\Apps\ImageEXIFStyler"
```

To show a console window while debugging startup errors:

```powershell
.\build_exe.ps1 -Console
```
