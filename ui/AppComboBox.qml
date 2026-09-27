// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A pop-up button: a white field with a hairline edge and a chevron. The list
// opens like every menu (150 ms in, rows settling 4 px; 100 ms out) with the
// highlighted row on the quiet selection colour and a check on the current one.
ComboBox {
    id: box
    implicitHeight: Theme.control
    font.family: Theme.family
    font.pixelSize: Theme.body
    opacity: enabled ? 1 : .38
    property real shift: 0
    contentItem: Text {
        leftPadding: 11; rightPadding: 8; text: box.displayText; font: box.font
        color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Icon {
        x: box.width-width-10; y: (box.height-height)/2; name: "down"; size: 13; tone: Theme.inkMuted
    }
    background: Rectangle {
        radius: Theme.radius
        color: box.pressed ? Theme.pressed : box.hovered ? Theme.hover : Theme.field
        border.width: box.visualFocus ? 2 : Theme.hairline
        border.color: box.visualFocus ? Theme.focusRing : box.hovered ? Theme.lineStrong : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.hoverMs } }
    }
    delegate: ItemDelegate {
        required property var modelData; required property int index
        width: box.popup.availableWidth; height: 32
        highlighted: box.highlightedIndex === index
        leftPadding: 30
        contentItem: Text {
            text: typeof parent.modelData === "string" ? parent.modelData : box.textAt(parent.index); font: box.font
            color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        Icon { visible: box.currentIndex === parent.index; x: 9; anchors.verticalCenter: parent.verticalCenter; name: "check"; size: 15; tone: Theme.accent }
        background: Rectangle { radius: Theme.radius; color: parent.highlighted ? Theme.accentSoft : "transparent" }
    }
    popup.padding: 5
    popup.y: box.height + 4
    popup.background: Block { fill: Theme.raised; radius: Theme.radiusLarge; shadow: "medium"; outline: Theme.line }
    popup.enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.menuInMs; easing.type: Easing.OutCubic }
            NumberAnimation { target: box; property: "shift"; from: Theme.menuShift; to: 0; duration: Theme.menuInMs; easing.type: Easing.OutCubic }
        }
    }
    popup.exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.menuOutMs; easing.type: Easing.OutCubic } }
    Component.onCompleted: if (popup.contentItem) popup.contentItem.transform = [listShift]
    property Translate listShift: Translate { y: box.shift }
}
