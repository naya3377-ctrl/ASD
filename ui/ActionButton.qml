// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool active: false
    property bool primary: false
    property bool outlined: false
    property bool leftAligned: false
    property bool compact: false
    property bool segmented: false   // inside a Segmented strip: active is a white pill
    property string glyph: ""
    property string hint: ""
    property string shortcutText: ""
    implicitHeight: compact ? 30 : 34
    implicitWidth: Math.max(implicitHeight, contentItem.implicitWidth + (text.length ? 24 : 16))
    leftPadding: text.length ? 12 : 8; rightPadding: text.length ? 12 : 8
    font.pixelSize: 13
    font.weight: primary || active ? Font.DemiBold : Font.Normal
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : .38
    readonly property color tone: primary ? Theme.inkOnAccent : active && !segmented ? Theme.iconActive : Theme.icon
    contentItem: Item {
        implicitWidth: contentRow.implicitWidth; implicitHeight: 20
        Row {
            id: contentRow; spacing: 7; anchors.verticalCenter: parent.verticalCenter
            x: control.leftAligned ? 0 : (parent.width-width)/2
            Icon { name: control.glyph; tone: control.tone; anchors.verticalCenter: parent.verticalCenter; size: control.glyph.length ? 18 : 0 }
            Text {
                visible: control.text.length>0; text: control.text; font: control.font
                color: control.primary ? Theme.inkOnAccent : control.active ? (control.segmented ? Theme.ink : Theme.accentInk) : Theme.inkSoft
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                visible: control.shortcutText.length>0 && control.leftAligned; text: control.shortcutText
                font.pixelSize: 11; color: Theme.inkMuted; anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.primary ? (control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accent)
             : control.segmented ? (control.active ? Theme.raised : control.down ? Theme.pressed : control.hovered ? Theme.hover : "transparent")
             : control.down ? Theme.pressed : control.active ? Theme.accentSoft : control.hovered ? Theme.hover
             : control.outlined ? Theme.raised : "transparent"
        border.width: control.outlined || control.visualFocus || (control.segmented && control.active) ? 1 : 0
        border.color: control.visualFocus ? Theme.focusRing : control.segmented ? Theme.line : Theme.lineStrong
        Behavior on color { ColorAnimation { duration: 90 } }
    }
    ToolTip.visible: hovered && hint.length>0
    ToolTip.text: hint; ToolTip.delay: 550
}
