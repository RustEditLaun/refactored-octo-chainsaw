import os
import urllib.request
import subprocess
import time
import zipfile
import shutil
import sys

# URLs and file definitions
DOWNLOAD_URL = "https://pub-23c735f3a19c44f3819cbf97f352eadf.r2.dev/files/RustEditLauncher.exe"
LAUNCHER_EXE = "RustEditLauncher.exe"
INSTALL_DIR = "RustEditClient"

def download_launcher():
    print(f"Downloading {LAUNCHER_EXE} from {DOWNLOAD_URL}...")
    req = urllib.request.Request(
        DOWNLOAD_URL, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    with urllib.request.urlopen(req) as response, open(LAUNCHER_EXE, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print("Download complete.")

def run_and_wait_for_download():
    print("Running launcher to download files...")
    # Note: We assume the launcher runs the installation or updates.
    # We pass standard silent flags just in case it's an installer like InnoSetup or NSIS
    # If it's the PatchKit launcher, it will just start patching.
    
    # We create the install dir and run the launcher from there if it's portable, 
    # but some installers just install to a specific location. Let's assume it puts files in the current dir or nearby.
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)
        
    # Start the launcher
    p = subprocess.Popen([LAUNCHER_EXE, "/S", "/VERYSILENT", "/SUPPRESSMSGBOXES", f"/DIR={os.path.abspath(INSTALL_DIR)}"])
    
    version_file = os.path.join(INSTALL_DIR, "version_info", "last_version.txt")
    
    # Wait for the files to appear and stabilize
    print("Waiting for files to be downloaded completely...")
    stable_count = 0
    last_size = -1
    
    def get_dir_size(path):
        total = 0
        if not os.path.exists(path): return 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
        return total

    # Wait for up to 10 minutes
    for i in range(120):
        time.sleep(5)
        
        # Check if version file exists and size stabilizes
        if os.path.exists(version_file) and os.path.exists(os.path.join(INSTALL_DIR, "RustEdit.exe")):
            current_size = get_dir_size(INSTALL_DIR)
            if current_size == last_size and current_size > 10000000: # at least 10MB
                stable_count += 1
            else:
                stable_count = 0
                
            last_size = current_size
            
            if stable_count >= 6: # Size hasn't changed for 30 seconds
                print(f"Download seems complete. Total size: {current_size / 1024 / 1024:.2f} MB")
                break
                
        # If launcher exited on its own, patching might be done
        if p.poll() is not None:
            if os.path.exists(version_file):
                print("Launcher exited naturally and files exist.")
                break

    print("Terminating launcher processes...")
    try: p.kill() 
    except: pass
    
    os.system("taskkill /f /im \"RustEdit Patcher.exe\" >nul 2>&1")
    os.system("taskkill /f /im \"RustEditLauncher.exe\" >nul 2>&1")
    os.system("taskkill /f /im \"Launcher.exe\" >nul 2>&1")
    time.sleep(2) # Give it time to release file locks

def package_and_get_version():
    version_file = os.path.join(INSTALL_DIR, "version_info", "last_version.txt")
    if not os.path.exists(version_file):
        print("Error: Could not find version file. Installation failed?")
        sys.exit(1)
        
    with open(version_file, "r") as f:
        version = f.read().strip()
        
    zip_filename = f"RustEdit_v{version}.zip"
    print(f"Packaging {INSTALL_DIR} to {zip_filename}...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(INSTALL_DIR):
            for file in files:
                abs_file = os.path.join(root, file)
                # Keep original folder structure without the INSTALL_DIR prefix
                rel_file = os.path.relpath(abs_file, INSTALL_DIR)
                zipf.write(abs_file, rel_file)
                
    print(f"Created {zip_filename}")
    
    # Save the version for Github Actions
    with open("build_version.txt", "w") as f:
        f.write(version)

if __name__ == "__main__":
    download_launcher()
    run_and_wait_for_download()
    package_and_get_version()
