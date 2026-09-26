// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// One place for every interface colour. "system" follows the Windows
// light/dark setting; the page itself always stays paper white.
QtObject {
    id: theme
    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // Surfaces, from the back of the window to the front.
    readonly property color canvas:     dark ? "#141816" : "#e9ebe6"
    readonly property color chrome:     dark ? "#101311" : "#e3e7e0"
    readonly property color surface:    dark ? "#1c211e" : "#fbfbf8"
    readonly property color surfaceAlt: dark ? "#181c1a" : "#f4f5f1"
    readonly property color raised:     dark ? "#232926" : "#ffffff"
    readonly property color field:      dark ? "#121614" : "#ffffff"
    readonly property color line:       dark ? "#2a302d" : "#e0e3dc"
    readonly property color lineStrong: dark ? "#3a423e" : "#cfd5cc"

    // Text.
    readonly property color ink:      dark ? "#e7ece8" : "#1d2822"
    readonly property color inkSoft:  dark ? "#b3bdb7" : "#4f5c54"
    readonly property color inkMuted: dark ? "#7d8983" : "#87918a"
    readonly property color inkFaint: dark ? "#5c6660" : "#aab2ab"

    // Brand green and states.
    readonly property color accent:        dark ? "#5aa587" : "#2e5c4d"
    readonly property color accentHover:   dark ? "#6bb597" : "#3a6d5c"
    readonly property color accentPressed: dark ? "#4a9176" : "#224639"
    readonly property color accentInk:     dark ? "#a6dcc4" : "#244f3f"
    readonly property color accentSoft:    dark ? "#233a31" : "#e1ece5"
    readonly property color onAccent:      dark ? "#0d1511" : "#ffffff"
    readonly property color hover:         dark ? "#262c29" : "#edf0eb"
    readonly property color pressed:       dark ? "#2f3632" : "#e1e6df"
    readonly property color focusRing:     dark ? "#6bb597" : "#5f8f7a"
    readonly property color selection:     dark ? "#335847" : "#cfe0d5"

    readonly property color warnSurface: dark ? "#3a2f1c" : "#fff3dc"
    readonly property color warnInk:     dark ? "#f0c98a" : "#7f5a2b"
    readonly property color danger:      dark ? "#e58b7b" : "#b04a3a"
    readonly property color dirty:       dark ? "#d7a45d" : "#b07c38"

    readonly property color icon:       dark ? "#c7d0ca" : "#3c4944"
    readonly property color iconActive: accentInk

    readonly property color pageEdge:   dark ? "#00000000" : "#d4d9d0"
    readonly property color shadow:     dark ? "#66000000" : "#1a1f2a22"

    readonly property int radius: 8
    readonly property int radiusSmall: 6

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
