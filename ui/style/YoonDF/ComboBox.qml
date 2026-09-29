// SPDX-License-Identifier: AGPL-3.0-or-later
// Pop-up button: white, hairline border, soft shadow, ⌃⌄ chevrons; the list
// opens as a rounded popover with an accent highlight.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.ComboBox {
    id: control
    implicitHeight: 32
    font.pixelSize: 13
    opacity: enabled ? 1 : .45
    delegate: ItemDelegate {
        required property var model
        required property int index
        width: ListView.view ? ListView.view.width : control.width
        height: 28
        text: control.textRole ? (Array.isArray(control.model) ? model.modelData[control.textRole] : model[control.textRole]) : model.modelData
        highlighted: control.highlightedIndex === index
        font.weight: control.currentIndex === index ? Font.DemiBold : Font.Normal
    }
    contentItem: Text {
        leftPadding: 11; rightPadding: control.indicator.width + 6
        text: control.displayText; font: control.font; color: Theme.ink
        verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Rectangle {
        x: control.width - width - 5; y: (control.height - height) / 2
        width: 20; height: 20; radius: 5; color: Theme.accent
        Column {
            anchors.centerIn: parent; spacing: -3
            Icon { name: "up"; size: 10; tone: Theme.inkOnAccent }
            Icon { name: "down"; size: 10; tone: Theme.inkOnAccent }
        }
    }
    background: Item {
        implicitWidth: 140
        SoftShadow { anchors.fill: parent; radius: Theme.radius; spread: 3; offsetY: 1; strength: Theme.dark ? .4 : .08 }
        Rectangle { anchors.fill: parent; radius: Theme.radius; color: control.pressed ? Theme.pressed : control.hovered ? (Theme.dark ? "#444446" : "#fafafc") : (Theme.dark ? "#3a3a3c" : "#ffffff"); border.width: 1; border.color: control.visualFocus ? Theme.focusRing : Theme.lineStrong }
    }
    popup: B.Popup {
        y: control.height + 4; width: Math.max(control.width, 160)
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 360)
        padding: 5
        contentItem: ListView {
            clip: true; implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollBar.vertical: ScrollBar { }
        }
        background: Item {
            SoftShadow { anchors.fill: parent; radius: Theme.radius + 2; spread: 14; offsetY: 5 }
            Rectangle { anchors.fill: parent; radius: Theme.radius + 2; color: Theme.dark ? "#2c2c2e" : "#fbfbfd"; border.width: 1; border.color: Theme.line }
        }
    }
}
