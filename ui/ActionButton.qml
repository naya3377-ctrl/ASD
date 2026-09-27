// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every button in the app, in four Bauhaus variants:
//  - ghost (default): no frame; hover greys, `active` becomes a yellow block
//  - primary: red block with a hard shadow that presses in
//  - outlined: white block with a hard shadow that presses in
//  - activeFill: a colour for the active state (the mode bar uses one per mode)
Button {
    id: control
    property bool active: false
    property bool primary: false
    property bool outlined: false
    property bool leftAligned: false
    property bool compact: false
    property bool round: false
    property bool inverted: false   // ghost button sitting on a black bar
    property bool onLight: false    // ghost button on a coloured light block (yellow): black ink in both themes
    property color activeFill: Theme.yellow
    property string glyph: ""
    property string hint: ""
    property string shortcutText: ""
    readonly property bool framed: primary || outlined
    // Ink follows the block behind it: white on red/blue, black on yellow/white.
    function inkOn(fill) { return fill.r*.299 + fill.g*.587 + fill.b*.114 > .6 ? Theme.black : Theme.white; }
    readonly property color fillColor: primary ? (hovered && !down ? Theme.accentHover : Theme.accent)
        : active ? activeFill
        : outlined ? (hovered ? Theme.hover : Theme.raised)
        : down ? (inverted ? "#3a3a3a" : onLight ? "#40000000" : Theme.pressed) : hovered ? (inverted ? "#2c2c2c" : onLight ? "#26000000" : Theme.hover) : "transparent"
    readonly property color tone: primary ? Theme.inkOnAccent : active ? inkOn(activeFill) : inverted ? Theme.white : onLight ? Theme.black : Theme.icon
    implicitHeight: compact ? 30 : 34
    implicitWidth: Math.max(implicitHeight, contentItem.implicitWidth + (text.length ? 26 : 16))
    leftPadding: text.length ? 13 : 8; rightPadding: text.length ? 13 : 8
    font.pixelSize: 13
    font.weight: primary || active ? Font.Bold : Font.Medium
    font.letterSpacing: text.length ? .3 : 0
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : .35
    contentItem: Item {
        implicitWidth: contentRow.implicitWidth; implicitHeight: 20
        // Framed buttons move with their face when pressed.
        transform: Translate { x: control.framed && control.down ? 2 : 0; y: control.framed && control.down ? 2 : 0 }
        Row {
            id: contentRow; spacing: 7; anchors.verticalCenter: parent.verticalCenter
            x: control.leftAligned ? 0 : (parent.width-width)/2
            Icon { name: control.glyph; tone: control.tone; anchors.verticalCenter: parent.verticalCenter; size: control.glyph.length ? 18 : 0 }
            Text {
                visible: control.text.length>0; text: control.text; font: control.font
                color: control.primary ? Theme.inkOnAccent : control.active ? control.inkOn(control.activeFill) : control.inverted ? Theme.white : control.onLight ? Theme.black : Theme.ink
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                visible: control.shortcutText.length>0 && control.leftAligned; text: control.shortcutText
                font.pixelSize: 11; color: control.active ? control.tone : Theme.inkMuted; anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    background: Item {
        Block {
            anchors.fill: parent
            radius: control.round ? height/2 : 0
            fill: control.fillColor
            outline: Theme.lineStrong
            outlineWidth: control.framed || control.active ? Theme.border : 0
            shadow: control.framed ? Theme.shadowSmall : 0
            pressed: control.framed && control.down
        }
        // Keyboard focus: a blue ring standing off the button.
        Rectangle {
            visible: control.visualFocus; anchors.fill: parent; anchors.margins: -4
            radius: control.round ? height/2 : 0
            color: "transparent"; border.color: Theme.focusRing; border.width: 2
        }
    }
    ToolTip.visible: hovered && hint.length>0
    ToolTip.text: hint; ToolTip.delay: 550
}
