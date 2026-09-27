// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A checkbox: an 18 px rounded box with a hairline edge that fills with the
// accent and shows a white check when on. The whole row is the click area.
CheckBox {
    id: box
    implicitHeight: Theme.control
    spacing: Theme.gapS
    font.family: Theme.family
    font.pixelSize: Theme.body
    indicator: Rectangle {
        x: box.leftPadding; y: (box.height-height)/2
        width: 18; height: 18; radius: Theme.radiusSmall
        color: box.checked ? Theme.accent : Theme.field
        border.width: box.visualFocus ? 2 : Theme.hairline
        border.color: box.checked ? Theme.accent : box.visualFocus ? Theme.focusRing : box.hovered ? Theme.inkMuted : Theme.lineStrong
        Behavior on color { ColorAnimation { duration: Theme.selectMs } }
        Icon { anchors.centerIn: parent; name: "check"; size: 14; tone: Theme.inkOnAccent; visible: box.checked }
    }
    contentItem: Text {
        leftPadding: box.indicator.width + box.spacing
        text: box.text; font: box.font; color: Theme.ink; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap
    }
}
