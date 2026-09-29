// SPDX-License-Identifier: AGPL-3.0-or-later
// Rounded-square check box: accent fill and a white tick when checked.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.CheckBox {
    id: control
    spacing: 9
    font.pixelSize: 13
    opacity: enabled ? 1 : .45
    indicator: Rectangle {
        implicitWidth: 18; implicitHeight: 18
        x: control.leftPadding; y: control.topPadding + (control.availableHeight - height) / 2
        radius: 5
        color: control.checked ? (control.down ? Theme.accentPressed : Theme.accent) : control.down ? Theme.pressed : Theme.field
        border.width: control.checked ? 0 : 1
        border.color: control.visualFocus ? Theme.focusRing : Theme.lineStrong
        Icon { anchors.centerIn: parent; visible: control.checked; name: "check"; size: 14; tone: Theme.inkOnAccent }
    }
    contentItem: Text {
        leftPadding: control.indicator.width + control.spacing
        text: control.text; font: control.font; color: Theme.ink
        verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap
    }
}
