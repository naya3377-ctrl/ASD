// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every button in the app, shaped like macOS controls:
//  - ghost (default): a toolbar button; a soft tint on hover, denim-tinted
//    when `active` (the tool in use)
//  - primary: the indigo push button
//  - outlined: the raised bezel push button
//  - tab: a segment of a Segmented control (the control draws the chosen pill)
//  - hud: a button on dark floating controls (slide show, focus reading)
Button {
    id: control
    property bool active: false
    property bool primary: false
    property bool outlined: false
    property bool tab: false
    property bool hud: false
    property bool leftAligned: false
    property bool compact: false
    property string glyph: ""
    property string hint: ""
    property string shortcutText: ""
    readonly property color fillColor: primary ? (down ? Theme.accentPressed : hovered ? Theme.accentHover : Theme.accent)
        : outlined ? (down ? Qt.darker(Theme.raised, 1.06) : Theme.raised)
        : tab ? (hovered && !active ? Theme.hover : "transparent")
        : hud ? (down ? "#40ffffff" : hovered ? "#26ffffff" : active ? "#33ffffff" : "transparent")
        : active ? Theme.accentSoft : down ? Theme.pressed : hovered ? Theme.hover : "transparent"
    readonly property color tone: primary ? Theme.inkOnAccent : hud ? Theme.hudInk
        : tab ? (active ? Theme.ink : Theme.inkSoft)
        : active ? Theme.accentInk : Theme.ink
    implicitHeight: compact ? 28 : 32
    implicitWidth: Math.max(implicitHeight, contentItem.implicitWidth + (text.length ? 24 : 12))
    leftPadding: text.length ? 12 : 6; rightPadding: text.length ? 12 : 6
    font.family: Theme.family
    font.pixelSize: Theme.body
    font.weight: primary || (tab && active) ? Font.DemiBold : Font.Medium
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : .38
    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    contentItem: Item {
        implicitWidth: contentRow.implicitWidth; implicitHeight: 20
        Row {
            id: contentRow; spacing: 7; anchors.verticalCenter: parent.verticalCenter
            x: control.leftAligned ? 0 : (parent.width-width)/2
            Icon { name: control.glyph; tone: control.tone; anchors.verticalCenter: parent.verticalCenter; size: control.glyph.length ? 17 : 0 }
            Text {
                visible: control.text.length>0; text: control.text; font: control.font
                color: control.tone; anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                visible: control.shortcutText.length>0 && control.leftAligned; text: control.shortcutText
                font.family: Theme.family; font.pixelSize: Theme.caption; color: Theme.inkMuted
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    background: Item {
        Shadow { target: face; level: "small"; visible: control.primary || control.outlined; opacity: control.down ? .4 : .75 }
        Rectangle {
            id: face; anchors.fill: parent
            radius: Theme.radius
            color: control.fillColor
            border.width: control.outlined ? Theme.hairline : 0
            border.color: Theme.line
            Behavior on color { ColorAnimation { duration: Theme.fast } }
            // The top edge of a push button catches a little light.
            Rectangle {
                visible: control.primary; anchors.fill: parent; radius: parent.radius
                gradient: Gradient { GradientStop { position: 0; color: "#1fffffff" } GradientStop { position: .6; color: "#00ffffff" } }
            }
        }
        // Keyboard focus: a soft denim ring around the control.
        Rectangle {
            visible: control.visualFocus; anchors.fill: parent; anchors.margins: -3
            radius: Theme.radius+3; color: "transparent"; border.color: Theme.focusRing; border.width: 2; opacity: .75
        }
    }
    ToolTip.visible: hovered && hint.length>0
    ToolTip.text: hint; ToolTip.delay: 600
}
