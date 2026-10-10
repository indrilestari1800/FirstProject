@echo off
setlocal enabledelayedexpansion

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv tidak ditemukan !, membuat virtual environment...
    echo === Mengecek Python ===
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python tidak ditemukan di PATH. Install Python 3.10+ dari python.org lalu ulangi.
        pause
        exit /b 1
    )
    echo === Membuat virtual environment (.venv) ===
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

:run_app
echo [%date% %time%] Starting app...

:: Jalankan python dan tangkap pesan error ke file sementara
python -m main 2> pip_error.txt
set APP_EXIT_CODE=%errorlevel%

:: Jika aplikasi berjalan sukses, selesai
if %APP_EXIT_CODE% equ 0 (
    echo [%date% %time%] App selesai berjalan dengan sukses.
    del pip_error.txt 2>nul
    pause
    exit /b 0
)

:: Cari text ModuleNotFoundError di dalam file error
findstr /C:"ModuleNotFoundError:" pip_error.txt >nul
if %errorlevel% equ 0 (
    
    :: Gunakan Python satu baris untuk mengekstrak nama module dengan pasti
    for /f "delims=" %%i in ('python -c "import re; txt=open('pip_error.txt').read(); match=re.search(r'ModuleNotFoundError:\s*No\s*module\s*named\s*\'([^\']+)\'', txt); print(match.group(1)) if match else ''"') do (
        set "MISSING_MODULE=%%i"
    )

    :: Validasi jika nama module berhasil didapatkan
    if "!MISSING_MODULE!"=="" (
        echo [ERROR] Gagal mendeteksi nama module dari log error.
        goto crash_end
    )
    
    echo [WARNING] Module '!MISSING_MODULE!' tidak ditemukan.
    echo [INFO] Menginstal module '!MISSING_MODULE!' secara otomatis...
    
    :: Install module yang hilang
    pip install !MISSING_MODULE! --disable-pip-version-check
    
    if !errorlevel! equ 0 (
        echo [SUCCESS] Berhasil menginstal !MISSING_MODULE!. Mencoba menjalankan ulang aplikasi...
        echo.
        goto run_app
    ) else (
        echo [ERROR] Gagal menginstal !MISSING_MODULE!. Proses dihentikan.
        goto crash_end
    )
)

:crash_end
echo [%date% %time%] App berhenti/crash karena error lain.
del pip_error.txt 2>nul
pause
