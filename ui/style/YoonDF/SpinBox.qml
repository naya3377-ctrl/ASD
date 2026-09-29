// SPDX-License-Identifier: AGPL-3.0-or-later
// Number field with − and + in one rounded control.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.SpinBox {
    id: control
    implicitHeight: 32; implicitWidth: 116
    font.pixelSize: 13
    opacity: enabled ? 1 : .45
    contentItem: TextInput {
        text: control.displayText; font: control.font; color: Theme.ink
        horizontalAlignment: Qt.AlignHCenter; verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable; validator: control.validator; inputMethodHints: Qt.ImhFormattedNumbersOnly
        selectByMouse: true; selectionColor: Theme.selection; selectedTextColor: Theme.ink
    }
    down.indicator: Rectangle {
        x: 0; height: parent.height; width: 32; radius: Theme.radius
        color: control.down.pressed ? Theme.pressed : control.down.hovered ? Theme.hover : "transparent"
        Text { anchors.centerIn: parent; text: "−"; font.pixelSize: 16; color: control.value > control.from ? Theme.ink : Theme.inkFaint }
    }
    up.indicator: Rectangle {
        x: parent.width - width; height: parent.height; width: 32; radius: Theme.radius
        color: control.up.pressed ? Theme.pressed : control.up.hovered ? Theme.hover : "transparent"
        Text { anchors.centerIn: parent; text: "+"; font.pixelSize: 16; color: control.value < control.to ? Theme.ink : Theme.inkFaint }
    }
    background: Rectangle { radius: Theme.radius; color: Theme.field; border.width: 1; border.color: control.activeFocus ? Theme.focusRing : Theme.lineStrong }
}
