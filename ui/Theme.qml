// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// One place for every interface token, in the Bauhaus style: three pure
// primaries on stark black and off-white, square corners, solid borders and
// hard offset shadows. "system" follows the Windows light/dark setting; the
// PDF page itself always stays paper white.
QtObject {
    id: theme
    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // Primaries. Dark mode lifts red and blue slightly so they read on black.
    readonly property color red:    dark ? "#e0393a" : "#d02020"
    readonly property color blue:   dark ? "#4a78ff" : "#1040c0"
    readonly property color yellow: "#f0c020"
    readonly property color black:  "#121212"
    readonly property color white:  "#ffffff"
    readonly property color paleYellow: dark ? "#3a3218" : "#fff9c4"

    // Surfaces, from the back of the window to the front.
    readonly property color canvas:     dark ? "#0b0b0b" : "#e0e0e0"
    readonly property color canvasDot:  dark ? "#1c1c1c" : "#cdcdcd"
    readonly property color chrome:     dark ? "#050505" : "#121212"   // the black title bar
    readonly property color surface:    dark ? "#171717" : "#f0f0f0"
    readonly property color surfaceAlt: dark ? "#1d1d1d" : "#e8e8e8"
    readonly property color raised:     dark ? "#222222" : "#ffffff"
    readonly property color field:      dark ? "#0f0f0f" : "#ffffff"
    // Structure lines are the ink colour: borders are drawn, not hinted.
    readonly property color line:       dark ? "#5a5a5a" : "#121212"
    readonly property color lineStrong: dark ? "#f0f0f0" : "#121212"
    readonly property color lineSoft:   dark ? "#333333" : "#c8c8c8"

    // Text.
    readonly property color ink:      dark ? "#f0f0f0" : "#121212"
    readonly property color inkSoft:  dark ? "#d6d6d6" : "#262626"
    readonly property color inkMuted: dark ? "#9a9a9a" : "#5c5c5c"
    readonly property color inkFaint: dark ? "#6a6a6a" : "#8c8c8c"
    readonly property color inkOnColor:  "#ffffff"   // text on red and blue
    readonly property color inkOnYellow: "#121212"   // text on yellow

    // Interaction. The primary action is red; selection and "on" states are
    // yellow blocks with black ink; focus and links are blue.
    readonly property color accent:        red
    readonly property color accentHover:   dark ? "#ea5051" : "#b81c1c"
    readonly property color accentPressed: dark ? "#c52f30" : "#a01818"
    readonly property color accentInk:     dark ? "#f0f0f0" : "#121212"
    readonly property color accentSoft:    yellow
    readonly property color inkOnAccent:      "#ffffff"
    readonly property color hover:         dark ? "#2a2a2a" : "#e0e0e0"
    readonly property color pressed:       dark ? "#333333" : "#d0d0d0"
    readonly property color focusRing:     blue
    readonly property color selection:     "#80f0c020"

    readonly property color warnSurface: paleYellow
    readonly property color warnInk:     dark ? "#f0d77a" : "#121212"
    readonly property color danger:      red
    readonly property color dirty:       red

    readonly property color icon:       dark ? "#f0f0f0" : "#121212"
    readonly property color iconActive: "#121212"   // icons sit on yellow when active

    readonly property color pageEdge:   dark ? "#5a5a5a" : "#121212"
    readonly property color shadow:     dark ? "#000000" : "#121212"

    // Geometry: square or round, nothing in between.
    readonly property int radius: 0
    readonly property int radiusSmall: 0
    readonly property int border: 2        // controls, cards, fields
    readonly property int borderHeavy: 4   // major divisions
    readonly property int shadowSmall: 3   // buttons, small cards
    readonly property int shadowLarge: 6   // pages, panels, dialogs

    // Motion: mechanical and quick.
    readonly property int snap: 140

    // Type: Outfit for Latin and numerals (bundled), the system Korean face after it.
    readonly property string displayFamily: outfitBlack.status === FontLoader.Ready ? outfitBlack.name : ""
    property FontLoader outfitRegular: FontLoader { source: "../assets/fonts/Outfit-Regular.ttf" }
    property FontLoader outfitMedium:  FontLoader { source: "../assets/fonts/Outfit-Medium.ttf" }
    property FontLoader outfitBold:    FontLoader { source: "../assets/fonts/Outfit-Bold.ttf" }
    property FontLoader outfitBlack:   FontLoader { id: outfitBlack; source: "../assets/fonts/Outfit-Black.ttf" }
    // Primaries in rotation for repeated decorations (cards, headings).
    function primary(index) { return [red, blue, yellow][((index % 3) + 3) % 3]; }

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
