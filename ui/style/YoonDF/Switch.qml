// SPDX-License-Identifier: AGPL-3.0-or-later
// iOS/macOS switch: a capsule that turns accent with a sliding white knob.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.Switch {
    id: control
    spacing: 10
    font.pixelSize: 13
    opacity: enabled ? 1 : .45
    indicator: Rectangle {
        implicitWidth: 38; implicitHeight: 22
        x: control.leftPadding; y: control.topPadding + (control.availableHeight - height) / 2
        radius: 11
        border.width: control.visualFocus ? 2 : 0; border.color: Theme.focusRing
        color: control.checked ? Theme.accent : Theme.surfaceAlt
        Behavior on color { ColorAnimation { duration: Theme.motionFast } }
        Rectangle {
            x: control.checked ? parent.width - width - 2 : 2; y: 2
            width: 18; height: 18; radius: 9; color: "white"
            border.width: 1; border.color: "#14000000"
            Behavior on x { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: Text {
        leftPadding: control.indicator.width + control.spacing
        text: control.text; font: control.font; color: Theme.ink
        verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap
    }
}
