// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// Every interface token. Minimal monochrome: black, white and the grays
// between them; serif type; lines instead of shadows; square corners; state
// changes that are instant. Emphasis is inversion (black block, white ink),
// never a colour. "system" follows the Windows light/dark setting; the PDF page
// itself always stays paper white. Comment colours are the document's own
// data and are the only colours shown.
QtObject {
    id: theme
    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // Absolutes, the same in both themes.
    readonly property color black: "#000000"
    readonly property color white: "#ffffff"

    // Surfaces, from the back of the window to the front.
    readonly property color canvas:     dark ? "#0a0a0a" : "#f5f5f5"   // behind the pages
    readonly property real canvasLineOpacity: dark ? .05 : .035       // its ruled texture
    // Title and status bars: black, lifted a step in the dark theme so the
    // black toolbar and the open tab still read as separate from them.
    readonly property color chrome:     dark ? "#171717" : "#000000"
    readonly property color chromeInk:  "#ffffff"
    readonly property color chromeMuted: "#a3a3a3"
    readonly property color chromeLine: dark ? "#3a3a3a" : "#2e2e2e"
    readonly property color surface:    dark ? "#000000" : "#ffffff"
    readonly property color surfaceAlt: dark ? "#000000" : "#ffffff"
    readonly property color raised:     dark ? "#000000" : "#ffffff"
    readonly property color field:      dark ? "#000000" : "#ffffff"
    readonly property color muted:      dark ? "#141414" : "#f5f5f5"

    // Lines. Structure is drawn in ink; hairlines divide quietly.
    readonly property color line:       dark ? "#ffffff" : "#000000"
    readonly property color lineStrong: line
    readonly property color lineSoft:   dark ? "#262626" : "#e5e5e5"

    // Text.
    readonly property color ink:      dark ? "#ffffff" : "#000000"
    readonly property color inkSoft:  dark ? "#e5e5e5" : "#1a1a1a"
    readonly property color inkMuted: dark ? "#a3a3a3" : "#525252"
    readonly property color inkFaint: dark ? "#6b6b6b" : "#8a8a8a"

    // Interaction. Active, pressed and primary states invert.
    readonly property color accent:      ink                 // the inverted block
    readonly property color inkOnAccent: surface             // ink on it
    readonly property color accentSoft:  muted               // a quiet selected row
    readonly property color hover:       muted
    readonly property color pressed:     lineSoft
    readonly property color focusRing:   ink
    readonly property color selection:   dark ? "#66ffffff" : "#33000000"
    readonly property color scrim:       "#66000000"
    readonly property color warnSurface: muted
    readonly property color warnInk:     ink

    readonly property color icon: ink
    readonly property color pageEdge: dark ? "#3d3d3d" : "#000000"

    // Marks drawn over the white PDF page, the same in both themes.
    readonly property color pageMark:      "#000000"
    readonly property color pageMarkFill:  "#1f000000"

    // Geometry: square corners, lines by weight.
    readonly property int radius: 0
    readonly property int hairline: 1
    readonly property int border: 1        // controls, cards, fields
    readonly property int borderStrong: 2  // focus, current page, selected card
    readonly property int rule: 4          // the heavy rule under a section title

    // Motion: instant state changes.
    readonly property int snap: 90

    // Type. YoonDF Display (Playfair Display) for headlines, YoonDF Text
    // (Source Serif 4) for text, JetBrains Mono for numbers and labels; Korean
    // in each comes from Nanum Myeongjo (see bichaek/typefaces.py).
    readonly property string displayFamily: "YoonDF Display"
    readonly property string textFamily: "YoonDF Text"
    readonly property string monoFamily: "JetBrains Mono"
    readonly property int label: 11      // mono labels, spaced
    readonly property int small: 12
    readonly property int body: 13
    readonly property int lead: 15
    readonly property int title: 26      // panel and dialog titles
    readonly property int headline: 40
    readonly property int hero: 112      // the start screen's name
    readonly property real labelSpacing: 1.4

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
