// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// One place for every interface colour. "system" follows the Windows
// light/dark setting; the page itself always stays paper white.
QtObject {
    id: theme
    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // Surfaces, from the back of the window to the front. Light greys and
    // white in the Windows 11 manner, one blue accent.
    readonly property color canvas:     dark ? "#1b1c1f" : "#f6f5f8"
    readonly property color chrome:     dark ? "#1b1c1f" : "#f6f5f8"
    readonly property color surface:    dark ? "#242529" : "#ffffff"
    readonly property color surfaceAlt: dark ? "#2d2f34" : "#f0f2f4"   // segmented groups
    readonly property color raised:     dark ? "#34363c" : "#ffffff"
    readonly property color field:      dark ? "#1f2023" : "#ffffff"
    readonly property color line:       dark ? "#34363b" : "#e7e7ea"
    readonly property color lineStrong: dark ? "#45484e" : "#d4d6dc"

    // Text.
    readonly property color ink:      dark ? "#eceef2" : "#1f1f24"
    readonly property color inkSoft:  dark ? "#c3c6cc" : "#45464d"
    readonly property color inkMuted: dark ? "#8d9098" : "#7a7c85"
    readonly property color inkFaint: dark ? "#62656c" : "#a9abb2"

    // Accent colour, chosen in Settings. Each entry: [light, dark] for
    // accent, hover, pressed, ink (text on light surfaces), soft (selected fill),
    // selection (text highlight).
    property string accentName: "blue"
    readonly property var accents: ({
        blue:     { label: "파랑",   light: ["#1474c3","#1067b0","#0d5898","#1464ab","#e5f1fd","#cce4fb"], dark: ["#4ea1f0","#66b0f3","#3b8fdd","#9ccdf8","#1f3550","#2b4a6b"] },
        green:    { label: "초록",   light: ["#1f7a4d","#1a6a43","#155a38","#1c6b44","#e3f3ea","#c8e8d6"], dark: ["#4cc38a","#63cf9a","#3aa876","#9be0bd","#1d3a2c","#2a5140"] },
        purple:   { label: "보라",   light: ["#6b45c6","#5d3ab3","#50309c","#5b3cad","#efe9fb","#ddd0f6"], dark: ["#a58af0","#b49df3","#9277e0","#cdbef8","#2e2550","#41356b"] },
        orange:   { label: "주황",   light: ["#c2560c","#ad4c0a","#964208","#a84a0a","#fdefe4","#f9d9c2"], dark: ["#f39a52","#f5aa6a","#e0873e","#f8c79c","#452a17","#5e3a20"] },
        red:      { label: "빨강",   light: ["#c62f3c","#b12835","#99222e","#ad2a36","#fcebed","#f7d0d4"], dark: ["#f07a84","#f38e97","#e0646f","#f7b4ba","#46222a","#60303a"] },
        graphite: { label: "흑연",   light: ["#3d4450","#333a45","#2a303a","#343a45","#eceef1","#d8dce2"], dark: ["#b6bcc7","#c4c9d2","#a2a9b5","#d7dbe1","#30343b","#434852"] }
    })
    readonly property var accentSet: (accents[accentName] || accents.blue)[dark ? "dark" : "light"]
    readonly property color accent:        accentSet[0]
    readonly property color accentHover:   accentSet[1]
    readonly property color accentPressed: accentSet[2]
    readonly property color accentInk:     accentSet[3]
    readonly property color accentSoft:    accentSet[4]
    readonly property color onAccent:      dark ? "#0b1622" : "#ffffff"
    readonly property color hover:         dark ? "#2e3035" : "#f0f2f5"
    readonly property color pressed:       dark ? "#383a40" : "#e4e7ec"
    readonly property color focusRing:     accent
    readonly property color selection:     accentSet[5]

    readonly property color warnSurface: dark ? "#3a2f1c" : "#fff4d6"
    readonly property color warnInk:     dark ? "#f0c98a" : "#7a5518"
    readonly property color danger:      dark ? "#f08b7b" : "#c4382a"
    readonly property color dirty:       dark ? "#e0a84f" : "#c77d12"

    readonly property color icon:       dark ? "#c9ccd2" : "#3b3d44"
    readonly property color iconActive: accentInk

    readonly property color pageEdge:   dark ? "#00000000" : "#dcdde2"
    readonly property color shadow:     dark ? "#66000000" : "#161b2a33"

    readonly property int radius: 8
    readonly property int radiusSmall: 6

    // The accent at a given opacity, for fills over the page.
    function tint(alpha) { return Qt.rgba(accent.r, accent.g, accent.b, alpha); }

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
