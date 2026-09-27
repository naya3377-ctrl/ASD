// SPDX-License-Identifier: AGPL-3.0-or-later
pragma Singleton
import QtQuick

// Every interface token, set around the white and ink-charcoal Y mark: flat
// white surfaces, hairline edges, one restrained blue for the active tool,
// the chosen page, focus and the main action. Shadows are kept for the page
// and for popups. "system" follows the Windows light/dark setting; the PDF
// page itself always keeps its own colours.
QtObject {
    id: theme
    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)
    // Settings → 동작 줄이기: no movement or scaling, changes happen at once.
    property bool reduceMotion: false

    readonly property color white: "#ffffff"
    readonly property color black: "#000000"

    // Surfaces, from the back of the window to the front. White is neutral,
    // never ivory; only the area around the pages is a pale grey.
    readonly property color window:   dark ? "#1c1e21" : "#ffffff"
    readonly property color chrome:   dark ? "#1c1e21" : "#ffffff"   // toolbar
    readonly property color tabStrip: dark ? "#141619" : "#f5f5f7"   // behind the document tabs
    readonly property color sidebar:  dark ? "#1c1e21" : "#ffffff"
    readonly property color canvas:   dark ? "#121315" : "#f5f5f7"   // around the pages
    readonly property color surface:  dark ? "#1c1e21" : "#ffffff"   // side panels
    readonly property color raised:   dark ? "#26292d" : "#ffffff"   // menus, popups, cards
    readonly property color field:    dark ? "#17191c" : "#ffffff"
    readonly property color well:     dark ? "#2a2d32" : "#f0f1f3"   // the groove of a segmented control

    // Lines.
    readonly property color lineSoft:   dark ? "#282b30" : "#eeeff1"
    readonly property color line:       dark ? "#33373d" : "#e3e5e8"
    readonly property color lineStrong: dark ? "#4a4f56" : "#c9cdd2"

    // Text and icons.
    readonly property color ink:      dark ? "#e6e8eb" : "#29313a"
    readonly property color inkSoft:  dark ? "#c6cad0" : "#434a53"
    readonly property color inkMuted: dark ? "#9ba0a7" : "#62666c"
    readonly property color inkFaint: dark ? "#6f747b" : "#9a9ea4"
    readonly property color icon: ink

    // The one accent: active tool, chosen page, focus, the main action.
    readonly property color accent:        dark ? "#8aaac6" : "#466985"
    readonly property color accentHover:   dark ? "#9db8d0" : "#3d5d76"
    readonly property color accentPressed: dark ? "#7898b5" : "#34516a"
    readonly property color inkOnAccent:   dark ? "#0f1419" : "#ffffff"
    readonly property color accentSoft:    dark ? "#26313c" : "#e3eaf0"   // selected background
    readonly property color accentInk:     dark ? "#b5cadd" : "#34516a"   // text on accentSoft
    readonly property color hover:         dark ? "#12ffffff" : "#0b29313a"
    readonly property color pressed:       dark ? "#1fffffff" : "#1529313a"
    readonly property color focusRing:     accent
    readonly property color selection:     dark ? "#36495b" : "#ccdae6"   // selected text in fields
    readonly property color scrim:         dark ? "#99000000" : "#3329313a"
    readonly property color warnSurface:   dark ? "#3a2f22" : "#fff3e0"
    readonly property color warnInk:       dark ? "#f0cfa0" : "#7a4510"
    readonly property color danger:        dark ? "#e38b81" : "#a8322a"
    readonly property color hud:           "#e6202429"                    // floating dark controls
    readonly property color hudInk:        "#f5f6f7"
    readonly property color tooltip:       dark ? "#e6e8eb" : "#29313a"
    readonly property color tooltipInk:    dark ? "#1c1e21" : "#ffffff"

    // Marks drawn over the PDF page, the same in both themes.
    readonly property color pageMark:     "#466985"
    readonly property color pageMarkFill: "#22466985"
    readonly property color searchFill:   "#5cf2c94c"
    readonly property color searchActive: "#99f2b233"
    readonly property color searchEdge:   "#b07f1a"

    // Spacing: 4 · 8 · 12 · 16 · 24.
    readonly property int gapXs: 4
    readonly property int gapS: 8
    readonly property int gapM: 12
    readonly property int gapL: 16
    readonly property int gapXl: 24

    // Geometry. Buttons 6, panels and popups 10, dialogs 12. Every button
    // keeps a click area of at least 32 × 32.
    readonly property int radiusSmall: 4
    readonly property int radius: 6
    readonly property int radiusLarge: 10
    readonly property int radiusDialog: 12
    readonly property int hairline: 1
    readonly property int control: 32
    readonly property int tabBarHeight: 36
    readonly property int toolbarHeight: 48
    readonly property int sidebarWidth: 220
    readonly property int commentsWidth: 300

    // Motion: react quickly, stop softly (OutCubic). Colour and opacity of the
    // interface only; never the page, its coordinates or its size.
    readonly property int hoverMs: reduceMotion ? 0 : 110       // hover tint and icon colour
    readonly property int pressInMs: 70                          // icon 1 → .97
    readonly property int pressOutMs: 140
    readonly property int selectMs: reduceMotion ? 0 : 140      // mode, tab and segment selection
    readonly property int listMs: reduceMotion ? 0 : 120        // thumbnails and list rows
    readonly property int menuInMs: reduceMotion ? 0 : 150
    readonly property int menuOutMs: reduceMotion ? 0 : 100
    readonly property int panelInMs: reduceMotion ? 0 : 180
    readonly property int panelOutMs: reduceMotion ? 0 : 120
    readonly property int noticeInMs: reduceMotion ? 0 : 160
    readonly property int noticeOutMs: reduceMotion ? 0 : 120
    readonly property int introMs: reduceMotion ? 0 : 360
    readonly property real pressScale: reduceMotion ? 1 : .97
    readonly property real menuShift: reduceMotion ? 0 : 4
    readonly property real panelShift: reduceMotion ? 0 : 8
    readonly property int fast: hoverMs
    readonly property int smooth: reduceMotion ? 0 : 180

    // Type: Pretendard throughout (see bichaek/typefaces.py). Interface text
    // is 14 px, secondary 12–13, panel titles 16. Regular for reading, Medium
    // or SemiBold for choices and titles. Never applied to PDF text.
    readonly property string family: "Pretendard"
    readonly property int caption: 12
    readonly property int small: 13
    readonly property int body: 14
    readonly property int callout: 14
    readonly property int headline: 15
    readonly property int title3: 16
    readonly property int title2: 18
    readonly property int title: 24
    readonly property int display: 30

    function iconUrl(name, tone) {
        var hex = String(tone === undefined ? icon : tone);
        if (hex.length === 9) hex = "#" + hex.slice(3);   // #aarrggbb → #rrggbb
        return "image://icon/" + name + "/" + hex.slice(1);
    }
}
