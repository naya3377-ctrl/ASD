// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every button in the app. Emphasis is inversion, never colour:
//  - ghost (default): no frame; a hairline frame on hover, inverted when
//    `active` or pressed
//  - primary: a black block that inverts on hover
//  - outlined: a thin frame that fills black on hover
//  - tab: text that is underlined when `active` (panel switches)
//  - inverted: a ghost button sitting on a black bar
Button {
    id: control
    property bool active: false
    property bool primary: false
    property bool outlined: false
    property bool tab: false
    property bool leftAligned: false
    property bool compact: false
    property bool inverted: false
    property string glyph: ""
    property string hint: ""
    property string shortcutText: ""
    readonly property bool framed: primary || outlined
    // The colours this button is drawn with, before and after inversion.
    readonly property color paper: inverted ? Theme.chrome : Theme.surface
    readonly property color ink: inverted ? Theme.chromeInk : Theme.ink
    readonly property bool filled: !tab && (primary ? !(hovered && !down) : outlined ? (hovered || down) : (active || down))
    readonly property color fillColor: filled ? ink : "transparent"
    readonly property color tone: filled ? paper : tab && !active ? Theme.inkMuted : ink
    implicitHeight: compact ? 30 : 34
    implicitWidth: Math.max(implicitHeight, contentItem.implicitWidth + (text.length ? 26 : 16))
    leftPadding: text.length ? 13 : 8; rightPadding: text.length ? 13 : 8
    font.pixelSize: Theme.body
    font.weight: primary || active ? Font.Bold : Font.Normal
    font.letterSpacing: text.length ? .4 : 0
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : .3
    contentItem: Item {
        implicitWidth: contentRow.implicitWidth; implicitHeight: 20
        Row {
            id: contentRow; spacing: 8; anchors.verticalCenter: parent.verticalCenter
            x: control.leftAligned ? 0 : (parent.width-width)/2
            Icon { name: control.glyph; tone: control.tone; anchors.verticalCenter: parent.verticalCenter; size: control.glyph.length ? 18 : 0 }
            Text {
                visible: control.text.length>0; text: control.text; font: control.font
                color: control.tone; anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                visible: control.shortcutText.length>0 && control.leftAligned; text: control.shortcutText
                font.family: Theme.monoFamily; font.pixelSize: Theme.label; color: control.filled ? control.paper : Theme.inkMuted
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    background: Item {
        Rectangle {
            anchors.fill: parent
            color: control.fillColor
            border.color: control.ink
            border.width: control.tab ? 0 : control.framed || (control.hovered && !control.filled) ? Theme.border : 0
        }
        // A tab says where you are with a rule under its label.
        Rectangle {
            visible: control.tab && control.active
            anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width-2*control.leftPadding+6; height: Theme.borderStrong; color: control.ink
        }
        // Keyboard focus: a solid ring standing off the button.
        Rectangle {
            visible: control.visualFocus; anchors.fill: parent; anchors.margins: -3
            color: "transparent"; border.color: control.ink; border.width: Theme.borderStrong
        }
    }
    ToolTip.visible: hovered && hint.length>0
    ToolTip.text: hint; ToolTip.delay: 550
}
