# Cross-builds LapLIS.exe for Windows (7 SP1+) from Linux, using Wine + a real Windows Python 3.9
# install + PyInstaller. This avoids needing an actual Windows machine just to produce the .exe.
#
# Build:
#   docker build -t laplis-win7-builder .
#   docker run --rm -v "$(pwd)/dist:/output" laplis-win7-builder
#
# The resulting LapLIS.exe (and its dependencies) will be in ./dist on the host afterwards.
#
# Why Wine + a Windows Python install (not the Linux python3.9 already in the base image): a
# .exe built by PyInstaller running under Linux Python is a Linux ELF binary, not a Windows PE
# executable - PyInstaller bundles the interpreter it runs under, it does not cross-compile.
# Running the whole toolchain (Python, pip, PyInstaller) inside Wine is what makes the output a
# genuine, working Windows executable.

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WINEARCH=win64
ENV WINEPREFIX=/root/.wine
ENV WINEDEBUG=-all

# --- Install Wine (WineHQ's own repo, not Ubuntu's older bundled version) ---
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends wget gnupg2 software-properties-common ca-certificates xvfb cabextract && \
    mkdir -pm755 /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# --- Initialize the Wine prefix once (creates /root/.wine) ---
RUN xvfb-run -a wineboot --init

# --- Install Python 3.9 (the last CPython release with an official Windows 7 installer) inside Wine ---
# The full installer (not the embeddable zip) is used because it also registers pip, which the
# embeddable distribution does not include by default.
RUN wget -O /tmp/python-3.9.13-amd64.exe https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe && \
    xvfb-run -a wine /tmp/python-3.9.13-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir="C:\\Python39" && \
    rm /tmp/python-3.9.13-amd64.exe

WORKDIR /app
COPY . /app

# --- Install the app's dependencies + PyInstaller inside the Windows Python ---
RUN xvfb-run -a wine "C:\\Python39\\python.exe" -m pip install --upgrade pip && \
    xvfb-run -a wine "C:\\Python39\\python.exe" -m pip install -r requirements.txt

# --- Build the one-file windowed executable, bundling the seed data and PDF fonts ---
RUN xvfb-run -a wine "C:\\Python39\\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name LapLIS \
    --add-data "app/seed_data;app/seed_data" \
    --add-data "app/reports/fonts;app/reports/fonts" \
    main.py

# The container's entrypoint just copies the freshly-built exe (and its onefile dependencies) out
# to a bind-mounted /output directory, so `docker run --rm -v "$(pwd)/dist:/output" ...` gives you
# the file on the host without needing `docker cp`.
CMD ["sh", "-c", "cp -r /app/dist/* /output/"]
