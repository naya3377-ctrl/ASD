// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// Every interface token. The shapes follow macOS Preview: one light toolbar,
// a soft sidebar, rounded controls, pages that float on soft shadows, quick
// eased motion, on plain white. The colours are amekaji, American casual
// workwear as Japan wears it, and the character's own clothes: indigo denim
// (the one accent), brown leather and brass, olive and khaki, with the
// character's near-black fur as ink. "system" follows the Windows light/dark
// setting; the PDF page itself always stays paper white.
QtObject {
    id: theme
    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // Amekaji palette. In the dark theme denim is worn pale.
    readonly property color indigo:      dark ? "#8ea9d8" : "#34507f"   // raw denim
    readonly property color indigoDeep:  dark ? "#a9bfe4" : "#253b63"
    readonly property color indigoSoft:  dark ? "#2b3649" : "#dfe6f1"   // faded chambray
    readonly property color leather:     dark ? "#cf9a6c" : "#8b5a35"   // bow tie, suspenders
    readonly property color leatherSoft: dark ? "#3a2d22" : "#f5ede3"
    readonly property color brass:       dark ? "#d9b467" : "#b08a3e"   // buttons
    readonly property color olive:       dark ? "#aaa874" : "#6b6a3c"
    readonly property color burgundy:    dark ? "#e38d7c" : "#9a3b2e"
    readonly property color white: "#ffffff"
    readonly property color black: "#000000"

    // Surfaces, from the back of the window to the front. The light theme is
    // plain white; only the pages' backdrop is a pale grey so paper shows.
    readonly property color window:  dark ? "#1b1815" : "#ffffff"
    readonly property color chrome:  dark ? "#23201b" : "#ffffff"   // toolbar and tab bar
    readonly property color sidebar: dark ? "#1f1c18" : "#fafaf9"
    readonly property color canvas:  dark ? "#141210" : "#f1f1f0"   // behind the pages
    readonly property color surface: dark ? "#221e1a" : "#ffffff"   // side panels
    readonly property color raised:  dark ? "#2d2823" : "#ffffff"   // cards, popups, the chosen segment
    readonly property color field:   dark ? "#1c1916" : "#ffffff"
    readonly property color well:    dark ? "#16ffffff" : "#0f2a2420"   // the groove of a segmented control

    // Lines.
    readonly property color lineSoft:   dark ? "#34302a" : "#ebeae7"
    readonly property color line:       dark ? "#48403a" : "#dcdad5"
    readonly property color lineStrong: dark ? "#655a4e" : "#b8b4ac"

    // Text: the character's fur.
    readonly property color ink:      dark ? "#f2ebe0" : "#2a2420"
    readonly property color inkSoft:  dark ? "#ddd3c5" : "#463c33"
    readonly property color inkMuted: dark ? "#a99b8b" : "#7a6d5f"
    readonly property color inkFaint: dark ? "#776b5f" : "#aa9d8b"

    // Interaction.
    readonly property color accent:        indigo
    readonly property color accentHover:   dark ? "#a1b8e0" : "#2c4570"
    readonly property color accentPressed: dark ? "#7896c9" : "#233a60"
    readonly property color inkOnAccent:   dark ? "#101624" : "#ffffff"
    readonly property color accentSoft:    indigoSoft
    readonly property color accentInk:     dark ? "#bccdec" : "#2d4674"
    readonly property color hover:         dark ? "#14ffffff" : "#0e2a2420"
    readonly property color pressed:       dark ? "#24ffffff" : "#1a2a2420"
    readonly property color focusRing:     dark ? "#8ea9d8" : "#5b79ae"
    readonly property color selection:     dark ? "#4a5d82" : "#c8d4ea"
    readonly property color scrim:         dark ? "#8c000000" : "#4d2a2420"
    readonly property color warnSurface:   leatherSoft
    readonly property color warnInk:       dark ? "#f0d2b4" : "#6b4222"
    readonly property color danger:        burgundy
    readonly property color hud:           "#e6241f1b"                  // floating dark controls
    readonly property color hudInk:        "#f5f0e7"
    readonly property color icon: ink

    // Marks drawn over the white PDF page, the same in both themes.
    readonly property color pageMark:     "#34507f"
    readonly property color pageMarkFill: "#2434507f"
    readonly property color searchFill:   "#5cd9b24c"
    readonly property color searchActive: "#99d9a93c"
    readonly property color searchEdge:   "#a07a2c"

    // Geometry.
    readonly property int radiusSmall: 5
    readonly property int radius: 7
    readonly property int radiusLarge: 11
    readonly property int hairline: 1

    // Motion: quick and eased.
    readonly property int fast: 120
    readonly property int smooth: 220

    // Type: Pretendard throughout (see bichaek/typefaces.py).
    readonly property string family: "Pretendard"
    readonly property int caption: 11
    readonly property int small: 12
    readonly property int body: 13
    readonly property int callout: 14
    readonly property int headline: 15
    readonly property int title3: 17
    readonly property int title2: 21
    readonly property int title: 28
    readonly property int display: 40

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
