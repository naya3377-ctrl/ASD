// SPDX-License-Identifier: AGPL-3.0-or-later
// Push button in the macOS manner: white, hairline border, soft shadow;
// "highlighted" (the default action) fills with the accent.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.Button {
    id: control
    implicitHeight: 36
    leftPadding: 16; rightPadding: 16
    font.pixelSize: 14
    font.weight: highlighted ? Font.DemiBold : Font.Normal
    opacity: enabled ? 1 : .45
    contentItem: Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality;
        text: control.text; font: control.font; elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        color: control.highlighted ? Theme.inkOnAccent : Theme.ink
    }
    background: Rectangle {
        implicitWidth: 80
        scale: control.down ? .97 : 1
        Behavior on scale { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Theme.motionFast } }
        radius: Theme.radius
        color: control.highlighted ? (control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accent)
             : control.down ? Theme.pressed : control.hovered ? Theme.hover : Theme.raised
        border.width: control.visualFocus ? 2 : control.highlighted ? 0 : 1
        border.color: control.visualFocus ? Theme.focusRing : Theme.lineStrong
    }
}
