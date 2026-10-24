#!/bin/bash
# Genera "JULIA.app" (J.U.L.I.A.): un icono que se abre con doble clic (o desde
# el Dock) y corre start.sh sin mostrar la Terminal.
#
# Uso (una sola vez, o si mueves la carpeta del proyecto):
#     bash launcher/crear_app.sh
#
# Luego arrastra "launcher/JULIA.app" al Dock o al Escritorio.

set -e

LAUNCHER_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$LAUNCHER_DIR/JULIA.app"
START="$LAUNCHER_DIR/start.sh"

rm -rf "$APP"
# La ruta a start.sh queda fija dentro de la app, asi que la app funciona
# aunque la copies al Escritorio o al Dock.
/usr/bin/osacompile -o "$APP" -e "do shell script \"/bin/bash \" & quoted form of \"$START\""

# Icono: el de la balanza, si existe launcher/icono.icns
if [ -f "$LAUNCHER_DIR/icono.icns" ]; then
  cp "$LAUNCHER_DIR/icono.icns" "$APP/Contents/Resources/applet.icns"
  # macOS nuevo toma el icono de Assets.car si existe CFBundleIconName;
  # lo quitamos para que use applet.icns.
  rm -f "$APP/Contents/Resources/Assets.car"
  /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$APP/Contents/Info.plist" 2>/dev/null || true
  # Re-firmar (ad hoc) despues de tocar el bundle, si no macOS lo marca como danado.
  /usr/bin/codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
  touch "$APP"
fi

echo "Listo: $APP"
