// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// One place for every interface colour. "system" follows the Windows
// light/dark setting; the page itself always stays paper white.
QtObject {
    id: theme
    property string mode: "system"
    property bool reducedMotion: false
    readonly property int motionFast: reducedMotion ? 0 : 120
    readonly property int motionNormal: reducedMotion ? 0 : 180
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // Surfaces, from the back of the window to the front, after Apple's
    // system colours: one unified light grey for title, tabs and toolbar,
    // white content, and Apple's label and separator greys.
    readonly property color canvas:     dark ? "#161618" : "#f2f3f5"   // behind the pages
    readonly property color chrome:     dark ? "#2a2a2c" : "#fafafb"   // title bar, tabs, toolbar
    readonly property color surface:    dark ? "#1e1e20" : "#ffffff"   // panels
    readonly property color surfaceAlt: dark ? "#3a3a3c" : "#eff0f3"   // segmented controls
    readonly property color raised:     dark ? "#636366" : "#ffffff"   // selected segment, cards
    readonly property color field:      dark ? "#1c1c1e" : "#ffffff"
    readonly property color line:       dark ? "#38383a" : "#e5e5ea"
    readonly property color lineStrong: dark ? "#48484a" : "#d1d1d6"

    // Text (label, secondary, tertiary, quaternary).
    readonly property color ink:      dark ? "#f5f5f7" : "#1d1d1f"
    readonly property color inkSoft:  dark ? "#d1d1d6" : "#3a3a3c"
    readonly property color inkMuted: dark ? "#98989d" : "#6e6e73"
    readonly property color inkFaint: dark ? "#636366" : "#aeaeb2"

    // Accent colour, chosen in Settings: Apple's system colours [light, dark].
    property string accentName: "blue"
    readonly property var accents: ({
        blue:     { label: "파랑", light: "#0078d4", dark: "#0a84ff" },
        purple:   { label: "보라", light: "#af52de", dark: "#bf5af2" },
        pink:     { label: "분홍", light: "#ff2d55", dark: "#ff375f" },
        red:      { label: "빨강", light: "#ff3b30", dark: "#ff453a" },
        orange:   { label: "주황", light: "#ff9500", dark: "#ff9f0a" },
        green:    { label: "초록", light: "#28cd41", dark: "#32d74b" },
        graphite: { label: "흑연", light: "#8e8e93", dark: "#98989d" }
    })
    readonly property var accentOrder: ["blue", "purple", "pink", "red", "orange", "green", "graphite"]
    function accentOf(name) { var a = accents[name] || accents.blue; return dark ? a.dark : a.light; }
    readonly property color accent:        accentOf(accentName)
    readonly property color accentHover:   Qt.darker(accent, 1.08)
    readonly property color accentPressed: Qt.darker(accent, 1.18)
    // Accent as text on light surfaces: a little deeper so it stays legible.
    readonly property color accentInk:     dark ? Qt.lighter(accent, 1.25) : Qt.darker(accent, accentName === "orange" || accentName === "green" ? 1.45 : 1.12)
    readonly property color accentSoft:    tint(dark ? .26 : .13)
    readonly property color inkOnAccent:      "#ffffff"
    readonly property color hover:         dark ? "#353537" : "#ececf0"
    readonly property color pressed:       dark ? "#414143" : "#e1e1e6"
    readonly property color focusRing:     accent
    readonly property color selection:     tint(dark ? .45 : .28)

    readonly property color warnSurface: dark ? "#3a3020" : "#fff8e5"
    readonly property color warnInk:     dark ? "#ffd60a" : "#8a5a00"
    readonly property color danger:      dark ? "#ff453a" : "#ff3b30"
    readonly property color dirty:       dark ? "#ff9f0a" : "#ff9500"

    readonly property color icon:       dark ? "#d1d1d6" : "#3a3a3c"
    readonly property color iconActive: accentInk

    readonly property color pageEdge:   dark ? "#00000000" : "#d8d8dd"
    readonly property color shadow:     dark ? "#66000000" : "#1e000000"

    readonly property int radius: 10          // buttons, fields
    readonly property int radiusSmall: 6
    readonly property int radiusLarge: 16    // sheets, popovers, cards

    // The accent at a given opacity, for fills over the page.
    function tint(alpha) { return Qt.rgba(accent.r, accent.g, accent.b, alpha); }

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
